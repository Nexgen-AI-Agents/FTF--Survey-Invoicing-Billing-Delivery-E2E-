"""Agent A2 — Data Collector (Invoice Pipeline)

For each order queued by A1 (status=invoice_needed), this agent collects
all available information from 3 sources:

  1. FTF API      — order details, client details, service type, property info
  2. Email inbox  — nesa@nexgenlogix.com: find emails matching this order
  3. Teams chat   — group chat: find staff messages about this order/property

Output: a structured "order packet" saved to processed_orders.data_sources
Each field has a confidence score: HIGH (confirmed) / MEDIUM (inferred) / LOW (missing).

Match logic for email + Teams:
  - property address (best match — most specific)
  - client name
  - order ID / order number

Status flow: invoice_needed → data_collected
"""

import json
import os
import re
import sys
import imaplib
import email as email_lib
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD
from config.models import CLASSIFIER_MODEL
from core.claude_client import call as llm_call
from core.db import get_orders_by_status, get_order_by_id, save_order_state, log_decision
from core.exceptions import AgentError
from core.ftf_client import get_order, get_customer
from core.logger import get_logger
from core.teams_graph_client import get_chat_messages

AGENT_NAME = "agent_a2_data_collector"
log = get_logger(AGENT_NAME)

# How far back to look for matching emails / Teams messages
LOOKBACK_DAYS = 90


def _decode_header_field(value: str) -> str:
    parts = decode_header(value or "")
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _extract_email_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")
    return body.strip()


def _text_matches_order(text: str, property_address: str, client_name: str, order_id: str) -> bool:
    """Quick check: does this text mention this order?"""
    lower = text.lower()
    if property_address and len(property_address) > 5:
        # Match on partial address — first meaningful word (usually house number or street)
        addr_parts = property_address.lower().split()
        if len(addr_parts) >= 2 and addr_parts[0].isdigit():
            # "123 Main St" → check for "123 main"
            if f"{addr_parts[0]} {addr_parts[1]}" in lower:
                return True
        if property_address.lower() in lower:
            return True
    if client_name and len(client_name) > 3:
        if client_name.lower() in lower:
            return True
    if order_id and order_id in text:
        return True
    return False


