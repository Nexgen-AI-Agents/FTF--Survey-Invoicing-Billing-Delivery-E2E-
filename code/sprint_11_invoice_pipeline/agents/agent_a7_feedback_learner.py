"""Agent A7 — Feedback Learner

Scans the Teams channel for non-approval replies on order message threads.
Extracts learnable rules from field user feedback (pricing, detection, workflow).
Persists rules to data/learned_rules.json and acknowledges in the Teams thread.

How it works:
  1. Reads all recent channel messages (last 48h).
  2. For each message that has thread replies, fetches those replies.
  3. Skips replies that are APPROVE/REJECT/DEFER commands (handled by A4/poll).
  4. Skips replies from senders not in APPROVED_SENDERS.
  5. Sends remaining feedback to Claude (Haiku) for classification.
  6. Stores high/medium confidence rules in data/learned_rules.json.
  7. Posts a "[INFO] Learned: ..." acknowledgment in the Teams thread.
  8. Marks each processed reply ID so it's never re-classified.

A3 reads learned_rules.json at pricing time and injects active rules as
additional context into the Claude pricing prompt — no code changes needed
to apply a new rule.

Status: called at the end of each invoice pipeline cycle by A0.
"""

import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.models import MONITOR_MODEL
from config.settings import APPROVED_SENDERS
from core.claude_client import call as llm_call
from core.logger import get_logger
from core.teams_graph_client import (
    get_channel_thread_replies,
    get_recent_messages,
    send_channel_message,
)

log = get_logger("agent_a7_feedback_learner")

_DATA_DIR            = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
_RULES_FILE          = os.path.join(_DATA_DIR, "learned_rules.json")
_MAX_RULES           = 100   # keep at most 100 active rules (oldest dropped first)
_SCAN_HOURS          = 48    # look back this many hours when scanning messages
_CONFIRM_EXPIRE_HRS  = 24   # pending confirmation expires after this many hours

# First words that mark APPROVE/REJECT/DEFER/YES/NO commands — already handled by A4
_COMMAND_FIRST_WORDS = {
    "approve", "reject", "defer", "yes", "no", "yeah", "nope", "nah",
    "yep", "yup", "sure", "ok", "okay",
}

# Replies too short or generic to carry useful rules
_NOISE_PHRASES = {
    "ok", "okay", "thanks", "thank you", "got it", "noted", "sure",
    "will do", "understood", "sounds good", "good", "great", "perfect",
    "alright", "done", "👍", "✅", "check", "cool", "nice",
}

# Response keywords for the global-vs-this-order confirmation prompt
_GLOBAL_KW = {
    "global", "all orders", "all future", "always", "save it", "save rule",
    "for all", "every order", "all cases", "every time",
}
_THIS_ORDER_KW = {
    "this order", "just this", "only this", "this one", "one time", "one-time",
    "just once", "this case", "only for this", "not global", "don't save",
    "dont save", "just now", "this instance",
}
_SKIP_KW = {
    "skip", "ignore", "never mind", "nevermind", "cancel", "discard", "forget it",
}


# ── Persistence ───────────────────────────────────────────────────────────────

def _load_rules() -> dict:
    try:
        with open(_RULES_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"version": 1, "rules": [], "processed_message_ids": []}
    except Exception as exc:
        log.warning("could not read learned_rules.json: %s — starting fresh", exc)
        return {"version": 1, "rules": [], "processed_message_ids": []}


def _save_rules(data: dict) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_RULES_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_order_id(text: str) -> str | None:
    """Return the first 10-digit FTF order ID (1000XXXXXX) found in text."""
    m = re.search(r"\b(100\d{7})\b", text)
    return m.group(1) if m else None


def _is_command(text: str) -> bool:
    """True if the reply starts with an APPROVE/REJECT/DEFER/YES/NO keyword."""
    first = text.strip().lower().split()[0] if text.strip() else ""
    return first in _COMMAND_FIRST_WORDS


def _is_noise(text: str) -> bool:
    """True if the reply is too short/generic to be actionable."""
    clean = text.strip().lower().rstrip("!.,?")
    return len(clean) < 5 or clean in _NOISE_PHRASES


# ── Confirmation resolution ───────────────────────────────────────────────────

def _classify_confirm_response(text: str) -> str | None:
    """Return 'global', 'this_order', 'skip', or None (ambiguous / not a response)."""
    t = text.lower().strip()
    for kw in _THIS_ORDER_KW:
        if kw in t:
            return "this_order"
    for kw in _GLOBAL_KW:
        if kw in t:
            return "global"
    for kw in _SKIP_KW:
        if kw in t:
            return "skip"
    # Single-word shortcuts
    first = t.split()[0] if t.split() else ""
    if first in {"global", "all", "always"}:
        return "global"
    if first in {"skip", "ignore", "cancel"}:
        return "skip"
    return None


