"""ftf_portal_client.py — Session-authenticated FTF portal client.

Logs in as the nesa HR user and calls portal endpoints to generate the invoice
PDF and deliver it to the client. This attributes the action to nesa in the FTF
audit trail (ng_log_trackflow.ng_user = 'nesa').

Flow:
  1. POST /admin/login         → Flask session cookie
  2. POST /order/invoice       → generates invoice-{order_id}.pdf in the order repo
  3. POST /order/deliver_invoice → sends email via SendGrid, records nesa as sender
"""

import httpx

from config.settings import (
    EMAIL_OVERRIDE_ALL,
    FTF_PORTAL_BASE_URL,
    FTF_PORTAL_PASS,
    FTF_PORTAL_USER,
)
from core.exceptions import AgentError
from core.logger import get_logger

log = get_logger("ftf_portal_client")

_DEFAULT_MSG = (
    "Please find your invoice attached. "
    "If you have any questions, please contact us at "
    "info@nexgensurveying.com or (561) 508-6272.\n\n"
    "www.NexGenSurveying.com\n"
    "1547 Prosperity Farms, Lake Park FL, 33403\n"
    "(561) 508-6272"
)


def _login() -> httpx.Client:
    """POST /admin/login as nesa. Returns authenticated httpx.Client with session cookie."""
    if not FTF_PORTAL_USER or not FTF_PORTAL_PASS:
        raise AgentError("FTF_PORTAL_USER / FTF_PORTAL_PASS not set — cannot authenticate as nesa")

    client = httpx.Client(follow_redirects=True, timeout=30.0)
    r = client.post(
        f"{FTF_PORTAL_BASE_URL}/admin/login",
        data={"user": FTF_PORTAL_USER, "password": FTF_PORTAL_PASS},
    )
    r.raise_for_status()

    body = r.json()
    if not body.get("success"):
        client.close()
        raise AgentError(f"FTF portal login failed for user={FTF_PORTAL_USER!r}: {body.get('message')}")

    log.info("portal login ok user=%s user_id=%s", FTF_PORTAL_USER, body.get("log_user_id"))
    return client


def _generate_pdf(client: httpx.Client, order_id: str) -> str:
    """POST /order/invoice to generate the invoice PDF. Returns the PDF filename."""
    r = client.post(
        f"{FTF_PORTAL_BASE_URL}/order/invoice",
        data={"invoice_order_id": str(order_id)},
    )
    r.raise_for_status()
    # Portal saves the file as invoice-{order_id}.pdf in the order's repo directory
    pdf_filename = f"invoice-{order_id}.pdf"
    log.info("invoice PDF generated order=%s filename=%s", order_id, pdf_filename)
    return pdf_filename


def deliver_invoice_as_nesa(
    order_id: str,
    client_email: str,
    property_address: str = "",
    subject: str = "",
    message: str = "",
) -> dict:
    """Generate invoice PDF and deliver it via the FTF portal authenticated as nesa.

    nesa's session is used for both steps so the FTF audit trail records nesa as
    the actor (ng_log_trackflow.ng_user = 'nesa').

    EMAIL_OVERRIDE_ALL: when set, overrides recipient (staging safety).

    Returns: {"sent": True, "to": <recipient>, "pdf": <filename>}
    """
    recipient = EMAIL_OVERRIDE_ALL or client_email
    if EMAIL_OVERRIDE_ALL:
        log.warning("TEST MODE — invoice for order=%s redirected from %s to %s",
                    order_id, client_email, EMAIL_OVERRIDE_ALL)

    if not recipient:
        raise AgentError(f"deliver_invoice_as_nesa: no recipient for order {order_id}")

    client = _login()
    try:
        pdf_filename = _generate_pdf(client, order_id)

        subject = subject or f"Your Invoice is ready to review ({property_address or order_id})"
        message = message or _DEFAULT_MSG

        r = client.post(
            f"{FTF_PORTAL_BASE_URL}/order/deliver_invoice",
            data={
                "order":        str(order_id),
                "invoice":      pdf_filename,
                "email":        recipient,
                "mail_subject": subject,
                "message":      message,
            },
        )
        r.raise_for_status()

        log.info("invoice delivered via portal as %s order=%s to=%s pdf=%s",
                 FTF_PORTAL_USER, order_id, recipient, pdf_filename)
        return {"sent": True, "to": recipient, "pdf": pdf_filename}

    finally:
        client.close()