def _fetch_matching_emails(
    property_address: str,
    client_name: str,
    order_id: str,
) -> list[dict]:
    """Search info@ inbox for emails related to this order.

    Returns list of {from, subject, body, date} dicts.
    Falls back to empty list if IMAP not configured.
    """
    if not IMAP_USER or not IMAP_PASSWORD:
        log.warning("IMAP not configured — skipping email search")
        return []

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("INBOX")

        # Search recent emails (IMAP SINCE date)
        since_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
        _, data = mail.search(None, f"SINCE {since_date}")
        email_ids = data[0].split()

        matching = []
        for eid in email_ids:
            try:
                _, msg_data = mail.fetch(eid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                subject = _decode_header_field(msg.get("Subject", ""))
                from_addr = _decode_header_field(msg.get("From", ""))
                body = _extract_email_body(msg)
                combined = f"{subject} {body}"

                if _text_matches_order(combined, property_address, client_name, order_id):
                    matching.append({
                        "from": from_addr,
                        "subject": subject,
                        "body": body[:3000],
                        "date": msg.get("Date", ""),
                    })
            except Exception as exc:
                log.debug("email fetch error eid=%s: %s", eid, exc)

        mail.close()
        mail.logout()
        log.info("email search complete matches=%d", len(matching))
        return matching

    except imaplib.IMAP4.error as exc:
        log.warning("IMAP connection failed: %s", exc)
        return []
    except Exception as exc:
        log.warning("email search failed: %s", exc)
        return []


def _fetch_matching_teams_messages(
    property_address: str,
    client_name: str,
    order_id: str,
) -> list[dict]:
    """Search the Teams group chat for messages related to this order.

    Returns list of {sender, text, date} dicts.
    """
    try:
        messages = get_chat_messages(limit=200)
        cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
        matching = []

        for msg in messages:
            if msg.get("is_app"):
                continue
            if msg["created_at_dt"] < cutoff:
                continue
            if _text_matches_order(msg["text"], property_address, client_name, order_id):
                matching.append({
                    "sender": msg["sender"],
                    "text": msg["text"][:2000],
                    "date": msg["created_at_dt"].isoformat(),
                })

        log.info("teams search complete matches=%d", len(matching))
        return matching

    except AgentError as exc:
        log.warning("Teams chat search failed: %s", exc)
        return []


def _ai_extract_order_packet(
    ftf_order: dict,
    ftf_customer: dict,
    emails: list[dict],
    teams_messages: list[dict],
) -> dict:
    """Use Claude to synthesize all sources into a structured order packet.

    Returns a dict with invoice-relevant fields and confidence scores.
    """
    email_block = ""
    for i, em in enumerate(emails[:5], 1):
        email_block += f"\n--- Email {i} from {em['from']} ({em['date']}) ---\n"
        email_block += f"Subject: {em['subject']}\n{em['body'][:1000]}\n"

    teams_block = ""
    for i, tm in enumerate(teams_messages[:10], 1):
        teams_block += f"\n--- Teams message {i} from {tm['sender']} ({tm['date']}) ---\n"
        teams_block += f"{tm['text'][:500]}\n"

    prompt = f"""You are extracting invoice details for a land surveying order at NexGen Surveying.

FTF ORDER DATA:
{json.dumps(ftf_order, indent=2, default=str)[:2000]}

FTF CUSTOMER DATA:
{json.dumps(ftf_customer, indent=2, default=str)[:1000]}

MATCHING EMAILS ({len(emails)} found):
{email_block or "(none found)"}

MATCHING TEAMS MESSAGES ({len(teams_messages)} found):
{teams_block or "(none found)"}

Extract the following fields. For each field, rate confidence as:
  HIGH   = explicitly stated in email/Teams or clear in FTF data
  MEDIUM = inferred from context
  LOW    = missing or unclear — needs human input

Return ONLY valid JSON, no markdown:
{{
  "client_name": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "client_email": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "property_address": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "property_county": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "services_requested": {{"value": ["service1", "service2"], "confidence": "HIGH|MEDIUM|LOW", "notes": "..."}},
  "special_requirements": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "lot_size_acres": {{"value": null, "confidence": "LOW"}},
  "property_features": {{"value": {{}}, "confidence": "LOW", "notes": "pool, shed, driveways etc if mentioned"}},
  "client_tier": {{"value": "residential|b2b|unknown", "confidence": "HIGH|MEDIUM|LOW"}},
  "urgency": {{"value": "normal|rush|unknown", "confidence": "HIGH|MEDIUM|LOW"}},
  "source_of_truth": "ftf_only|email_primary|teams_primary|mixed",
  "gaps": ["list of information that is missing and needs human input"],
  "summary": "one sentence describing this order"
}}"""

    try:
        result_str = llm_call(
            model=CLASSIFIER_MODEL,
            system="You are an invoice data extraction assistant for a land surveying company. Return only valid JSON.",
            user=prompt,
            max_tokens=800,
        ).strip()

        if result_str.startswith("```"):
            result_str = re.sub(r"^```[a-z]*\n?", "", result_str).rstrip("`").strip()

        return json.loads(result_str)

    except Exception as exc:
        log.warning("AI packet extraction failed: %s", exc)
        return {
            "client_name":        {"value": ftf_customer.get("name") or ftf_order.get("customer_name", ""), "confidence": "MEDIUM"},
            "client_email":       {"value": ftf_order.get("customer_email", ""), "confidence": "MEDIUM"},
            "property_address":   {"value": ftf_order.get("property_address") or ftf_order.get("address", ""), "confidence": "MEDIUM"},
            "property_county":    {"value": ftf_order.get("county") or ftf_order.get("property_county", ""), "confidence": "MEDIUM"},
            "services_requested": {"value": [ftf_order.get("service_type", "Unknown")], "confidence": "LOW", "notes": "AI extraction failed — review manually"},
            "special_requirements": {"value": "", "confidence": "LOW"},
            "lot_size_acres":     {"value": None, "confidence": "LOW"},
            "property_features":  {"value": {}, "confidence": "LOW", "notes": ""},
            "client_tier":        {"value": "unknown", "confidence": "LOW"},
            "urgency":            {"value": "unknown", "confidence": "LOW"},
            "source_of_truth":    "ftf_only",
            "gaps":               ["AI extraction failed — all fields need manual review"],
            "summary":            f"Order {ftf_order.get('order_id', '')} — extraction failed",
        }


def collect_for_order(order_id: str) -> dict:
    """Run full data collection for one order.

    Returns the assembled order packet.
    """
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"collect_for_order: order {order_id} not in processed_orders")

    property_address = db_row.get("property_address", "")
    client_name      = db_row.get("client_name", "")
    customer_email   = db_row.get("customer_email", "")

    # 1 — FTF API
    try:
        ftf_order = get_order(order_id)
    except Exception as exc:
        log.warning("FTF order fetch failed order=%s: %s", order_id, exc)
        ftf_order = {"order_id": order_id}

    # Enrich address / client from FTF if missing in DB
    if not property_address:
        property_address = str(
            ftf_order.get("property_address") or
            ftf_order.get("address") or
            ftf_order.get("site_address") or ""
        )
    if not client_name:
        client_name = str(ftf_order.get("customer_name") or ftf_order.get("client_name") or "")

    customer_id = str(ftf_order.get("customer_id") or ftf_order.get("client_id") or "")
    try:
        ftf_customer = get_customer(customer_id) if customer_id else {}
    except Exception:
        ftf_customer = {}

    # 2 — Email inbox
    emails = _fetch_matching_emails(property_address, client_name, order_id)

    # 3 — Teams chat
    teams_messages = _fetch_matching_teams_messages(property_address, client_name, order_id)

    # 4 — AI synthesis
    packet = _ai_extract_order_packet(ftf_order, ftf_customer, emails, teams_messages)

    # Store metadata about sources
    data_sources = {
        "ftf_order":      ftf_order,
        "ftf_customer":   ftf_customer,
        "emails_found":   len(emails),
        "teams_found":    len(teams_messages),
        "email_snippets": [{"from": e["from"], "subject": e["subject"], "date": e["date"]} for e in emails],
        "teams_snippets": [{"sender": t["sender"], "date": t["date"]} for t in teams_messages],
        "packet":         packet,
    }

    save_order_state(
        order_id,
        status="data_collected",
        invoice_draft=None,
        data_sources=json.dumps(data_sources, default=str),
        client_name=str(packet.get("client_name", {}).get("value") or client_name),
        property_address=str(packet.get("property_address", {}).get("value") or property_address),
        data_collected_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        AGENT_NAME,
        decision="data_collected",
        order_id=order_id,
        reason=(
            f"emails={len(emails)} teams={len(teams_messages)} "
            f"source_of_truth={packet.get('source_of_truth')} "
            f"gaps={len(packet.get('gaps', []))}"
        ),
        input_summary=f"property={property_address[:60]} client={client_name[:40]}",
        output_summary=f"packet built confidence={_min_confidence(packet)}",
        model_used=CLASSIFIER_MODEL,
    )
    log.info("data collected order=%s emails=%d teams=%d", order_id, len(emails), len(teams_messages))
    return packet