def _find_confirm_response(
    conf: dict, messages: list[dict]
) -> tuple[str | None, str | None]:
    """Scan recent top-level messages AND thread replies for a confirmation response.

    Returns (response, replied_msg_id) where response is 'global' | 'this_order' |
    'skip' | None, and replied_msg_id is the ID of the message that contained
    the response (to mark as processed).
    """
    sender_first = conf["sender"].split()[0].lower()
    asked_at     = datetime.fromisoformat(conf["asked_at"])

    for msg in messages:
        if msg["created_at_dt"] <= asked_at:
            continue

        # Top-level channel messages from the same sender
        if not msg["is_app"]:
            if (msg["sender"] or "").split()[0].lower() == sender_first:
                r = _classify_confirm_response(msg["text"])
                if r:
                    return r, msg["id"]

        # Thread replies on any recent message
        try:
            for reply in get_channel_thread_replies(msg["id"]):
                if reply["created_at_dt"] <= asked_at:
                    continue
                if (reply["sender"] or "").split()[0].lower() == sender_first:
                    r = _classify_confirm_response(reply["text"])
                    if r:
                        return r, reply["id"]
        except Exception:
            pass

    return None, None


def _resolve_pending_confirmations(
    data: dict, messages: list[dict], processed_ids: set
) -> int:
    """Resolve any pending confirmations that now have a response. Returns count resolved."""
    pending  = data.get("pending_confirmations", [])
    resolved = set()
    now      = datetime.now(timezone.utc)
    count    = 0

    for conf in pending:
        conf_id  = conf["id"]
        asked_at = datetime.fromisoformat(conf["asked_at"])
        order_id = conf["order_id"]
        sender   = conf["sender"]
        cls      = conf["classification"]

        # Expire after _CONFIRM_EXPIRE_HRS
        if (now - asked_at).total_seconds() > _CONFIRM_EXPIRE_HRS * 3600:
            log.info("confirmation expired id=%s order=%s", conf_id, order_id)
            resolved.add(conf_id)
            continue

        response, resp_msg_id = _find_confirm_response(conf, messages)
        if response is None:
            continue

        # Mark the response message as seen so it isn't re-processed as feedback
        if resp_msg_id:
            processed_ids.add(resp_msg_id)

        resolved.add(conf_id)
        count += 1

        if response == "global":
            rule_id = f"rule_{uuid.uuid4().hex[:8]}"
            rule = {
                "id":           rule_id,
                "type":         cls["type"],
                "description":  cls["description"],
                "raw_feedback": conf["raw_feedback"],
                "order_id":     order_id,
                "learned_from": sender,
                "learned_at":   now.isoformat(),
                "confidence":   cls["confidence"],
                "status":       "active",
            }
            data.setdefault("rules", []).append(rule)
            log.info("confirmation resolved global rule_id=%s order=%s", rule_id, order_id)
            try:
                send_channel_message(
                    f"[INFO] ✅ <strong>Rule saved globally</strong> (from <strong>{sender}</strong> on order "
                    f"<strong>{order_id}</strong>):<br><em>{cls['description']}</em><br>"
                    f"<small>Applied to all future orders. Rule ID: <code>{rule_id}</code></small>"
                )
            except Exception as exc:
                log.warning("could not post global-save ack: %s", exc)

        elif response == "this_order":
            overrides = data.setdefault("order_overrides", {})
            overrides.setdefault(order_id, []).append(cls["description"])
            log.info("confirmation resolved this-order order=%s", order_id)
            try:
                send_channel_message(
                    f"[INFO] ✅ <strong>Got it</strong> — <strong>{sender}</strong>'s instruction applied to order "
                    f"<strong>{order_id}</strong> only. No global rule saved."
                )
            except Exception as exc:
                log.warning("could not post this-order ack: %s", exc)

        elif response == "skip":
            log.info("confirmation skipped id=%s order=%s", conf_id, order_id)
            try:
                send_channel_message(
                    f"[INFO] Feedback from <strong>{sender}</strong> on order "
                    f"<strong>{order_id}</strong> discarded — no rule saved."
                )
            except Exception as exc:
                log.warning("could not post skip ack: %s", exc)

    data["pending_confirmations"] = [c for c in pending if c["id"] not in resolved]
    return count


