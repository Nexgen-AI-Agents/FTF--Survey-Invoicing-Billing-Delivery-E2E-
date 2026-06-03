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
from config.settings import APPROVED_SENDERS, APPROVED_SENDER_EMAILS, APPROVED_SENDER_EMAIL_MAP, FTF_ORDER_URL, MAX_INVOICE_MODIFICATIONS
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
    get_chat_messages, post_chat_message, post_chat_reply,
)

AGENT_NAME = "agent_a4_human_gate_v2"
log = get_logger(AGENT_NAME)


def _is_approved_sender(sender_name: str, sender_email: str = "") -> bool:
    first = sender_name.strip().lower().split()[0] if sender_name.strip() else ""
    email_local = sender_email.split("@")[0].lower() if "@" in sender_email else ""
    name_match = first in APPROVED_SENDERS or email_local in APPROVED_SENDERS
    if not name_match:
        return False
    if APPROVED_SENDER_EMAILS:
        if sender_email.lower() in APPROVED_SENDER_EMAILS:
            return True
        # Accept on email local-part match to handle UPN drift (e.g. pchandra@ vs prateek@)
        if email_local in APPROVED_SENDERS:
            log.warning("sender=%s email=%s — accepting on local-part match (UPN drift)",
                        sender_name, sender_email)
            return True
        return False
    return True


