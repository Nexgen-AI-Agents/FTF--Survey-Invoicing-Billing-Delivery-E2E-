"""Agent A6 — Sender v2 (Invoice Pipeline)

Delivers the FTF invoice to the client using FTF's native send endpoint.
POST /ftf-ai-api/v1/invoices/{invoice_id}/send — FTF handles email composition and delivery.

EMAIL_OVERRIDE_ALL: when set, redirects delivery to the override address instead of the
client email on file (staging safety — set this secret to test without hitting real clients).

Status flow: invoice_finalized → invoice_sent
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import EMAIL_OVERRIDE_ALL
from core.excel_db import get_orders_by_status, get_order_by_id, save_order_state, log_decision
from core.exceptions import AgentError
from core.ftf_client import send_invoice as ftf_send_invoice
from core.logger import get_logger

AGENT_NAME = "agent_a6_sender_v2"
log = get_logger(AGENT_NAME)


def send_for_order(order_id: str) -> dict:
    """Deliver FTF invoice for one finalized order."""
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"send_for_order: order {order_id} not in DB")

    invoice_id = db_row.get("invoice_id") or ""
    if not invoice_id or "TEST" in str(invoice_id).upper():
        raise AgentError(
            f"send_for_order: order {order_id} has no real invoice_id ({invoice_id!r}) — "
            "run A5 first to create the invoice in FTF"
        )

    client_email = db_row.get("customer_email", "")
    recipient = EMAIL_OVERRIDE_ALL or None  # None = FTF resolves from client record

    if recipient:
        log.warning("TEST MODE — invoice for order=%s redirected from %s to %s",
                    order_id, client_email, recipient)

    ftf_send_invoice(invoice_id, recipient_email=recipient)

    save_order_state(
        order_id,
        status="invoice_sent",
        sent_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        AGENT_NAME,
        decision="invoice_sent",
        order_id=order_id,
        reason=f"Invoice {invoice_id} delivered via FTF to {recipient or client_email}",
        input_summary=f"invoice_id={invoice_id}",
        output_summary=f"sent_to={recipient or client_email}",
        model_used=None,
    )

    log.info("invoice delivered order=%s invoice_id=%s to=%s",
             order_id, invoice_id, recipient or client_email)
    return {"sent": True, "to": recipient or client_email, "invoice_id": invoice_id}


def run() -> dict:
    """Deliver invoices for all invoice_finalized orders."""
    orders  = get_orders_by_status("invoice_finalized")
    summary = {"processed": 0, "sent": 0, "skipped": 0, "errors": 0}

    for db_row in orders:
        order_id = db_row["order_id"]
        try:
            fresh = get_order_by_id(order_id)
            if fresh and fresh.get("status") != "invoice_finalized":
                log.warning("order %s already processed (status=%s) — skipping",
                            order_id, fresh.get("status"))
                summary["skipped"] += 1
                continue

            send_for_order(order_id)
            summary["sent"] += 1
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
    args = parser.parse_args(argv)

    if args.order_id:
        result = send_for_order(args.order_id)
        print(result)
    elif args.run_now:
        print(run())


if __name__ == "__main__":
    main()
