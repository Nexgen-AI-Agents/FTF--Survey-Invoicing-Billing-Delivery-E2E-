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

_DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
_RULES_FILE = os.path.join(_DATA_DIR, "learned_rules.json")
_MAX_RULES  = 100   # keep at most 100 active rules (oldest dropped first)
_SCAN_HOURS = 48    # look back this many hours when scanning messages

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


# ── Claude classification ─────────────────────────────────────────────────────

def _classify_feedback(order_id: str, sender: str, feedback: str) -> dict | None:
    """Ask Claude (Haiku) to classify feedback and extract a generalized rule.

    Returns a dict with keys: type, description, confidence.
    Returns None if the LLM call fails.
    """
    prompt = (
        f"You analyze a Teams reply from a land survey field user on order {order_id}.\n"
        f"Sender: {sender}\n"
        f'Reply: "{feedback}"\n\n'
        "Classify this feedback:\n"
        "- pricing_rule: teaches how to price similar orders "
        '(e.g., "add $X for Y", "this type should cost $Z", "reduce price when...")\n'
        "- detection_rule: teaches what orders to reject/skip/flag "
        '(e.g., "don\'t invoice these", "skip if property type is X")\n'
        "- general_instruction: general workflow or process guidance that should always apply\n"
        "- noise: not actionable (vague, conversational, or already covered)\n\n"
        "If actionable, write a GENERALIZED one-sentence rule for FUTURE orders "
        "(not specific to this one order).\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"type": "pricing_rule|detection_rule|general_instruction|noise", '
        '"description": "one-sentence rule (empty string if noise)", '
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
    """Scan Teams for feedback, extract rules, save to learned_rules.json."""
    data          = _load_rules()
    processed_ids: set  = set(data.get("processed_message_ids", []))
    rules: list         = data.get("rules", [])

    new_rules  = 0
    skipped    = 0
    cutoff     = datetime.now(timezone.utc) - timedelta(hours=_SCAN_HOURS)

    try:
        messages = get_recent_messages(limit=100)
    except Exception as exc:
        log.error("could not fetch Teams messages: %s", exc)
        return {"new_rules": 0, "skipped": 0, "error": str(exc)}

    for msg in messages:
        # Only scan messages within the look-back window
        if msg["created_at_dt"] < cutoff:
            continue

        # Extract order ID from the parent message (our bot order cards contain it)
        parent_order_id = _extract_order_id(msg["text"])

        # We're interested in replies on bot order-card messages, but also check
        # any message that has replies in case a human posted the order ref themselves
        try:
            replies = get_channel_thread_replies(msg["id"])
        except Exception as exc:
            log.warning("could not fetch replies msg=%s: %s", msg["id"], exc)
            continue

        for reply in replies:
            reply_id = reply["id"]

            # Always mark as seen — even if we skip, so we don't reprocess
            already_seen = reply_id in processed_ids
            processed_ids.add(reply_id)

            if already_seen:
                continue

            sender = reply["sender"]
            text   = reply["text"].strip()

            if not text:
                continue

            # Only learn from authorized users (same whitelist as approvals)
            sender_first = (sender or "").split()[0].lower()
            if sender_first not in APPROVED_SENDERS:
                log.debug("skip feedback from unauthorized sender=%s", sender)
                skipped += 1
                continue

            # Skip APPROVE/REJECT/DEFER/YES/NO — handled by poll_teams_approvals
            if _is_command(text):
                continue

            # Skip short/generic noise without calling the LLM
            if _is_noise(text):
                skipped += 1
                continue

            eff_order_id = _extract_order_id(text) or parent_order_id or "unknown"

            # Ask Claude to classify
            result = _classify_feedback(eff_order_id, sender, text)
            if not result:
                skipped += 1
                continue

            feedback_type = result.get("type", "noise")
            description   = (result.get("description") or "").strip()
            confidence    = result.get("confidence", "low")

            if feedback_type == "noise" or not description or confidence == "low":
                skipped += 1
                log.debug("noise/low-confidence feedback skipped: %s", text[:80])
                continue

            # Store the rule
            rule_id = f"rule_{uuid.uuid4().hex[:8]}"
            rule = {
                "id":           rule_id,
                "type":         feedback_type,
                "description":  description,
                "raw_feedback": text[:500],
                "order_id":     eff_order_id,
                "learned_from": sender,
                "learned_at":   datetime.now(timezone.utc).isoformat(),
                "confidence":   confidence,
                "status":       "active",
            }
            rules.append(rule)
            new_rules += 1

            log.info(
                "rule learned id=%s type=%s from=%s order=%s | %s",
                rule_id, feedback_type, sender, eff_order_id, description[:80],
            )

            # Acknowledge in the Teams thread
            label = feedback_type.replace("_", " ").title()
            ack = (
                f"[INFO] ✅ Learned ({label}) from <strong>{sender}</strong>:<br>"
                f"<em>{description}</em><br>"
                f"<small>Applied to all future orders. Rule: <code>{rule_id}</code></small>"
            )
            try:
                send_channel_message(ack, parent_message_id=msg["id"])
            except Exception as exc:
                log.warning("could not post ack for rule=%s: %s", rule_id, exc)

    # Keep only the most recent _MAX_RULES rules
    if len(rules) > _MAX_RULES:
        rules = rules[-_MAX_RULES:]

    # Persist
    data["rules"]                = rules
    data["processed_message_ids"] = list(processed_ids)
    _save_rules(data)

    log.info(
        "feedback learner complete new_rules=%d skipped=%d total_rules=%d",
        new_rules, skipped, len(rules),
    )
    return {"new_rules": new_rules, "skipped": skipped, "total_rules": len(rules)}


if __name__ == "__main__":
    import json as _j
    print(_j.dumps(run(), indent=2))
