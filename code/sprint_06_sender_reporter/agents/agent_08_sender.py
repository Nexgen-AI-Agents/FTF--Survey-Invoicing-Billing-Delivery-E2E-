import os
import sys
import random
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from config.models import SENDER_MODEL
from config.settings import (
    ESTIMATE_DELAY_MAX,
    ESTIMATE_DELAY_MIN,
    MAX_SENDER_RETRIES,
    SEND_HOUR_END,
    SEND_HOUR_START,
)
from core.db import get_order_by_id, get_reviewed_order, log_decision, save_order_state
from core.exceptions import AgentError
from core.ftf_client import create_invoice, mark_estimate_sent, send_invoice
from core.logger import get_logger

AGENT_NAME = "agent_08_sender"
log = get_logger(AGENT_NAME)

_EASTERN = ZoneInfo("America/New_York")


def _in_send_window() -> bool:
    """Return True if current Eastern time is within the allowed send window (8 AM–6 PM ET)."""
    now_et = datetime.now(_EASTERN)
    return SEND_HOUR_START <= now_et.hour < SEND_HOUR_END


def _create_and_send_invoice(order_id: str, amount: float, service_type: str) -> str:
    """Create and send FTF invoice with up to MAX_SENDER_RETRIES attempts.

    Returns the invoice_id on success.
    Raises AgentError after exhausting all retries.
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_SENDER_RETRIES + 1):
        try:
            services = [{"name": service_type, "amount": amount}]
            invoice = create_invoice(order_id, amount, services)
            invoice_id = str(invoice.get("invoice_id") or invoice.get("id", ""))
            send_invoice(invoice_id)
            return invoice_id
        except Exception as exc:
            last_exc = exc
            log.warning(
                "send attempt=%s/%s failed order=%s error=%s",
                attempt, MAX_SENDER_RETRIES, order_id, exc,
            )

    raise AgentError(
        f"send_estimate: order {order_id} failed after {MAX_SENDER_RETRIES} attempts"
    ) from last_exc


def send_estimate(order_id: str) -> dict | None:
    """Send a reviewed estimate through FTF Books.

    Returns None if called outside the 8 AM–6 PM ET send window (caller reschedules).
    Returns {"order_id": ..., "status": "sent", "invoice_id": ...} on success.
    Saves status="error" and raises AgentError after MAX_SENDER_RETRIES send failures.
    Raises AgentError if order not found, wrong status, or zero amount.
    """
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"send_estimate: order {order_id} not found in processed_orders")

    current_status = db_row.get("status")
    if current_status != "reviewed":
        raise AgentError(
            f"send_estimate: order {order_id} status={current_status!r}, expected 'reviewed'"
        )

    amount = float(db_row.get("estimate_amount") or 0.0)
    if amount <= 0:
        raise AgentError(
            f"send_estimate: order {order_id} has no estimate amount — cannot create invoice"
        )

    # Guard: never send outside business hours (I-024)
    if not _in_send_window():
        log.warning(
            "send_estimate outside send window (%s–%s ET) order=%s — will retry next cycle",
            SEND_HOUR_START, SEND_HOUR_END, order_id,
        )
        return None

    service_type = db_row.get("service_type") or "Survey"

    # Apply random human-like delay before sending
    delay_secs = random.randint(ESTIMATE_DELAY_MIN, ESTIMATE_DELAY_MAX)
    log.info("send_estimate queued order=%s delay=%ss", order_id, delay_secs)
    time.sleep(delay_secs)

    # Attempt to create + send invoice with retry (I-024)
    try:
        invoice_id = _create_and_send_invoice(order_id, amount, service_type)
    except AgentError as exc:
        save_order_state(order_id, status="error", flag_reason=str(exc))
        log_decision(
            agent_name=AGENT_NAME,
            decision="error",
            order_id=order_id,
            reason=str(exc),
            input_summary=f"amount={amount:.2f} service={service_type}",
            output_summary=f"failed after {MAX_SENDER_RETRIES} attempts",
            model_used=SENDER_MODEL,
        )
        raise

    mark_estimate_sent(order_id)

    save_order_state(
        order_id,
        status="sent",
        sent_at=datetime.now(timezone.utc).isoformat(),
    )
    log_decision(
        agent_name=AGENT_NAME,
        decision="sent",
        order_id=order_id,
        reason=f"invoice {invoice_id} created and sent after {delay_secs}s delay",
        input_summary=f"amount={amount:.2f} service={service_type}",
        output_summary=f"status=sent invoice_id={invoice_id}",
        model_used=SENDER_MODEL,
    )
    log.info("estimate sent order=%s invoice_id=%s", order_id, invoice_id)
    return {"order_id": order_id, "status": "sent", "invoice_id": invoice_id}


def run() -> dict | None:
    """Send the next reviewed order. Returns result dict, None if nothing queued or outside window."""
    order_rec = get_reviewed_order()
    if not order_rec:
        log.info("no reviewed orders awaiting send")
        return None
    return send_estimate(order_rec["order_id"])


if __name__ == "__main__":
    run()
