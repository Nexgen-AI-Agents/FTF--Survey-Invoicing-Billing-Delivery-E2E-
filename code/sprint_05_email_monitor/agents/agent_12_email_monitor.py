"""Agent 12 — Email Monitor (Quote Approval)

I-061: Ryan (2026-05-26): "There should be an agent monitoring the info emails.
Any email that says convert/approved/go ahead — read the whole email, figure out
what it's approving, move to pending, notify team."

Monitors nesa@nexgenlogix.com for customer approval emails.
When a customer replies to their quote with intent to proceed:
  1. AI reads the full email to identify which order/property it refers to
  2. Moves the order from quote->pending status in FTF CRM (or our DB)
  3. Notifies the NexGen team via Teams

Approval keywords (any match triggers AI reading of full email):
  "approved", "approve", "go ahead", "go-ahead", "move forward",
  "please proceed", "convert", "yes please", "let's go", "confirmed",
  "i'd like to proceed", "ready to proceed"

Hard rules:
  - Refund intent detected -> route to Jessica immediately (I-063)
  - No order/property identifiable -> reply asking for order# or address
  - Ambiguous email -> flag for human review, do not auto-convert

Email integration: IMAP (SMTP settings in .env).
Requires: IMAP_HOST, IMAP_USER, IMAP_PASSWORD environment variables.
"""

import os
import re
import sys
import imaplib
import email as email_lib
from datetime import datetime, timezone
from email.header import decode_header

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.models import CLASSIFIER_MODEL
from config.settings import TEAMS_WEBHOOK_URL
from core.claude_client import call as llm_call
from core.db import get_order_by_id, save_order_state, log_decision
from core.exceptions import AgentError
from core.logger import get_logger
from core.refund_guard import detect_refund_intent, alert_jessica_refund

AGENT_NAME = "agent_12_email_monitor"
log = get_logger(AGENT_NAME)

IMAP_HOST     = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT     = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER     = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
MONITOR_EMAIL = "nesa@nexgenlogix.com"

_APPROVAL_KEYWORDS = [
    "approved", "approve", "go ahead", "go-ahead", "move forward",
    "please proceed", "convert", "yes please", "let's go", "confirmed",
    "i'd like to proceed", "ready to proceed", "i am ready", "we are ready",
    "i want to proceed", "we want to proceed",
]


def _has_approval_intent(text: str) -> bool:
    """Quick keyword scan — if any approval keyword found, send to AI for full analysis."""
    lower = text.lower()
    return any(kw in lower for kw in _APPROVAL_KEYWORDS)


def _extract_email_body(msg) -> str:
    """Extract plain text body from email.message object."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")
    return body.strip()


def _decode_header_field(value: str) -> str:
    parts = decode_header(value or "")
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _ai_identify_order(from_addr: str, subject: str, body: str) -> dict:
    """Use Claude to identify which order/property this email refers to.

    Returns dict with:
      - order_id: str or None
      - property_address: str or None
      - intent: "approve" | "refund" | "inquiry" | "unclear"
      - confidence: "high" | "medium" | "low"
      - summary: str (brief summary of AI reasoning)
    """
    prompt = f"""You are reviewing an email sent to nesa@nexgenlogix.com.

Email From: {from_addr}
Email Subject: {subject}
Email Body:
---
{body[:2000]}
---

Analyze this email and respond in this exact JSON format (no markdown, just JSON):
{{
  "order_id": "<order ID if mentioned, e.g. '1000123456', or null>",
  "property_address": "<property address if mentioned, or null>",
  "intent": "<one of: approve | refund | inquiry | unclear>",
  "confidence": "<one of: high | medium | low>",
  "summary": "<one sentence: what is the customer asking/confirming?>"
}}

