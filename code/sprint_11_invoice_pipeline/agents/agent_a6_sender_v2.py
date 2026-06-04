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
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import (
    ESTIMATE_DELAY_MIN, ESTIMATE_DELAY_MAX,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM,
    EMAIL_OVERRIDE_ALL,
)
from core.excel_db import get_orders_by_status, get_order_by_id, save_order_state, log_decision
from core.exceptions import AgentError
from core.logger import get_logger

AGENT_NAME = "agent_a6_sender_v2"
log = get_logger(AGENT_NAME)

_SKIP_DELAY = os.getenv("SKIP_SEND_DELAY", "0") == "1"

_GOOGLE_REVIEW_URL = os.getenv("GOOGLE_REVIEW_URL", "")
_review_link = (
    f'<a href="{_GOOGLE_REVIEW_URL}">Google review</a>'
    if _GOOGLE_REVIEW_URL
    else "Google review"
)

_SMTP_FROM_DISPLAY = "Nexgen Land Solutions <nesa@nexgenlogix.com>"
_CONTACT_PHONE     = "(561) 508-6272"
_CONTACT_EMAIL     = "info@nexgensurveying.com"
_CONTACT_WEB       = "nexgensurveying.com"

# Logo — resolved relative to the repo root (4 levels up from this file)
_REPO_ROOT  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_LOGO_PATH  = os.path.join(_REPO_ROOT, "Resources", "Nexgen Land Solutions.png")
_LOGO_CID   = "nexgen_logo"

def _load_logo() -> bytes | None:
    try:
        with open(_LOGO_PATH, "rb") as f:
            return f.read()
    except OSError:
        return None