def _ai_parse_instruction(
    reply_text: str,
    current_draft: dict,
    order_id: str,
) -> dict:
    """Use Claude to interpret a natural language reply.

    Returns:
    {
      "action": "approve" | "reject" | "hold" | "modify" | "question" | "ignore",
      "email_override": "sender" | null,
      "modification": {   # only when action=modify
        "type": "change_price" | "add_service" | "remove_service" | "change_field" | "other",
        "description": "what to change",
        "new_value": "...",  # for price changes: float
        "service_name": "..." # for service add/remove
      },
      "reject_reason": "..." | null,
      "question_text": "..." | null,
      "confidence": "HIGH" | "MEDIUM" | "LOW",
      "status_message": "one natural sentence of what you understood",
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
  "email_override": "sender | null",
  "modification": {{
    "type": "change_price | add_service | remove_service | change_field | other",
    "description": "what specifically to change",
    "new_value": null,
    "service_name": null
  }},
  "reject_reason": null,
  "question_text": null,
  "confidence": "HIGH | MEDIUM | LOW",
  "status_message": "one natural sentence describing exactly what you understood",
  "learned_rule": "short sentence about what we learned from this"
}}

Rules:
- action=approve: they want to send the invoice (synonyms: looks good, send it, ok, APPROVE, approved, go ahead, create the invoice, proceed etc.)
- action=reject: they want to cancel permanently (synonyms: don't send, reject, no, REJECT etc.)
- action=hold: they want to pause without rejecting (synonyms: hold, skip, defer, wait, not yet, pause, hold this, skip this cycle)
- action=modify: they want to change something (price, service, add/remove)
- action=question: you are genuinely unsure — set question_text to a specific, natural clarifying question that names what was ambiguous and offers 2-3 options
- action=ignore: random chat not related to this invoice
- confidence=LOW → always set action=question; question_text must be specific and natural — do not use generic "could you clarify"
- confidence=MEDIUM → proceed with your best interpretation; set status_message so the user can correct you
- confidence=HIGH → proceed; still set status_message
- email_override="sender": they said "send to me", "email me", "send it to me", "send to my email", "send the email to me", or referenced their own name as the recipient
- email_override=null: they did not ask to redirect the email recipient
- status_message: ALWAYS set — natural language, e.g. "You approved the invoice and want the email sent to you instead of the client." or "You want to change the price to $450."
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
    message_id = db_row.get("approval_message_id") or ""
    if not message_id:
        log.debug("order %s has no approval_message_id — replies will post as flat chat messages", order_id)

    raw_draft = db_row.get("invoice_draft")
    if not raw_draft:
        log.warning("order %s has no invoice_draft", order_id)
        return None

    current_draft = json.loads(raw_draft) if isinstance(raw_draft, str) else raw_draft

    # Guard: condo-rejected orders cannot be approved — reply and skip
    if "condo_rejected" in current_draft.get("flags", []):
        log.info("order %s is condo-rejected — skipping approval scan", order_id)
        # Post one-time clarification if there's a reply mentioning this order
        all_check = get_chat_messages(limit=40)
        for m in all_check:
            if not m["is_app"] and str(order_id) in m["text"]:
                already = get_processed_reply_ids(order_id)
                if m["id"] not in already:
                    mark_reply_processed(order_id, m["id"])
                    post_chat_reply(
                        message_id,
                        f"🚫 Order <strong>#{order_id}</strong> was rejected as a condo order — "
                        f"no land parcel to survey. Cannot approve. "
                        f"Contact @Robert @Ryan if this needs manual review."
                    )
                    break
        return None
    raw_sources   = db_row.get("data_sources")
    data_sources  = json.loads(raw_sources) if isinstance(raw_sources, str) else (raw_sources or {})

    already_processed = get_processed_reply_ids(order_id)

    # In group chat, team members reply as flat messages (not thread replies).
    # Match messages that mention the full order_id OR its last 6 digits (e.g. "1787" for 1000271787).
    all_msgs = get_chat_messages(limit=80)
    order_str    = str(order_id)
    order_suffix = order_str[-6:]
    replies = [
        m for m in all_msgs
        if not m["is_app"] and (
            order_str in m["text"] or
            bool(re.search(r'\b' + re.escape(order_suffix) + r'\b', m["text"]))
        )
    ]
    if not replies:
        log.debug("no chat messages mentioning order=%s", order_id)
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
            log.warning("REJECTED reply from unapproved sender=%s email=%s order=%s",
                        sender, sender_email, order_id)
            mark_reply_processed(order_id, reply_id)
            continue

        parsed = _ai_parse_instruction(text, current_draft, order_id)
        action = parsed.get("action") or "question"
        learned_rule = parsed.get("learned_rule", "")
        confidence = parsed.get("confidence", "HIGH")
        status_msg = parsed.get("status_message", "")

        log.info("order=%s sender=%s action=%s confidence=%s text=%r",
                 order_id, sender, action, confidence, text[:120])

        if action == "ignore":
            log.warning("LLM classified reply as IGNORE order=%s sender=%s text=%r",
                        order_id, sender, text[:200])
            mark_reply_processed(order_id, reply_id)
            continue

        mark_reply_processed(order_id, reply_id)

        # For MEDIUM confidence: post what was understood before acting so the user can correct
        if confidence == "MEDIUM" and status_msg and action not in ("question",):
            post_chat_reply(
                message_id,
                f"💬 I think I understood: <em>{status_msg}</em> Proceeding — reply to correct me if that's wrong."
            )

        if action == "approve":
            email_override = parsed.get("email_override")

            # Resolve sender's actual email if they asked "send to me"
            override_email = ""
            if email_override == "sender":
                first = sender.strip().lower().split()[0] if sender.strip() else ""
                override_email = APPROVED_SENDER_EMAIL_MAP.get(first) or sender_email

            # Embed override into the draft JSON so A6 can pick it up
            draft_to_save = current_draft
            if override_email:
                draft_to_save = json.loads(json.dumps(current_draft))
                draft_to_save["email_override_to"] = override_email

            save_order_state(
                order_id,
                status="invoice_approved",
                approved_by=sender,
                **({} if not override_email else {"invoice_draft": json.dumps(draft_to_save, default=str)}),
            )
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

            if override_email:
                post_chat_reply(
                    message_id,
                    f"✅ <strong>Invoice approved by {sender}.</strong> "
                    f"Email will be sent to you (<strong>{override_email}</strong>) — not to the client."
                )
            else:
                post_chat_reply(message_id, f"✅ <strong>Invoice approved by {sender}.</strong> Sending to client shortly...")
            log.info("invoice approved order=%s by=%s override_email=%r", order_id, sender, override_email)
            return "invoice_approved"

        elif action == "hold":
            save_order_state(order_id, status="on_hold")
            log_decision(
                AGENT_NAME, "invoice_on_hold",
                order_id=order_id,
                reason=f"Held by {sender} via Teams thread",
                model_used=HUMAN_GATE_MODEL,
            )
            post_chat_reply(message_id, f"⏸️ <strong>Invoice held by {sender}.</strong> Will skip this cycle. Reply APPROVE or REJECT when ready.")
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
            post_chat_reply(message_id, f"❌ <strong>Invoice rejected.</strong> Reason: {reason}<br>Will not send to client.")
            log.info("invoice rejected order=%s by=%s reason=%s", order_id, sender, reason)
            return "invoice_rejected"

        elif action == "modify":
            mod_count = increment_modification_count(order_id)

            if mod_count > MAX_INVOICE_MODIFICATIONS:
                save_order_state(order_id, status="invoice_needs_human")
                post_chat_reply(
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
            link = f"{FTF_ORDER_URL}/?order={order_id}"
            reply_html = _build_updated_draft_post(order_id, updated_draft, mod_count, link)
            post_chat_reply(message_id, reply_html)

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
            if confidence == "LOW":
                q_text += "<br>@Robert @Ryan — help needed with this one."
            post_chat_reply(message_id, f"❓ {q_text}")
            log.info("clarification requested order=%s confidence=%s", order_id, confidence)
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


# Matches common approval/rejection keywords for orphan reply detection
_ACTION_KEYWORDS = re.compile(
    r'\b(approve|approved|reject|rejected|hold|send it|looks good|go ahead|ok|okay)\b',
    re.IGNORECASE,
)


def _handle_orphan_replies(all_pending_orders: list[dict]) -> None:
    """Handle action messages that mention no specific order_id.

    If 1 order is pending and the reply is a clear simple action → handle it.
    If multiple orders pending → post a clarifying question tagging @Robert @Ryan.
    """
    if not all_pending_orders:
        return

    pending_ids      = [str(row["order_id"]) for row in all_pending_orders]
    pending_suffixes = {str(oid)[-6:] for oid in pending_ids}

    all_msgs = get_chat_messages(limit=80)
    already  = get_processed_reply_ids("__orphan__")

    for msg in all_msgs:
        if msg["is_app"] or msg["id"] in already:
            continue

        text = msg["text"]

        # Skip messages already handled by process_order_replies (mention a known order)
        if any(oid in text for oid in pending_ids):
            continue
        if any(bool(re.search(r'\b' + re.escape(sfx) + r'\b', text)) for sfx in pending_suffixes):
            continue

        if not _ACTION_KEYWORDS.search(text):
            continue

        sender       = msg["sender"]
        sender_email = msg.get("sender_email", "")
        if not _is_approved_sender(sender, sender_email):
            continue

        mark_reply_processed("__orphan__", msg["id"])

        def _reply(mid: str, html: str) -> None:
            """Post to the order's message if we have its ID, else post as new chat message."""
            if mid:
                post_chat_reply(mid, html)
            else:
                post_chat_message(html, subject="")

        if len(all_pending_orders) == 1:
            target_row = all_pending_orders[0]
            target_id  = pending_ids[0]
            message_id = target_row.get("approval_message_id") or ""

            try:
                current_draft = json.loads(target_row.get("invoice_draft") or "{}")
            except Exception:
                current_draft = {}

            parsed     = _ai_parse_instruction(text, current_draft, target_id)
            action     = parsed.get("action", "question")
            confidence = parsed.get("confidence", "LOW")

            log.info("orphan reply order=%s sender=%s action=%s confidence=%s text=%r",
                     target_id, sender, action, confidence, text[:80])

            if action in ("approve", "reject", "hold") and confidence == "HIGH":
                if action == "approve":
                    save_order_state(target_id, status="invoice_approved", approved_by=sender)
                    _reply(message_id, f"✅ <strong>Invoice approved by {sender}.</strong> Sending to client shortly...")
                elif action == "reject":
                    reason = parsed.get("reject_reason") or text
                    save_order_state(target_id, status="invoice_rejected")
                    _reply(message_id, f"❌ <strong>Invoice rejected.</strong> Reason: {reason}")
                elif action == "hold":
                    save_order_state(target_id, status="on_hold")
                    _reply(message_id, f"⏸️ <strong>Invoice held by {sender}.</strong> Reply APPROVE {target_id} or REJECT {target_id} when ready.")
            else:
                _reply(
                    message_id,
                    f"💬 Looks like you're responding about order <strong>#{target_id}</strong>.<br>"
                    f"Please include the order number so I process it correctly, e.g.:<br>"
                    f"<code>APPROVE {target_id}</code> or <code>REJECT {target_id} [reason]</code>"
                )
        else:
            # Show the 5 most recently posted orders — most likely what the user just saw in Teams
            recent = sorted(
                all_pending_orders,
                key=lambda r: r.get("draft_posted_at") or "",
                reverse=True,
            )[:5]
            recent_ids  = [str(r["order_id"]) for r in recent]
            order_lines = "<br>".join(
                f"&nbsp;&nbsp;• <code>{r['order_id']}</code> — {r.get('client_name','?')} · {r.get('property_address','?')[:40]}"
                for r in recent
            )
            post_chat_message(
                f"❓ <strong>Which order?</strong> You said <em>\"{text[:60]}\"</em> but didn't include an order number.<br>"
                f"Most recent orders waiting for approval:<br>{order_lines}<br><br>"
                f"Reply with: <code>APPROVE {recent_ids[0]}</code> or <code>REJECT {recent_ids[0]} [reason]</code>",
                subject="",
            )


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

    # Handle messages with no order_id (user replied without specifying which order)
    try:
        _handle_orphan_replies(orders)
    except Exception as exc:
        log.warning("orphan reply handler failed: %s", exc)

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
