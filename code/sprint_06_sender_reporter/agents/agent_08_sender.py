import os
import sys
import random
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone

from config.models import SENDER_MODEL
from config.settings import ESTIMATE_DELAY_MAX, ESTIMATE_DELAY_MIN
from core.db import get_order_by_id, get_reviewed_order, log_decision, save_order_state
from core.exceptions import AgentError
from core.ftf_client import create_invoice, mark_estimate_sent, send_invoice
from core.logger import get_logger

AGENT_NAME = "agent_08_sender"
log = get_logger(AGENT_NAME)


def send_estimate(order_id: str) -> dict:
    """Send a reviewed estimate through FTF Books.

    Flow: create invoice → random delay → send invoice → mark estimate sent → update DB.

    Returns {"order_id": ..., "status": "sent", "invoice_id": ...}.
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

    service_type = db_row.get("service_type") or "Survey"

    # Apply random human-like delay before sending
    delay_secs = random.randint(ESTIMATE_DELAY_MIN, ESTIMATE_DELAY_MAX)
    log.info("send_estimate queued order=%s delay=%ss", order_id, delay_secs)
    time.sleep(delay_secs)

    # Create invoice in FTF Books, then send it
    services = [{"name": service_type, "amount": amount}]
    invoice = create_invoice(order_id, amount, services)
    invoice_id = str(invoice.get("invoice_id") or invoice.get("id", ""))

    send_invoice(invoice_id)
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
    """Send the next reviewed order. Returns result dict or None if nothing queued."""
    order_rec = get_reviewed_order()
    if not order_rec:
        log.info("no reviewed orders awaiting send")
        return None
    return send_estimate(order_rec["order_id"])


if __name__ == "__main__":
    run()