def _build_email_html(client_name: str, order_id: str, draft: dict, pay_link: str = "") -> str:
    services   = draft.get("services", [])
    total      = draft.get("total_amount", 0)
    first_name = client_name.split()[0] if client_name else "there"

    # Service rows — name on left, amount on right
    svc_rows = ""
    for svc in services:
        name   = svc.get("name", "Service")
        amount = svc.get("amount", 0)
        svc_rows += f"""
<tr style="border-top:1px solid #e8e8e8;">
  <td style="padding:12px 12px;font-size:14px;color:#333;">{name}</td>
  <td style="padding:12px 12px;text-align:right;font-size:14px;color:#333;font-weight:600;">${amount:,.2f}</td>
</tr>"""

    # Pay Now block — shown when a real portal link is available
    if pay_link:
        pay_now_block = f"""
    <!-- Pay Now -->
    <tr><td style="padding:20px 32px 0;text-align:center;">
      <a href="{pay_link}"
         style="display:inline-block;width:100%;box-sizing:border-box;padding:18px 0;background:#1e7e34;color:#ffffff;text-decoration:none;font-size:16px;font-weight:700;border-radius:8px;text-align:center;">
        Pay Now &#8594; Secure Online Payment
      </a>
      <p style="margin:8px 0 0;color:#aaa;font-size:11px;">
        Clicking Pay Now opens your personal invoice in the secure client portal.
      </p>
    </td></tr>"""
        payment_info = """
    <!-- Payment info -->
    <tr><td style="padding:12px 32px 0;">
      <p style="margin:0;color:#666;font-size:13px;line-height:1.7;">
        <strong>Payment due upon survey completion.</strong>
        We accept: Credit / Debit Card, ACH / Bank Transfer, and Check.
      </p>
    </td></tr>"""
        # Action buttons — no "Accept & Pay" when real pay link exists
        question_href = f"mailto:{_CONTACT_EMAIL}?subject=Question%20about%20Order%20%23{order_id}&body=Hi%2C%20I%20have%20a%20question%20about%20my%20invoice%20for%20order%20%23{order_id}."
        decline_href  = f"mailto:{_CONTACT_EMAIL}?subject=DECLINE%20Order%20%23{order_id}&body=Hi%2C%20I%20would%20like%20to%20decline%20the%20estimate%20for%20order%20%23{order_id}.%20Reason%3A%20"
        action_buttons = f"""
    <!-- Secondary actions -->
    <tr><td style="padding:16px 32px 0;">
      <table cellpadding="0" cellspacing="0">
        <tr>
          <td style="border-radius:6px;background:#1a3a5c;">
            <a href="{question_href}" style="display:inline-block;padding:10px 20px;color:#ffffff;text-decoration:none;font-size:13px;font-weight:600;">? Ask a Question</a>
          </td>
          <td style="width:10px;"></td>
          <td style="border-radius:6px;border:1px solid #cccccc;">
            <a href="{decline_href}" style="display:inline-block;padding:10px 20px;color:#777777;text-decoration:none;font-size:13px;font-weight:600;">Decline</a>
          </td>
        </tr>
      </table>
      <p style="margin:10px 0 0;color:#aaa;font-size:12px;">
        You can also reply directly to this email — we usually respond within one business day.
      </p>
    </td></tr>"""
    else:
        pay_now_block = ""
        payment_info = """
    <!-- Payment info -->
    <tr><td style="padding:16px 32px 0;">
      <p style="margin:0;color:#666;font-size:13px;line-height:1.7;">
        <strong>Payment due upon survey completion.</strong><br>
        We accept: &nbsp; &#10003; Credit / Debit Card &nbsp; &#10003; ACH / Bank Transfer &nbsp; &#10003; Check
      </p>
    </td></tr>"""
        accept_href   = f"mailto:{_CONTACT_EMAIL}?subject=ACCEPT%20Order%20%23{order_id}&body=Hi%2C%20I%20accept%20the%20estimate%20for%20order%20%23{order_id}.%20Please%20proceed."
        question_href = f"mailto:{_CONTACT_EMAIL}?subject=Question%20about%20Order%20%23{order_id}&body=Hi%2C%20I%20have%20a%20question%20about%20my%20estimate%20for%20order%20%23{order_id}."
        decline_href  = f"mailto:{_CONTACT_EMAIL}?subject=DECLINE%20Order%20%23{order_id}&body=Hi%2C%20I%20would%20like%20to%20decline%20the%20estimate%20for%20order%20%23{order_id}.%20Reason%3A%20"
        action_buttons = f"""
    <!-- Action buttons -->
    <tr><td style="padding:24px 32px 0;">
      <p style="margin:0 0 14px;color:#333;font-size:14px;font-weight:600;">What would you like to do?</p>
      <table cellpadding="0" cellspacing="0">
        <tr>
          <td style="border-radius:6px;background:#1e7e34;">
            <a href="{accept_href}" style="display:inline-block;padding:12px 22px;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;">&#10003;&nbsp; Accept &amp; Pay</a>
          </td>
          <td style="width:10px;"></td>
          <td style="border-radius:6px;background:#1a3a5c;">
            <a href="{question_href}" style="display:inline-block;padding:12px 22px;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;">&#63;&nbsp; Ask a Question</a>
          </td>
          <td style="width:10px;"></td>
          <td style="border-radius:6px;border:1px solid #cccccc;">
            <a href="{decline_href}" style="display:inline-block;padding:12px 22px;color:#777777;text-decoration:none;font-size:14px;font-weight:600;">Decline</a>
          </td>
        </tr>
      </table>
      <p style="margin:12px 0 0;color:#aaa;font-size:12px;">
        You can also reply directly to this email — we usually respond within one business day.
      </p>
    </td></tr>"""

    review_block = (
        f'<p style="margin:12px 0 0;font-size:12px;color:#999;">'
        f'Loved our service? A quick {_review_link} means the world to our team. Thank you!'
        f'</p>'
    ) if _GOOGLE_REVIEW_URL else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Survey Invoice — Order #{order_id}</title></head>
<body style="margin:0;padding:0;background:#f2f4f7;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f2f4f7;">
<tr><td align="center" style="padding:32px 16px;">

  <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <!-- Header -->
    <tr><td style="background:#1a3a5c;padding:20px 32px;text-align:center;">
      <img src="cid:{_LOGO_CID}" alt="Nexgen Land Solutions" width="200" style="max-width:200px;height:auto;display:block;margin:0 auto;">
      <p style="margin:10px 0 0;color:#8eb8d8;font-size:13px;">Licensed Professional Surveyors &amp; Mappers — Florida</p>
    </td></tr>

    <!-- Greeting -->
    <tr><td style="padding:28px 32px 0;">
      <p style="margin:0 0 6px;color:#222;font-size:17px;font-weight:600;">Hi {first_name},</p>
      <p style="margin:0;color:#555;font-size:14px;line-height:1.7;">
        Thank you for choosing Nexgen Land Solutions.<br>
        Here is your survey invoice for order <strong>#{order_id}</strong>. Please review and proceed with payment at your convenience.
      </p>
    </td></tr>

    <!-- Services table -->
    <tr><td style="padding:20px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8e8e8;border-radius:6px;overflow:hidden;">
        <tr style="background:#f7f9fc;">
          <td style="padding:10px 12px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Service</td>
          <td style="padding:10px 12px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:0.5px;text-align:right;">Amount</td>
        </tr>
        {svc_rows}
      </table>
    </td></tr>

    <!-- Total -->
    <tr><td style="padding:16px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#eef4fb;border:1px solid #c5d9ef;border-radius:6px;">
        <tr>
          <td style="padding:16px 20px;color:#1a3a5c;font-size:14px;font-weight:600;">Total Amount Due</td>
          <td style="padding:16px 20px;text-align:right;color:#1a3a5c;font-size:28px;font-weight:700;">${total:,.2f}</td>
        </tr>
      </table>
    </td></tr>
    {pay_now_block}
    {payment_info}
    {action_buttons}

    <!-- Footer -->
    <tr><td style="padding:28px 32px;margin-top:20px;border-top:1px solid #eeeeee;">
      <p style="margin:0;color:#888;font-size:12px;line-height:1.8;">
        <strong style="color:#555;">Nexgen Land Solutions</strong><br>
        {_CONTACT_PHONE} &nbsp;|&nbsp; <a href="mailto:{_CONTACT_EMAIL}" style="color:#1a3a5c;text-decoration:none;">{_CONTACT_EMAIL}</a><br>
        <a href="https://{_CONTACT_WEB}" style="color:#1a3a5c;text-decoration:none;">{_CONTACT_WEB}</a>
      </p>
      {review_block}
    </td></tr>

  </table>
