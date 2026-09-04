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
from html import unescape as _unescape
from typing import Callable, Optional

import httpx

from config.settings import (
    EMAIL_OVERRIDE_ALL,
    FTF_PORTAL_BASE_URL,
    FTF_PORTAL_PASS,
    FTF_PORTAL_USER,
    FTF_SITE_BASE_URL,
)
from core.exceptions import AgentError, DeliveryAttemptedError, PreDeliveryError
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


# The Pay Now link is minted server-side by FTF (a Fernet token) and rendered into the order
# page as `paynow?token=<token>`. We scrape FTF's own token — we do NOT mint it — and build the
# same `/link/paynow?token=...` URL a human send uses. FTF appends the standard footer (PDF link,
# hint, review) to whatever `message` we pass, but it does NOT inject the Pay Now line unless it's
# in the message body — which is exactly why the AI's static message dropped it (see git history).
_PAYNOW_RE = re.compile(r"paynow\?token=([A-Za-z0-9_\-]+={0,2})")


def _scrape_delivery_extras(client: httpx.Client, order_id: str) -> dict:
    """Read the order page to recover FTF's Pay Now link + purchaser name for the email body.

    Read-only. Returns {"pay_link": str, "purchaser": str}; pay_link is "" if the token can't be
    found (caller then falls back to the plain message rather than failing the send)."""
    try:
        r = client.get(f"{FTF_PORTAL_BASE_URL}/order/?order={order_id}", timeout=20.0)
        r.raise_for_status()
        html = r.text
    except Exception as exc:
        log.warning("pay-link scrape: could not load order page order=%s: %s", order_id, exc)
        return {"pay_link": "", "purchaser": ""}

    m = _PAYNOW_RE.search(html)
    pay_link = f"{FTF_SITE_BASE_URL}/link/paynow?token={m.group(1)}" if m else ""
    if not pay_link:
        log.warning("pay-link scrape: no paynow token on order page order=%s — email will omit Pay Now",
                    order_id)

    pm = re.search(r'id=["\']{0,1}invoice_purchaser["\']{0,1}\s[^>]*value=["\'](.*?)["\']', html)
    if not pm:
        pm = re.search(r'value=["\'](.*?)["\']\s*[^>]*id=["\']{0,1}invoice_purchaser["\']{0,1}', html)
    purchaser = pm.group(1) if pm else ""

    # ── FTF's OWN pre-filled subject + message body ───────────────────────────────
    # This is the single source of truth for what a delivery email looks like: the order page
    # renders the exact subject and body a human sees in the Deliver modal and sends verbatim.
    # Rebuilding it by hand is how the AI email silently lost content twice — first the Pay Now
    # link, then (2026-08-27) the "Invoice Amount: $X" line and the "View Invoice" link, so the
    # client received a delivery email that never stated a price or linked the invoice. Taking
    # FTF's text verbatim also means a future FTF template change follows automatically.
    sm = re.search(r'id=["\']mail_subject["\'][^>]*\svalue=["\'](.*?)["\']', html)
    prefill_subject = _unescape(sm.group(1)).strip() if sm else ""
    tm = re.search(r'<textarea[^>]+id=["\']deliver-message["\'][^>]*>(.*?)</textarea>', html, re.S)
    prefill_message = _unescape(tm.group(1)).strip() if tm else ""
    # FTF appends " ({address})" to the subject using the address it holds, in its own casing.
    am = re.search(r'<input type=["\']hidden["\'] name=["\']address["\'] value=["\'](.*?)["\']', html)
    prefill_address = _unescape(am.group(1)).strip() if am else ""
    if not prefill_message:
        log.warning("delivery prefill: no deliver-message textarea on order page order=%s — "
                    "falling back to the locally built message", order_id)

    return {"pay_link": pay_link, "purchaser": purchaser,
            "subject": prefill_subject, "message": prefill_message, "address": prefill_address}


# A pre-filled body is only usable if it still carries the parts that make the email worth
# sending. If FTF ever changes the template beyond recognition we fall back rather than mail a
# client something we cannot vouch for.
_PREFILL_REQUIRED = ("Pay Now", "View Invoice")


def _prefill_usable(message: str) -> bool:
    return bool(message) and all(tok in message for tok in _PREFILL_REQUIRED)


def _build_invoice_message(pay_link: str, property_address: str, purchaser: str) -> str:
    """Reproduce FTF's pre-filled delivery message body (greeting + delivery-for + Pay Now block).

    FTF converts newlines to <br> and appends its own footer, so we only supply the top block.
    The Pay Now anchor must be explicit HTML so MailerSend click-wraps it exactly like a human send."""
    first = (purchaser or "").strip().split(" ")[0] if (purchaser or "").strip() else ""
    greeting = f"Hello {first}," if first else "Hello,"
    addr = (property_address or "").strip()
    delivery = f" This delivery is for {addr}" if addr else ""
    return (
        f"{greeting}\n\n"
        f"Thank you for your order from Nexgen! We are delighted to have the privilege of serving you."
        f"{delivery}\n\n"
        f"If the invoice has not yet been paid, please click below to make payment: "
        f"<a href=\"{pay_link}\">Pay Now</a>\n\n"
        f"If you have any questions regarding your order, please contact us by either replying to this "
        f"email or by sending us a message through our website. We look forward to meeting all of your "
        f"surveying needs with speed, accuracy, and excellence!"
    )


