"""ftf_portal_client.py — Session-authenticated FTF portal client.

Logs in as the nesa HR user and calls portal endpoints to generate the invoice
PDF and deliver it to the client. This attributes the action to nesa in the FTF
audit trail (ng_log_trackflow.ng_user = 'nesa').

Flow:
  1. POST /admin/login           → Flask session cookie
  2. GET  /order/?order={id}     → scrape invoice form fields (city, state, zip, date)
  3. POST /order/invoice         → generates repos/{order}/invoice/invoice-{order}-order.pdf
  4. POST /order/deliver_invoice → sends email via SendGrid, records nesa as sender

FTF /order/invoice required fields (from order/static/js/update.js generate_invoice_paid()):
  order_id, invoice_order_id, invoice_address, invoice_city, invoice_state,
  invoice_zip, invoice_order_date, invoice_purchaser, invoice_note, b_paid

FTF filename convention (order/invoice.py line 163):
  status = '-quote' if orderStatus == 'Quote' else '-order'
  path = f"repos/{order}/invoice/invoice-{order}{status}.pdf"

deliver_invoice subject convention (order/sendgridsend.py line 195):
  subject = mail_subject + f" ({address})"
  So mail_subject must NOT include the address — pass address separately.
"""

import re

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


def _scrape_invoice_fields(client: httpx.Client, order_id: str) -> dict:
    """GET /order/?order={id} and extract the hidden invoice form field values."""
    r = client.get(f"{FTF_PORTAL_BASE_URL}/order/?order={order_id}", timeout=20.0)
    r.raise_for_status()
    html = r.text

    def _val(field_id: str) -> str:
        m = re.search(rf'id=["\']{{0,1}}{field_id}["\']{{0,1}}\s[^>]*value=["\'](.*?)["\']', html)
        if not m:
            m = re.search(rf'value=["\'](.*?)["\']\s*[^>]*id=["\']{{0,1}}{field_id}["\']{{0,1}}', html)
        return m.group(1) if m else ""

    fields = {
        "order_id":           _val("order_id") or order_id,
        "invoice_order_id":   _val("invoice_order_id") or order_id,
        "invoice_purchaser":  _val("invoice_purchaser"),
        "invoice_address":    _val("invoice_address"),
        "invoice_city":       _val("invoice_city"),
        "invoice_state":      _val("invoice_state"),
        "invoice_zip":        _val("invoice_zip"),
        "invoice_order_date": _val("invoice_order_date"),
        "invoice_note":       _val("invoice_note"),
    }
    log.debug("scraped invoice fields for order=%s: %s", order_id, fields)
    return fields


def _generate_pdf(client: httpx.Client, order_id: str) -> str:
    """POST /order/invoice to generate the invoice PDF.

    Scrapes required address fields from the order page first, then submits the
    full form. Returns the PDF path relative to the order repo directory:
      invoice/invoice-{order_id}-order.pdf

    Raises AgentError if FTF reports success:false.
    """
    fields = _scrape_invoice_fields(client, order_id)

    r = client.post(
        f"{FTF_PORTAL_BASE_URL}/order/invoice",
        data={
            **fields,
            "b_paid": "1",
            "check_number": "",
            "check_amount": "",
            "customizer_item": [],
            "customizer_amount": [],
            "customizer_id": [],
        },
    )
    r.raise_for_status()

    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not body.get("success", True):
        raise AgentError(
            f"FTF /order/invoice failed for order={order_id}: {body.get('message', 'unknown error')}"
        )

    pdf_path = f"invoice/invoice-{order_id}-order.pdf"
    log.info("invoice PDF generated order=%s path=%s", order_id, pdf_path)
    return pdf_path


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

    Subject: FTF's sendgridsend.py appends f" ({address})" to mail_subject.
    We pass mail_subject="Your Invoice is ready to review" + address=property_address
    so the final subject is "Your Invoice is ready to review ({property_address})".

    Returns: {"sent": True, "to": <recipient>, "pdf": <path>}
    """
    recipient = EMAIL_OVERRIDE_ALL or client_email
    if EMAIL_OVERRIDE_ALL:
        log.warning("TEST MODE — invoice for order=%s redirected from %s to %s",
                    order_id, client_email, EMAIL_OVERRIDE_ALL)

    if not recipient:
        raise AgentError(f"deliver_invoice_as_nesa: no recipient for order {order_id}")

    client = _login()
    try:
        pdf_path = _generate_pdf(client, order_id)

        # mail_subject must NOT include address — FTF appends f" ({address})" automatically
        mail_subject = subject or "Your Invoice is ready to review"
        message = message or _DEFAULT_MSG

        r = client.post(
            f"{FTF_PORTAL_BASE_URL}/order/deliver_invoice",
            data={
                "order":        str(order_id),
                "invoice":      pdf_path,
                "address":      property_address,   # FTF appends this to subject
                "email":        recipient,
                "mail_subject": mail_subject,
                "message":      message,
            },
        )
        r.raise_for_status()

        log.info("invoice delivered via portal as %s order=%s to=%s pdf=%s",
                 FTF_PORTAL_USER, order_id, recipient, pdf_path)
        return {"sent": True, "to": recipient, "pdf": pdf_path}

    finally:
        client.close()