def _min_confidence(packet: dict) -> str:
    """Return the lowest confidence level across all packet fields."""
    levels = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    min_level = 3
    for key, val in packet.items():
        if isinstance(val, dict) and "confidence" in val:
            min_level = min(min_level, levels.get(val["confidence"], 1))
    return {3: "HIGH", 2: "MEDIUM", 1: "LOW"}.get(min_level, "LOW")


def run() -> dict:
    """Process all orders with status=invoice_needed.

    Returns summary: {processed, data_collected, errors}
    """
    orders = get_orders_by_status("invoice_needed")
    summary = {"processed": 0, "data_collected": 0, "errors": 0}

    for db_row in orders:
        order_id = db_row["order_id"]
        try:
            collect_for_order(order_id)
            summary["data_collected"] += 1
        except Exception as exc:
            log.error("data collection failed order=%s: %s", order_id, exc)
            summary["errors"] += 1
        summary["processed"] += 1

    log.info("data_collector complete: %s", summary)
    return summary


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="A2 Data Collector — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--order-id", help="Collect for a specific order ID")
    args = parser.parse_args(argv)

    if args.order_id:
        packet = collect_for_order(args.order_id)
        print(json.dumps(packet, indent=2))
    elif args.run_now:
        summary = run()
        print(summary)


if __name__ == "__main__":
    main()