# ── Claude classification ─────────────────────────────────────────────────────

def _classify_feedback(order_id: str, sender: str, feedback: str) -> dict | None:
    """Ask Claude (Haiku) to classify feedback and extract a generalized rule.

    Type values:
      pricing_rule       — adjusts how future orders are priced (Claude applies as context)
      detection_rule     — teaches which orders to skip/reject/flag (Claude applies as context)
      general_instruction — workflow guidance Claude should follow for all orders
      code_change        — requires editing Python/YAML/SQL — must NOT be auto-applied;
                           user is directed to the development team instead
      noise              — vague, conversational, or not actionable

    The critical distinction:
      Logic rules → Claude can apply them by reading natural language (store as rule)
      Code changes → require a developer to edit source files (never store; alert user)

    Returns a dict with keys: type, description, confidence.
    Returns None if the LLM call fails.
    """
    prompt = (
        f"You analyze a Teams reply from a land survey manager on order {order_id}.\n"
        f"Sender: {sender}\n"
        f'Reply: "{feedback}"\n\n'
        "STEP 1 — Does the message contain an APPROVAL or REJECTION?\n"
        "  approval_detected: true if the person says approved, looks good, go ahead, yes do it, "
        "create it, confirmed, proceed, etc.\n"
        "  approval_detected: false if it is purely feedback, a question, or a rejection.\n\n"
        "STEP 2 — Does the message ALSO contain a separate INSTRUCTION (even if approval was detected)?\n"
        "Classify the instruction (ignore the approval part) into ONE of:\n"
        "  pricing_rule: adjusts how similar orders should be priced\n"
        "  detection_rule: teaches which orders to reject, skip, or flag\n"
        "  general_instruction: workflow/process guidance\n"
        "  code_change: requires a developer to edit code (bugs, new features, system changes)\n"
        "  noise: no actionable instruction found\n\n"
        "CRITICAL: If approval_detected is true AND there is also an instruction, set both.\n"
        "CRITICAL: system behaviour changes (bugs, new features) → always code_change.\n\n"
        "If there is an actionable instruction, write a GENERALIZED one-sentence rule "
        "for future orders (not specific to this order). Empty string otherwise.\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"approval_detected": true|false, '
        '"type": "pricing_rule|detection_rule|general_instruction|code_change|noise", '
        '"description": "one-sentence rule or empty string", '
        '"confidence": "high|medium|low"}'
    )

    try:
        raw = llm_call(
            model=MONITOR_MODEL,
            system="Classify land survey Teams feedback. Output valid JSON only.",
            user=prompt,
            max_tokens=150,
        ).strip()

        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()

        return json.loads(raw)

    except Exception as exc:
        log.warning("classification LLM call failed order=%s: %s", order_id, exc)
        return None


# ── Main run ──────────────────────────────────────────────────────────────────