</td></tr>
</table>
</body></html>""".strip()


def _send_smtp(to_email: str, subject: str, html_body: str, logo_bytes: bytes | None = None) -> bool:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        raise AgentError("SMTP not configured — set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env")

    # Use multipart/related so the HTML and inline logo are bundled together
    msg = MIMEMultipart("related")
    msg["Subject"]  = subject
    msg["From"]     = _SMTP_FROM_DISPLAY
    msg["To"]       = to_email
    msg["Reply-To"] = _CONTACT_EMAIL

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    if logo_bytes:
        img = MIMEImage(logo_bytes, "png")
        img.add_header("Content-ID", f"<{_LOGO_CID}>")
        img.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(img)

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

    draft          = json.loads(raw_draft) if isinstance(raw_draft, str) else raw_draft
    override_email = draft.get("email_override_to") or ""
    client_name    = db_row.get("client_name", "")
    client_email   = db_row.get("customer_email", "")
    to_email       = EMAIL_OVERRIDE_ALL or override_email or client_email
    message_id     = db_row.get("approval_message_id")
    approved_by    = db_row.get("approved_by", "Unknown")
    test_mode      = bool(EMAIL_OVERRIDE_ALL)

    if not to_email:
        raise AgentError(f"send_for_order: no email for order {order_id}")

    # Must have a real FTF invoice_id before sending — never send without one
    invoice_id = db_row.get("invoice_id") or ""
    if not invoice_id or "TEST" in str(invoice_id).upper():
        raise AgentError(
            f"send_for_order: order {order_id} has no real invoice_id ({invoice_id!r}) — "
            "run A5 first to create the invoice in FTF"
        )

    if test_mode:
        log.warning("TEST MODE — email for order=%s redirected from %s to %s",
                    order_id, client_email, EMAIL_OVERRIDE_ALL)

    # Random delay (human-like) — skipped when invoked from the 2-min poller
    if not skip_delay and not _SKIP_DELAY:
        delay = random.randint(ESTIMATE_DELAY_MIN, ESTIMATE_DELAY_MAX)
        log.info("send delay=%ds order=%s", delay, order_id)
        time.sleep(delay)

    # Re-check status after delay — another process may have sent it already
    fresh = get_order_by_id(order_id)
    if fresh and fresh.get("status") != "invoice_finalized":
        log.warning("order %s already processed (status=%s) — skipping duplicate send",
                    order_id, fresh.get("status"))
        return {"sent": False, "skipped": True, "reason": "already_sent"}

    pay_link = db_row.get("pay_link") or ""
    logo     = _load_logo()
    html     = _build_email_html(client_name, order_id, draft, pay_link=pay_link)
    total    = draft.get("total_amount", 0)
    subject = f"Your Survey Invoice — Order #{order_id} — Nexgen Land Solutions"

    _send_smtp(to_email, subject, html, logo_bytes=logo)

    save_order_state(
        order_id,
        status="invoice_sent",
        sent_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        AGENT_NAME,
        decision="invoice_sent",
        order_id=order_id,
        reason=f"Invoice email sent to {to_email} total=${total:.2f}",
        input_summary=f"client={client_name}",
        output_summary=f"to={to_email} total={total}",
        model_used=None,
    )

    log.info("invoice sent order=%s to=%s override=%r total=%.2f", order_id, to_email, bool(override_email), total)
    return {"sent": True, "to": to_email, "total": total}


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
