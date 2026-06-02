"""Agent A6 — Sender v2 (Invoice Pipeline)

Sends a personalized invoice email directly to the client.
This is Phase 1's last step — once sent, the pipeline is done for this order.

Email structure:
  - Personalized greeting using client name
  - Clear list of services + amounts
  - Total
  - NexGen contact info + Google review ask
  - Professional FL PSM tone

Delivery: SMTP (settings from .env) with 6–13 minute random delay
to avoid bulk-send patterns (same behavior as original Agent 08).

Status flow: invoice_finalized → invoice_sent
"""

import json
import os
import random
import smtplib
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import (
    ESTIMATE_DELAY_MIN, ESTIMATE_DELAY_MAX,
    SEND_HOUR_START, SEND_HOUR_END,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM,
)
from core.excel_db import get_orders_by_status, get_order_by_id, save_order_state, log_decision
from core.exceptions import AgentError
from core.logger import get_logger
from core.teams_graph_client import post_channel_reply

AGENT_NAME = "agent_a6_sender_v2"
log = get_logger(AGENT_NAME)

_GOOGLE_REVIEW_URL = os.getenv("GOOGLE_REVIEW_URL", "")
_review_link = (
    f'<a href="{_GOOGLE_REVIEW_URL}">Google review</a>'
    if _GOOGLE_REVIEW_URL
    else "Google review"
)

_NEXGEN_SIGNATURE = f"""
<hr>
<p>
<strong>NexGen Surveying</strong><br>
Licensed Professional Surveyors & Mappers — Florida<br>
Phone: (561) 508-6272 | Email: nesa@nexgenlogix.com<br>
<a href="https://nexgensurveying.com">nexgensurveying.com</a>
</p>
<p><em>
If our service exceeded your expectations, we'd truly appreciate a quick
{_review_link} — it means the world to our small team. Thank you!
</em></p>
"""


def _is_business_hours() -> bool:
    # Use America/New_York to handle EST/EDT automatically — GA runners are UTC
    hour = datetime.now(ZoneInfo("America/New_York")).hour
    return SEND_HOUR_START <= hour < SEND_HOUR_END


def _build_email_html(client_name: str, order_id: str, draft: dict) -> str:
    services = draft.get("services", [])
    total    = draft.get("total_amount", 0)

    first_name = client_name.split()[0] if client_name else "there"

    rows = ""
    for svc in services:
        rows += f"""
<tr>
  <td style="padding:8px;border-bottom:1px solid #eee;">{svc.get('name', '')}</td>
  <td style="padding:8px;border-bottom:1px solid #eee;">{svc.get('description', '')}</td>
  <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">${svc.get('amount', 0):,.2f}</td>
</tr>"""

    return f"""
<html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto;">
<p>Hi {first_name},</p>

<p>Thank you for choosing NexGen Surveying. Please find your invoice details below for order <strong>#{order_id}</strong>.</p>

<table width="100%" style="border-collapse:collapse;margin:20px 0;">
  <thead>
    <tr style="background:#f5f5f5;">
      <th style="padding:10px;text-align:left;">Service</th>
      <th style="padding:10px;text-align:left;">Description</th>
      <th style="padding:10px;text-align:right;">Amount</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
  <tfoot>
    <tr style="font-weight:bold;">
      <td colspan="2" style="padding:10px;">Total</td>
      <td style="padding:10px;text-align:right;">${total:,.2f}</td>
    </tr>
  </tfoot>
</table>

<p>
Payment is due upon completion of the survey. We accept check, ACH, or credit card.
If you have any questions about this invoice, please don't hesitate to reach out.
</p>

{_NEXGEN_SIGNATURE}
</body></html>""".strip()


def _send_smtp(to_email: str, subject: str, html_body: str) -> bool:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        raise AgentError("SMTP not configured — set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_FROM
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())

    return True


def send_for_order(order_id: str, skip_delay: bool = False) -> dict:
    """Send invoice email to client for one finalized order."""
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"send_for_order: order {order_id} not in DB")

    raw_draft = db_row.get("invoice_draft")
    if not raw_draft:
        raise AgentError(f"send_for_order: no invoice_draft for order {order_id}")

    draft        = json.loads(raw_draft) if isinstance(raw_draft, str) else raw_draft
    client_name  = db_row.get("client_name", "")
    client_email = db_row.get("customer_email", "")
    message_id   = db_row.get("approval_message_id")
    approved_by  = db_row.get("approved_by", "Unknown")

    if not client_email:
        raise AgentError(f"send_for_order: no client email for order {order_id}")

    # Business hours check
    if not skip_delay and not _is_business_hours():
        log.info("outside business hours — skipping send for order=%s", order_id)
        return {"sent": False, "reason": "outside_business_hours"}

    # Random delay (human-like)
    if not skip_delay:
        delay = random.randint(ESTIMATE_DELAY_MIN, ESTIMATE_DELAY_MAX)
        log.info("send delay=%ds order=%s", delay, order_id)
        time.sleep(delay)

    html    = _build_email_html(client_name, order_id, draft)
    total   = draft.get("total_amount", 0)
    subject = f"Your Survey Invoice — Order #{order_id} — NexGen Surveying"

    _send_smtp(client_email, subject, html)

    save_order_state(
        order_id,
        status="invoice_sent",
        sent_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        AGENT_NAME,
        decision="invoice_sent",
        order_id=order_id,
        reason=f"Invoice email sent to {client_email} total=${total:.2f}",
        input_summary=f"client={client_name}",
        output_summary=f"to={client_email} total={total}",
        model_used=None,
    )

    # Confirm in Teams channel thread
    if message_id:
        post_channel_reply(
            message_id,
            f"✅ <strong>Email sent to {client_name} ({client_email}), approved by {approved_by}</strong><br>"
            f"Order: {order_id} | Total: ${total:,.2f}"
        )

    log.info("invoice sent order=%s to=%s total=%.2f", order_id, client_email, total)
    return {"sent": True, "to": client_email, "total": total}


def run() -> dict:
    """Send emails for all invoice_finalized orders."""
    orders  = get_orders_by_status("invoice_finalized")
    summary = {"processed": 0, "sent": 0, "skipped": 0, "errors": 0}

    for db_row in orders:
        order_id = db_row["order_id"]
        try:
            result = send_for_order(order_id)
            if result.get("sent"):
                summary["sent"] += 1
            else:
                summary["skipped"] += 1
        except Exception as exc:
            log.error("send failed order=%s: %s", order_id, exc)
            summary["errors"] += 1
        summary["processed"] += 1

    log.info("sender_v2 complete: %s", summary)
    return summary


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="A6 Sender v2 — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--order-id")
    parser.add_argument("--skip-delay", action="store_true")
    args = parser.parse_args(argv)

    if args.order_id:
        result = send_for_order(args.order_id, skip_delay=args.skip_delay)
        print(result)
    elif args.run_now:
        print(run())


if __name__ == "__main__":
    main()