def run() -> dict:
    """Scan Teams for feedback; ask global-vs-this-order before saving any rule."""
    data          = _load_rules()
    processed_ids: set = set(data.get("processed_message_ids", []))
    rules: list        = data.get("rules", [])

    pending_confirmed = 0
    new_pending       = 0
    skipped           = 0
    cutoff            = datetime.now(timezone.utc) - timedelta(hours=_SCAN_HOURS)

    try:
        messages = get_recent_messages(limit=100)
    except Exception as exc:
        log.error("could not fetch Teams messages: %s", exc)
        return {"new_pending": 0, "skipped": 0, "error": str(exc)}

    # ── Phase 1: resolve any pending confirmations that now have a response ───
    pending_confirmed = _resolve_pending_confirmations(data, messages, processed_ids)
    # Re-read rules list in case confirmations added to it
    rules = data.get("rules", [])

    # ── Phase 2: scan for new feedback ───────────────────────────────────────
    for msg in messages:
        if msg["created_at_dt"] < cutoff:
            continue

        parent_order_id = _extract_order_id(msg["text"])

        try:
            replies = get_channel_thread_replies(msg["id"])
        except Exception as exc:
            log.warning("could not fetch replies msg=%s: %s", msg["id"], exc)
            continue

        for reply in replies:
            reply_id     = reply["id"]
            already_seen = reply_id in processed_ids
            processed_ids.add(reply_id)

            if already_seen:
                continue

            sender = reply["sender"]
            text   = reply["text"].strip()

            if not text:
                continue

            sender_first = (sender or "").split()[0].lower()
            if sender_first not in APPROVED_SENDERS:
                log.debug("skip unauthorized sender=%s", sender)
                skipped += 1
                continue

            if _is_command(text):
                continue

            if _is_noise(text):
                skipped += 1
                continue

            eff_order_id = _extract_order_id(text) or parent_order_id or "unknown"

            result = _classify_feedback(eff_order_id, sender, text)
            if not result:
                skipped += 1
                continue

            feedback_type     = result.get("type", "noise")
            description       = (result.get("description") or "").strip()
            confidence        = result.get("confidence", "low")
            approval_detected = bool(result.get("approval_detected", False))

            # ── Approval intent handled by A4 via LLM — just log and skip ────
            # A4's check_for_approvals() now has an LLM fallback that will
            # pick up natural language approvals on the same cycle.
            if approval_detected:
                log.info(
                    "approval_detected in reply from=%s order=%s — A4 will handle it",
                    sender, eff_order_id,
                )
                # If the reply is ONLY an approval with no separate instruction, skip
                if feedback_type == "noise" or not description:
                    continue

            # ── Code change: direct to dev team ──────────────────────────────
            if feedback_type == "code_change":
                log.info("code_change from=%s order=%s: %s", sender, eff_order_id, text[:120])
                dev_msg = (
                    f"[INFO] 🛠️ <strong>{sender}</strong> — your feedback on order "
                    f"<strong>{eff_order_id}</strong> requires a <strong>code change</strong> "
                    f"and cannot be applied automatically.<br><br>"
                    f"<strong>What you said:</strong> <em>{text[:300]}</em><br><br>"
                    f"Please contact the <strong>development team</strong> to implement this. "
                    f"The AI pipeline only learns order logic (pricing rules, detection rules, "
                    f"workflow instructions) — system-level changes require a developer."
                )
                try:
                    send_channel_message(dev_msg)
                except Exception as exc:
                    log.warning("could not post code_change notice: %s", exc)
                skipped += 1
                continue

            # ── Noise / low-confidence: discard silently ─────────────────────
            if feedback_type == "noise" or not description or confidence == "low":
                skipped += 1
                log.debug("noise/low skipped: %s", text[:80])
                continue

            # ── Valid logic feedback: ask global-vs-this-order BEFORE saving ─
            confirm_id = f"confirm_{uuid.uuid4().hex[:8]}"
            pending_entry = {
                "id":            confirm_id,
                "order_id":      eff_order_id,
                "sender":        sender,
                "raw_feedback":  text[:500],
                "classification": {
                    "type":        feedback_type,
                    "description": description,
                    "confidence":  confidence,
                },
                "asked_at": datetime.now(timezone.utc).isoformat(),
            }
            data.setdefault("pending_confirmations", []).append(pending_entry)
            new_pending += 1

            log.info(
                "confirmation pending id=%s type=%s from=%s order=%s | %s",
                confirm_id, feedback_type, sender, eff_order_id, description[:80],
            )

            label       = feedback_type.replace("_", " ").title()
            confirm_msg = (
                f"[FEEDBACK] <strong>Order {eff_order_id}</strong> — "
                f"<strong>{sender}</strong> said:<br>"
                f"<em>{text[:300]}</em><br><br>"
                f"AI classified as <strong>{label}</strong>:<br>"
                f"<em>{description}</em><br><br>"
                f"📋 <strong>Reply with one of:</strong><br>"
                f"&nbsp;&nbsp;<code>global</code> — save this rule for <strong>ALL future orders</strong><br>"
                f"&nbsp;&nbsp;<code>this order</code> — apply to order <strong>{eff_order_id} only</strong><br>"
                f"&nbsp;&nbsp;<code>skip</code> — discard, save nothing<br><br>"
                f"<small>Confirmation ID: {confirm_id} | Expires in 24h</small>"
            )
            try:
                send_channel_message(confirm_msg)
            except Exception as exc:
                log.warning("could not post confirmation question id=%s: %s", confirm_id, exc)

    # Keep only the most recent _MAX_RULES rules
    if len(rules) > _MAX_RULES:
        rules = rules[-_MAX_RULES:]

    data["rules"]                 = rules
    data["processed_message_ids"] = list(processed_ids)
    _save_rules(data)

    log.info(
        "feedback learner complete pending_confirmed=%d new_pending=%d skipped=%d total_rules=%d",
        pending_confirmed, new_pending, skipped, len(rules),
    )
    return {
        "pending_confirmed": pending_confirmed,
        "new_pending":       new_pending,
        "skipped":           skipped,
        "total_rules":       len(rules),
    }


if __name__ == "__main__":
    import json as _j
    print(_j.dumps(run(), indent=2))
