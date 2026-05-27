"""Agent 17 — Statement Sender

Delivers reviewed monthly statements:
  1. Email — Excel + PDF attachments to master billing contact
                (fallback: customer_email from most recent order)
  2. Teams  — delivery confirmation to Ryan, Wyatt, Jessica

Marks statement status='sent' on success.
"""

import os
import smtplib
from datetime import date, datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from config.settings import (
    SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER,
    TEAMS_WEBHOOK_URL,
)
from core.db import get_generated_statements, log_decision, update_statement_status
from core.logger import get_logger

logger = get_logger(__name__)

_TEAMS_COLOR = "00B050"  # green — delivery confirmation
_INTERNAL_CC = ["Ryan", "Wyatt", "Jessica"]


def _get_reviewed_statements(statement_month):
    """Re-use get_generated_statements but query 'reviewed' status directly."""
    from core.db import _get_cursor
    with _get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM monthly_statements
            WHERE statement_month = %s AND status = 'reviewed'
            ORDER BY client_email ASC
            """,
            (statement_month,),
        )
        return [dict(row) for row in cur.fetchall()]


def _send_email(to_email: str, statement_month: date,
                excel_path: str, pdf_path: str) -> None:
    if not SMTP_HOST:
        logger.warning("SMTP_HOST not set — skipping email for %s", to_email)
        return

    msg = MIMEMultipart()
    msg["From"]    = SMTP_FROM
    msg["To"]      = to_email
    msg["Subject"] = f"NexGen Surveying — Monthly Statement {statement_month.strftime('%B %Y')}"

    body = (
        f"Dear Client,\n\n"
        f"Please find attached your monthly statement for {statement_month.strftime('%B %Y')}.\n\n"
        f"The statement includes all survey orders for this period along with payment status "
        f"and any outstanding balance.\n\n"
        f"If you have any questions, please contact us at info@nexgensurveying.com.\n\n"
        f"Thank you for your business,\n"
        f"NexGen Land Surveying"
    )
    msg.attach(MIMEText(body, "plain"))

    for filepath in (excel_path, pdf_path):
        if filepath and os.path.exists(filepath):
            with open(filepath, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(filepath)}",
            )
            msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    logger.info("statement emailed to=%s month=%s", to_email, statement_month)


def _send_teams_notification(client_email: str, statement_month: date,
                              order_count: int, total_amount: float) -> None:
    if not TEAMS_WEBHOOK_URL:
        logger.warning("TEAMS_WEBHOOK_URL not set — skipping Teams notification")
        return

    title = f"Statement Delivered — {statement_month.strftime('%B %Y')}"
    body  = (
        f"**Client:** {client_email}  \n"
        f"**Period:** {statement_month.strftime('%B %Y')}  \n"
        f"**Orders:** {order_count}  \n"
        f"**Total Invoiced:** ${total_amount:,.2f}  \n"
        f"**Delivered to:** {client_email}  \n"
        f"**CC (internal):** {', '.join(_INTERNAL_CC)}"
    )
    payload = {
        "@type":      "MessageCard",
        "@context":   "https://schema.org/extensions",
        "themeColor": _TEAMS_COLOR,
        "summary":    title,
        "title":      title,
        "text":       body,
    }
    try:
        httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=15).raise_for_status()
        logger.info("teams notification sent client=%s month=%s", client_email, statement_month)
    except Exception as exc:
        logger.error("teams notification failed client=%s: %s", client_email, exc)


def run(statement_month: date | None = None) -> dict:
    if statement_month is None:
        today = date.today()
        if today.month == 1:
            statement_month = date(today.year - 1, 12, 1)
        else:
            statement_month = date(today.year, today.month - 1, 1)

    statements = _get_reviewed_statements(statement_month)
    sent = skipped = 0

    for stmt in statements:
        client_email  = stmt["client_email"]
        total_amount  = float(stmt.get("total_amount") or 0)

        try:
            _send_email(
                to_email=client_email,
                statement_month=statement_month,
                excel_path=stmt.get("excel_path") or "",
                pdf_path=stmt.get("pdf_path") or "",
            )
            _send_teams_notification(
                client_email=client_email,
                statement_month=statement_month,
                order_count=stmt["order_count"],
                total_amount=total_amount,
            )
            update_statement_status(
                client_email=client_email,
                statement_month=statement_month,
                status="sent",
                sent_at=datetime.now(timezone.utc),
            )
            log_decision(
                agent_name="agent_17_statement_sender",
                decision="statement_sent",
                reason=f"email + Teams delivered for {statement_month}",
                output_summary=f"client={client_email} orders={stmt['order_count']}",
            )
            sent += 1
            logger.info("statement sent client=%s", client_email)

        except Exception as exc:
            update_statement_status(client_email, statement_month, "failed")
            log_decision(
                agent_name="agent_17_statement_sender",
                decision="statement_send_failed",
                reason=str(exc),
                output_summary=f"client={client_email}",
            )
            skipped += 1
            logger.error("statement send failed client=%s: %s", client_email, exc)

    logger.info("agent_17_statement_sender: sent=%d skipped=%d", sent, skipped)
    return {"sent": sent, "skipped": skipped}


if __name__ == "__main__":
    print(run())