def deliver_invoice_as_nesa(
    order_id: str,
    client_email: str,
    property_address: str = "",
    subject: str = "",
    message: str = "",
    on_before_deliver: Optional[Callable[[], None]] = None,
) -> dict:
    """Generate invoice PDF and deliver it via the FTF portal authenticated as nesa.

    nesa's session is used for both steps so the FTF audit trail records nesa as
    the actor (ng_log_trackflow.ng_user = 'nesa').

    EMAIL_OVERRIDE_ALL: when set, overrides recipient (staging safety).

    Subject: FTF's sendgridsend.py appends f" ({address})" to mail_subject.
    We pass mail_subject="Your Invoice is ready to review" + address=property_address
    so the final subject is "Your Invoice is ready to review ({property_address})".

    Exactly-once send contract (FTF has NO "already sent" flag, so the caller relies
    on WHERE we failed):
      * login / PDF generation failure  → raise PreDeliveryError      (nothing sent; safe to retry)
      * deliver POST attempted + failed → raise DeliveryAttemptedError (outcome unknown; do NOT retry)
    `on_before_deliver`, if given, is invoked AFTER PDF generation and IMMEDIATELY
    BEFORE the irreversible deliver POST — the caller uses it to persist a durable
    "sending" marker so a crash anywhere at/after the POST can never resend.

    Returns: {"sent": True, "to": <recipient>, "pdf": <path>}
    """
    recipient = EMAIL_OVERRIDE_ALL or client_email
    if EMAIL_OVERRIDE_ALL:
        log.warning("TEST MODE — invoice for order=%s redirected from %s to %s",
                    order_id, client_email, EMAIL_OVERRIDE_ALL)

    if not recipient:
        # No recipient = nothing was sent; safe to retry once the email is known.
        raise PreDeliveryError(f"deliver_invoice_as_nesa: no recipient for order {order_id}")

    # ── Pre-delivery: login + PDF. Any failure here means NOTHING was sent. ──────
    try:
        client = _login()
    except Exception as exc:
        raise PreDeliveryError(f"portal login failed for order {order_id}: {exc}") from exc

    try:
        try:
            pdf_path = _generate_pdf(client, order_id)
        except Exception as exc:
            raise PreDeliveryError(f"PDF generation failed for order {order_id}: {exc}") from exc

        # mail_subject must NOT include address — FTF appends f" ({address})" automatically
        mail_subject = subject or "Your Invoice is ready to review"

        # Build the body BEFORE the tombstone/POST. When no explicit message was passed, take
        # FTF's OWN pre-filled subject + body from the order page and send them verbatim, which
        # is precisely what a human send does. Preference order:
        #   1. FTF's pre-filled body  — identical to a human send; carries the amount, the
        #      View Invoice link, the address block and the Pay Now link
        #   2. locally built block    — Pay Now only (used if the template moved)
        #   3. _DEFAULT_MSG           — no link at all (used if the page can't be read)
        # A scrape miss must never fail or delay a send, so every step degrades quietly.
        pay_link  = ""
        addr_used = property_address
        if not message:
            extras   = _scrape_delivery_extras(client, order_id)
            pay_link = extras["pay_link"]
            if _prefill_usable(extras["message"]):
                message = extras["message"]
                # Use FTF's own subject/address too, so the delivered subject line matches a
                # human send exactly ("Your NexGen Quote is Ready" on a Quote-stage order,
                # "Your Invoice is ready to review" on an order-stage one).
                if not subject and extras["subject"]:
                    mail_subject = extras["subject"]
                if extras["address"]:
                    addr_used = extras["address"]
                log.info("delivery body: using FTF's pre-filled message order=%s subject=%r "
                         "(%d chars)", order_id, mail_subject, len(message))
            else:
                message = (
                    _build_invoice_message(pay_link, property_address, extras["purchaser"])
                    if pay_link else _DEFAULT_MSG
                )
                log.warning("delivery body: FTF pre-fill unusable for order=%s — sending the "
                            "locally built message (pay_link=%s)", order_id, "yes" if pay_link else "no")

        # Durable "about to send" marker — set right before the irreversible POST so
        # that a crash/timeout at or after the POST can never trigger a second send.
        if on_before_deliver is not None:
            try:
                on_before_deliver()
            except Exception as exc:
                # Could not persist the marker → do NOT send (an unguarded send could
                # be resent on the next run). Nothing has gone out yet → safe to retry.
                raise PreDeliveryError(
                    f"on_before_deliver hook failed for order {order_id} — not sending: {exc}"
                ) from exc

        # ── The irreversible send. Any failure from here on is AMBIGUOUS. ────────
        try:
            r = client.post(
                f"{FTF_PORTAL_BASE_URL}/order/deliver_invoice",
                data={
                    "order":        str(order_id),
                    "invoice":      pdf_path,
                    "address":      addr_used,          # FTF appends this to subject
                    "email":        recipient,
                    "mail_subject": mail_subject,
                    "message":      message,
                },
            )
            r.raise_for_status()
        except Exception as exc:
            raise DeliveryAttemptedError(
                f"deliver POST failed for order {order_id} — email may or may not have been sent; "
                f"NOT retrying automatically: {exc}"
            ) from exc

        log.info("invoice delivered via portal as %s order=%s to=%s pdf=%s pay_link=%s",
                 FTF_PORTAL_USER, order_id, recipient, pdf_path, "yes" if pay_link else "no")
        return {"sent": True, "to": recipient, "pdf": pdf_path, "pay_link": pay_link}

    finally:
        client.close()
