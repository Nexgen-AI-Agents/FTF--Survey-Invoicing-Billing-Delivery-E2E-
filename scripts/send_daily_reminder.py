"""Daily approval reminder — email edition.

Reads pipeline_state Excel (data/invoice_pipeline_state.xlsx) for orders
with status=invoice_draft_posted and sends a plain-text summary email to
NOTIFICATION_TO_EMAILS so approvers know what's waiting in the spreadsheet.

Run: GitHub Actions daily at 9:00 AM ET (Mon–Fri)
"""

import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.excel_db import get_orders_by_status, get_orders_awaiting_invoice_approval
from core.logger import get_logger

log = get_logger("send_daily_reminder")

SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", "nesa@nexgenlogix.com")
TO_EMAILS_RAW = os.getenv("NOTIFICATION_TO_EMAILS", "")
FTF_ORDER_URL = os.getenv("FTF_ORDER_URL", "https://stage.fieldtofinish.jobs/order")


def _build_email(pending: list[dict], awaiting: list[dict]) -> tuple[str, str]:
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    total_pending = len(pending) + len(awaiting)

    if total_pending == 0:
        subject = "Daily Invoice Review — No pending orders"
        body    = f"Good morning,\n\nNo orders are currently waiting for approval. All clear!\n\nDate: {today}\n"
        return subject, body

    subject = f"Daily Invoice Review — {total_pending} order(s) need attention"

    lines = [
        f"Good morning,",
        f"",
        f"As of {today}, the following orders need your review in the approval spreadsheet:",
        f"(FTF-Invoicing Agent.xlsx on nesa@nexgenlogix.com's OneDrive)",
        f"",
    ]

    if pending:
        lines.append(f"AWAITING APPROVAL ({len(pending)} orders):")
        for row in pending:
            oid     = row.get("order_id", "?")
            client  = row.get("client_name", "Unknown")
            address = (row.get("property_address") or "")[:50]
            amount  = row.get("estimate_amount") or 0
            posted  = row.get("draft_posted_at") or ""
            link    = f"{FTF_ORDER_URL}/?order={oid}"
            lines.append(f"  • Order {oid} | {client} | {address} | ${amount:,.2f} | Posted: {posted}")
            lines.append(f"    {link}")
        lines.append("")

    if awaiting:
        lines.append(f"ON HOLD / MODIFICATION REQUESTED ({len(awaiting)} orders):")
        for row in awaiting:
            oid    = row.get("order_id", "?")
            client = row.get("client_name", "Unknown")
            status = row.get("status", "")
            lines.append(f"  • Order {oid} | {client} | Status: {status}")
        lines.append("")

    lines += [
        "To approve/reject/hold: open the Excel sheet, change the Status column,",
        "then Power Automate will trigger the pipeline automatically.",
        "",
        "-- NexGen Invoice Bot",
    ]

    return subject, "\n".join(lines)


def main() -> None:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        log.error("SMTP not configured — set SMTP_HOST, SMTP_USER, SMTP_PASSWORD")
        sys.exit(1)

    to_list = [e.strip() for e in TO_EMAILS_RAW.split(",") if e.strip()]
    if not to_list:
        log.error("NOTIFICATION_TO_EMAILS not set — no recipients")
        sys.exit(1)

    pending  = get_orders_by_status("invoice_draft_posted")
    awaiting = [
        r for r in get_orders_awaiting_invoice_approval()
        if r.get("status") != "invoice_draft_posted"
    ]

    subject, body = _build_email(pending, awaiting)
    log.info("sending reminder: %d pending, %d awaiting, to=%s", len(pending), len(awaiting), to_list)

    msg = MIMEMultipart("alternative")
    msg["Subject"]  = subject
    msg["From"]     = SMTP_FROM
    msg["To"]       = ", ".join(to_list)
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, to_list, msg.as_string())

    log.info("daily reminder sent to %s", to_list)
    print(f"Reminder sent: {subject}")


if __name__ == "__main__":
    main()
