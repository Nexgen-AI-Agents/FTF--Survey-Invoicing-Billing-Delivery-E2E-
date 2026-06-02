"""Agent A4 — Human Gate v2 (Invoice Pipeline)

Monitors the Teams group chat for replies to posted invoice drafts.
Interprets natural language — not just APPROVE/REJECT keywords.

Supported interactions (all via thread reply on the original message):
  - Approve:       "approve", "looks good", "send it", "go ahead" etc.
  - Reject:        "reject", "don't send", "hold this", "cancel" etc.
  - Modify price:  "change price to 500", "make it $450", "adjust to 600"
  - Add service:   "add elevation certificate", "include EC"
  - Remove service:"remove boundary survey", "take off the EC"
  - Question ans:  free text answers to AI questions posted in the draft
  - Confused:      if AI can't interpret → posts a clarifying question back

Modification loop:
  - A4 interprets the instruction → updates the draft → calls A3 to repost
  - Counter: after MAX_INVOICE_MODIFICATIONS → flags for manual intervention
  - Every human correction is saved to invoice_learnings

Only Robert, Ryan, Prateek can trigger approve/reject/modify.
Random chat is silently ignored.

Status flow:
  invoice_draft_posted
    → invoice_approved       (send to A5)
    → invoice_rejected       (stop, notify)
    → invoice_draft_posted   (after modification — repost loop)
    → invoice_needs_human    (max modifications reached)
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.models import HUMAN_GATE_MODEL
from config.settings import APPROVED_SENDERS, APPROVED_SENDER_EMAILS, FTF_ORDER_URL, MAX_INVOICE_MODIFICATIONS
from core.claude_client import call as llm_call
from core.excel_db import (
    get_orders_awaiting_invoice_approval, get_order_by_id,
    get_processed_reply_ids, increment_modification_count,
    mark_reply_processed, save_invoice_learning,
    save_order_state, log_decision,
)
from core.exceptions import AgentError
from core.logger import get_logger
from core.teams_graph_client import (
    get_channel_thread_replies, post_channel_reply,
)

AGENT_NAME = "agent_a4_human_gate_v2"
log = get_logger(AGENT_NAME)


def _is_approved_sender(sender_name: str, sender_email: str = "") -> bool:
    first = sender_name.strip().lower().split()[0] if sender_name.strip() else ""
    if first not in APPROVED_SENDERS:
        return False
    # Double-verify with email when APPROVED_SENDER_EMAILS is configured
    if APPROVED_SENDER_EMAILS:
        return sender_email.lower() in APPROVED_SENDER_EMAILS
    return True


def _ai_parse_instruction(
    reply_text: str,
    current_draft: dict,
    order_id: str,
) -> dict:
    """Use Claude to interpret a natural language reply.

    Returns:
    {
      "action": "approve" | "reject" | "modify" | "question" | "ignore",
      "modification": {   # only when action=modify
        "type": "change_price" | "add_service" | "remove_service" | "change_field" | "other",
        "description": "what to change",
        "new_value": "...",  # for price changes: float
        "service_name": "..." # for service add/remove
      },
      "reject_reason": "..." | null,
      "question_text": "..." | null,
      "confidence": "HIGH" | "MEDIUM" | "LOW",
      "learned_rule": "one sentence about what was learned from this correction"
    }
    """
    prompt = f"""You work for NexGen Surveying. A team member replied to an invoice draft in Teams.

Reply text: "{reply_text}"

Current invoice draft:
{json.dumps(current_draft, indent=2, default=str)[:1500]}

Determine what the team member wants to do. Return ONLY valid JSON:
{{
  "action": "approve | reject | hold | modify | question | ignore",
  "modification": {{
    "type": "change_price | add_service | remove_service | change_field | other",
    "description": "what specifically to change",
    "new_value": null,
    "service_name": null
  }},
  "reject_reason": null,
  "question_text": null,
  "confidence": "HIGH | MEDIUM | LOW",
  "learned_rule": "short sentence about what we learned from this"
}}