Rules:
- intent=approve: customer is confirming they want to proceed with the survey/quote
- intent=refund: customer is asking for a refund or money back
- intent=inquiry: customer is asking a question, not approving
- intent=unclear: cannot determine from email content
- confidence=high: order ID or address clearly stated; intent unmistakable
- confidence=medium: intent clear but order not precisely identified
- confidence=low: ambiguous or missing key information"""

    try:
        result_str = llm_call(
            model=CLASSIFIER_MODEL,
            system="You are an email classification assistant. Respond only with valid JSON.",
            user=prompt,
            max_tokens=200,
        ).strip()
        import json
        return json.loads(result_str)
    except Exception as exc:
        log.warning("AI email analysis failed: %s", exc)
        return {
            "order_id": None,
            "property_address": None,
            "intent": "unclear",
            "confidence": "low",
            "summary": f"AI analysis failed: {exc}",
        }


def _notify_team(from_addr: str, order_id: str, analysis: dict) -> None:
    """Send Teams notification about a converted quote."""
    if not TEAMS_WEBHOOK_URL:
        log.warning("TEAMS_WEBHOOK_URL not set — skipping team notification")
        return
    import httpx
    title = f"Quote Conversion: Customer Approved — Order {order_id or 'TBD'}"
    body = (
        f"**Customer:** {from_addr}  \n"
        f"**Order ID:** {order_id or 'Not identified — see email'}  \n"
        f"**Property:** {analysis.get('property_address') or 'Not stated'}  \n"
        f"**AI Summary:** {analysis.get('summary', '')}  \n"
        f"**Confidence:** {analysis.get('confidence', 'unknown')}  \n\n"
        f"**Action:** Quote moved to Pending — team notified."
    )
    payload = {
        "@type": "MessageCard", "@context": "http://schema.org/extensions",
        "themeColor": "00B050", "summary": title, "title": title, "text": body,
    }
    try:
        httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=15)
    except Exception as exc:
        log.error("teams notify failed: %s", exc)


def process_approval_email(from_addr: str, subject: str, body: str) -> dict:
    """Process one customer email that may contain quote approval.

    Returns:
      {"action": "converted" | "refund_routed" | "flagged" | "skipped",
       "order_id": str | None, "reason": str}
    """
    # I-063: refund check first
    if detect_refund_intent(body) or detect_refund_intent(subject):
        alert_jessica_refund(f"email:{from_addr}", f"Subject: {subject}\n{body[:200]}")
        log_decision(AGENT_NAME, "refund_detected", reason=f"from={from_addr}", input_summary=subject)
        return {"action": "refund_routed", "order_id": None, "reason": "refund intent detected"}

    # Quick keyword check — only deep-analyse if approval keyword present
    combined = f"{subject} {body}"
    if not _has_approval_intent(combined):
        return {"action": "skipped", "order_id": None, "reason": "no approval keywords"}

    # Full AI analysis
    analysis = _ai_identify_order(from_addr, subject, body)
    intent = analysis.get("intent", "unclear")
    confidence = analysis.get("confidence", "low")
    order_id = analysis.get("order_id")

    if intent == "refund":
        alert_jessica_refund(f"email:{from_addr}", f"Subject: {subject}\n{body[:200]}")
        return {"action": "refund_routed", "order_id": order_id, "reason": "AI detected refund intent"}

    if intent != "approve":
        log.info("email from %s classified as intent=%s — skipping", from_addr, intent)
        return {"action": "skipped", "order_id": order_id, "reason": f"intent={intent}"}

    if confidence == "low" or (not order_id and not analysis.get("property_address")):
        log.warning("approval email from %s but low confidence — flagging for human", from_addr)
        log_decision(
            AGENT_NAME, "flagged",
            reason=f"approval detected but low confidence or no order ID — from={from_addr}",
            input_summary=analysis.get("summary"),
        )
        return {
            "action": "flagged",
            "order_id": order_id,
            "reason": "approval confirmed but order not identifiable — human review required",
        }

    # High/medium confidence approval with identifiable order
    if order_id:
        existing = get_order_by_id(order_id)
        if existing:
            save_order_state(order_id, status="approved")
            log_decision(
                AGENT_NAME, "quote_approved",
                order_id=order_id,
                reason=f"customer email approval — from={from_addr}",
                input_summary=analysis.get("summary"),
                output_summary="status -> approved",
            )
            _notify_team(from_addr, order_id, analysis)
            log.info("quote approved order=%s from=%s", order_id, from_addr)
            return {"action": "converted", "order_id": order_id, "reason": "order identified and approved"}

    # No DB record for order_id — notify team to handle manually
    log_decision(
        AGENT_NAME, "approval_no_db_match",
        reason=f"customer approved but no DB record found — order={order_id} from={from_addr}",
        input_summary=analysis.get("summary"),
    )
    _notify_team(from_addr, order_id, analysis)
    return {
        "action": "flagged",
        "order_id": order_id,
        "reason": "customer approved but order not in DB — manual lookup required",
    }


def fetch_unread_emails() -> list[dict]:
    """Connect to IMAP and fetch unread emails from inbox."""
    if not IMAP_USER or not IMAP_PASSWORD:
        raise AgentError("IMAP_USER and IMAP_PASSWORD must be set to monitor email")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("INBOX")

        _, data = mail.search(None, "UNSEEN")
        email_ids = data[0].split()
        log.info("found %d unread emails in inbox", len(email_ids))

        emails = []
        for eid in email_ids:
            _, msg_data = mail.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            from_addr = _decode_header_field(msg.get("From", ""))
            subject   = _decode_header_field(msg.get("Subject", ""))
            body      = _extract_email_body(msg)
            emails.append({
                "email_id": eid.decode(),
                "from": from_addr,
                "subject": subject,
                "body": body,
            })
            # Mark as read
            mail.store(eid, "+FLAGS", "\\Seen")

        mail.close()
        mail.logout()
        return emails

    except imaplib.IMAP4.error as exc:
        raise AgentError(f"IMAP connection failed: {exc}") from exc


def run() -> dict:
    """Fetch unread emails and process any with quote approval intent.

    Returns summary: {processed, converted, refund_routed, flagged, skipped}
    """
    emails = fetch_unread_emails()
    summary = {"processed": 0, "converted": 0, "refund_routed": 0, "flagged": 0, "skipped": 0}

    for em in emails:
        result = process_approval_email(em["from"], em["subject"], em["body"])
        action = result.get("action", "skipped")
        summary["processed"] += 1
        summary[action] = summary.get(action, 0) + 1
        log.info("email processed from=%s action=%s order=%s", em["from"], action, result.get("order_id"))

    log.info("email_monitor complete: %s", summary)
    return summary


if __name__ == "__main__":
    result = run()
    print(result)