Rules:
- action=approve: they want to send the invoice as-is (synonyms: looks good, send it, ok, APPROVE etc.)
- action=reject: they want to cancel permanently (synonyms: don't send, reject, no, REJECT etc.)
- action=hold: they want to pause this invoice for now but not reject it (synonyms: hold, skip, defer, wait, not yet, pause, hold on, hold this, skip this cycle)
- action=modify: they want to change something (price, service, add/remove)
- action=question: unclear — set question_text to what you'd ask them to clarify
- action=ignore: random chat not related to this invoice
- confidence=LOW → set action=question
- If they say "change price to $500" → type=change_price, new_value=500
- If they say "add elevation certificate" → type=add_service, service_name="Elevation Certificate"
- If they say "remove boundary survey" → type=remove_service, service_name="Boundary Survey"
"""

    try:
        result_str = llm_call(
            model=HUMAN_GATE_MODEL,
            system="You are an invoice approval assistant. Return only valid JSON.",
            user=prompt,
            max_tokens=300,
        ).strip()

        if result_str.startswith("```"):
            result_str = re.sub(r"^```[a-z]*\n?", "", result_str).rstrip("`").strip()

        return json.loads(result_str)

    except Exception as exc:
        log.warning("AI instruction parse failed: %s", exc)
        return {
            "action": "question",
            "modification": {},
            "reject_reason": None,
            "question_text": "I had trouble understanding your message. Could you reply with APPROVE, REJECT, or describe the change you'd like?",
            "confidence": "LOW",
            "learned_rule": "",
        }


def _apply_modification(draft: dict, modification: dict) -> dict:
    """Apply a modification instruction to the current draft dict.

    Returns the updated draft.
    """
    mod_type    = modification.get("type", "other")
    description = modification.get("description", "")
    new_value   = modification.get("new_value")
    service_name = modification.get("service_name", "")

    draft = json.loads(json.dumps(draft))  # deep copy

    if mod_type == "change_price":
        try:
            new_total = float(new_value)
            # If single service: update that service's amount
            if len(draft.get("services", [])) == 1:
                draft["services"][0]["amount"] = new_total
            else:
                # Distribute proportionally, or just update total
                draft["invoice_notes"] = (
                    f"{draft.get('invoice_notes', '')} [Price adjusted to ${new_total:,.2f} by approver]"
                ).strip()
            draft["total_amount"] = new_total
        except (TypeError, ValueError):
            draft["invoice_notes"] = f"{draft.get('invoice_notes', '')} [Approver requested: {description}]".strip()

    elif mod_type == "add_service":
        from config.settings import ELEVATION_CERT_PRICE
        # Add with a default/estimated price
        new_svc = {
            "name": service_name or description,
            "description": service_name or description,
            "amount": ELEVATION_CERT_PRICE if "elevation" in (service_name or "").lower() else 0.0,
        }
        draft.setdefault("services", []).append(new_svc)
        draft["total_amount"] = sum(s.get("amount", 0) for s in draft["services"])
        if new_svc["amount"] == 0.0:
            draft.setdefault("questions_for_approver", []).append(
                f"What price should I use for {service_name}?"
            )

    elif mod_type == "remove_service":
        before = len(draft.get("services", []))
        draft["services"] = [
            s for s in draft.get("services", [])
            if service_name.lower() not in s.get("name", "").lower()
        ]
        if len(draft.get("services", [])) == before:
            draft["invoice_notes"] = f"{draft.get('invoice_notes', '')} [Note: '{service_name}' not found in current services to remove]".strip()
        draft["total_amount"] = sum(s.get("amount", 0) for s in draft["services"])

    else:
        # Generic: note the change for the AI to handle on next compile
        draft["invoice_notes"] = f"{draft.get('invoice_notes', '')} [Requested change: {description}]".strip()

    return draft


def _build_updated_draft_post(order_id: str, draft: dict, modification_count: int, link: str) -> str:
    """Build Teams reply HTML for the updated invoice draft."""
    total = draft.get("total_amount", 0)
    services_lines = ""
    for svc in draft.get("services", []):
        services_lines += f"<li><strong>{svc['name']}</strong> — ${svc.get('amount', 0):,.2f}</li>"

    notes = draft.get("invoice_notes", "")
    questions = draft.get("questions_for_approver", [])
    q_block = "".join(f"<li>❓ {q}</li>" for q in questions)

    html = f"""<strong>Updated Invoice — Order {order_id}</strong> (revision {modification_count})

<ul>{services_lines}</ul>
<strong>Total: ${total:,.2f}</strong>

{f'<p>Notes: {notes}</p>' if notes else ''}
{f'<ul>{q_block}</ul>' if q_block else ''}

<p>Reply <code>APPROVE</code> to send, <code>REJECT [reason]</code> to hold, or request more changes.</p>"""

    return html


def process_order_replies(order_id: str, db_row: dict) -> Optional[str]:
    """Check replies for one order and act on them.

    Returns new status, or None if no actionable reply found.
    """
    message_id = db_row.get("approval_message_id")
    if not message_id:
        log.warning("order %s has no approval_message_id — cannot check replies", order_id)
        return None

    raw_draft = db_row.get("invoice_draft")
    if not raw_draft:
        log.warning("order %s has no invoice_draft", order_id)
        return None

    current_draft = json.loads(raw_draft) if isinstance(raw_draft, str) else raw_draft
    raw_sources   = db_row.get("data_sources")
    data_sources  = json.loads(raw_sources) if isinstance(raw_sources, str) else (raw_sources or {})

    already_processed = get_processed_reply_ids(order_id)

    replies = get_channel_thread_replies(message_id)
    if not replies:
        return None

    new_replies = [r for r in replies if r["id"] not in already_processed]
    if not new_replies:
        log.debug("no new replies for order=%s (all %d already processed)", order_id, len(replies))
        return None

    # Process newest-first — only the latest non-ignored reply counts
    for reply in sorted(new_replies, key=lambda r: r["created_at_dt"], reverse=True):
        sender       = reply["sender"]
        sender_email = reply.get("sender_email", "")
        text         = reply["text"]
        reply_id     = reply["id"]

        if not _is_approved_sender(sender, sender_email):
            log.debug("ignoring reply from unapproved sender=%s email=%s", sender, sender_email)
            mark_reply_processed(order_id, reply_id)
            continue

        parsed = _ai_parse_instruction(text, current_draft, order_id)
        action = parsed.get("action", "ignore")
        learned_rule = parsed.get("learned_rule", "")

        log.info("order=%s sender=%s action=%s confidence=%s",
                 order_id, sender, action, parsed.get("confidence"))

        if action == "ignore":
            mark_reply_processed(order_id, reply_id)
            continue

        mark_reply_processed(order_id, reply_id)

        if action == "approve":
            save_order_state(order_id, status="invoice_approved", approved_by=sender)
            log_decision(
                AGENT_NAME, "invoice_approved",
                order_id=order_id,
                reason=f"Approved by {sender} via Teams thread",
                input_summary=f"total=${current_draft.get('total_amount', 0):.2f}",
                output_summary="status → invoice_approved",
                model_used=HUMAN_GATE_MODEL,
            )
            if db_row.get("modification_count", 0) > 0 and learned_rule:
                _store_learning(order_id, current_draft, text, learned_rule, data_sources, sender)

            post_channel_reply(message_id, f"✅ <strong>Invoice approved by {sender}.</strong> Sending to client shortly...")
            log.info("invoice approved order=%s by=%s", order_id, sender)
            return "invoice_approved"

        elif action == "hold":
            save_order_state(order_id, status="on_hold")
            log_decision(
                AGENT_NAME, "invoice_on_hold",
                order_id=order_id,
                reason=f"Held by {sender} via Teams thread",
                model_used=HUMAN_GATE_MODEL,
            )
            post_channel_reply(message_id, f"⏸️ <strong>Invoice held by {sender}.</strong> Will skip this cycle. Reply APPROVE or REJECT when ready.")
            log.info("invoice on_hold order=%s by=%s", order_id, sender)
            return "on_hold"

        elif action == "reject":
            reason = parsed.get("reject_reason") or text
            save_order_state(order_id, status="invoice_rejected")
            log_decision(
                AGENT_NAME, "invoice_rejected",
                order_id=order_id,
                reason=f"Rejected by {sender}: {reason}",
                model_used=HUMAN_GATE_MODEL,
            )
            post_channel_reply(message_id, f"❌ <strong>Invoice rejected.</strong> Reason: {reason}<br>Will not send to client.")
            log.info("invoice rejected order=%s by=%s reason=%s", order_id, sender, reason)
            return "invoice_rejected"

        elif action == "modify":
            mod_count = increment_modification_count(order_id)

            if mod_count > MAX_INVOICE_MODIFICATIONS:
                save_order_state(order_id, status="invoice_needs_human")
                post_channel_reply(
                    message_id,
                    f"⚠️ I've made {mod_count - 1} modifications on this order and I'm still not getting it right. "
                    f"Please handle order {order_id} manually. I've flagged it for human review."
                )
                log.warning("max modifications reached order=%s count=%d", order_id, mod_count)
                return "invoice_needs_human"

            # Apply modification
            modification = parsed.get("modification", {})
            updated_draft = _apply_modification(current_draft, modification)

            # Store learning
            if learned_rule:
                _store_learning(order_id, current_draft, text, learned_rule, data_sources, sender)

            # Save updated draft
            save_order_state(
                order_id,
                invoice_draft=json.dumps(updated_draft, default=str),
                modification_count=mod_count,
                status="invoice_draft_posted",
                estimate_amount=updated_draft.get("total_amount"),
            )

            # Repost updated draft as a thread reply
            link = f"{FTF_ORDER_URL}/{order_id}"
            reply_html = _build_updated_draft_post(order_id, updated_draft, mod_count, link)
            post_channel_reply(message_id, reply_html)

            log_decision(
                AGENT_NAME, "invoice_modified",
                order_id=order_id,
                reason=f"Modified by {sender}: {modification.get('description', text[:80])}",
                input_summary=f"modification_count={mod_count}",
                output_summary=f"new_total=${updated_draft.get('total_amount', 0):.2f}",
                model_used=HUMAN_GATE_MODEL,
            )
            log.info("invoice modified order=%s by=%s count=%d new_total=%.2f",
                     order_id, sender, mod_count, updated_draft.get("total_amount", 0))
            return "invoice_draft_posted"

        elif action == "question":
            q_text = parsed.get("question_text", "Could you clarify what change you'd like?")
            post_channel_reply(message_id, f"❓ {q_text}")
            log.info("clarification requested order=%s", order_id)
            return None

    return None


def _store_learning(
    order_id: str,
    original_draft: dict,
    human_reply: str,
    learned_rule: str,
    data_sources: dict,
    entered_by: str,
) -> None:
    try:
        packet   = data_sources.get("packet", {})
        svc_type = ""
        svcs     = packet.get("services_requested", {}).get("value", [])
        if svcs:
            svc_type = svcs[0] if isinstance(svcs, list) else str(svcs)
        county = packet.get("property_county", {}).get("value", "")

        save_invoice_learning(
            order_id=order_id,
            original_draft=json.dumps(original_draft, default=str)[:2000],
            human_correction=human_reply[:500],
            learned_rule=learned_rule,
            service_type=svc_type,
            county=county,
            entered_by=entered_by,
        )
        log.info("learning saved order=%s", order_id)
    except Exception as exc:
        log.warning("failed to save learning order=%s: %s", order_id, exc)


def run() -> dict:
    """Check all orders awaiting invoice approval for new replies."""
    orders  = get_orders_awaiting_invoice_approval()
    summary = {"checked": 0, "approved": 0, "rejected": 0, "on_hold": 0, "modified": 0, "errors": 0, "no_reply": 0}

    for db_row in orders:
        order_id = db_row["order_id"]
        try:
            new_status = process_order_replies(order_id, db_row)
            summary["checked"] += 1
            if new_status == "invoice_approved":
                summary["approved"] += 1
            elif new_status == "invoice_rejected":
                summary["rejected"] += 1
            elif new_status == "on_hold":
                summary["on_hold"] += 1
            elif new_status == "invoice_draft_posted":
                summary["modified"] += 1
            else:
                summary["no_reply"] += 1
        except Exception as exc:
            log.error("gate check failed order=%s: %s", order_id, exc)
            summary["errors"] += 1

    log.info("human_gate_v2 complete: %s", summary)
    return summary


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="A4 Human Gate v2 — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--order-id", help="Check a specific order")
    args = parser.parse_args(argv)

    if args.order_id:
        db_row = get_order_by_id(args.order_id)
        if not db_row:
            print(f"Order {args.order_id} not found")
            return
        result = process_order_replies(args.order_id, db_row)
        print(f"Result: {result}")
    elif args.run_now:
        summary = run()
        print(summary)


if __name__ == "__main__":
    main()
