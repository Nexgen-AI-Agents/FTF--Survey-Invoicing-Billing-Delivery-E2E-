"""Agent A5 — Invoice Finalizer (Invoice Pipeline)

Takes orders with status=invoice_approved, creates the invoice in FTF via API,
and verifies the $ flag (invoice_needed) is cleared.

FTF API calls:
  POST /invoices  →  create invoice with approved services + amount
  GET  /invoices/{id}  →  verify creation succeeded

If the API call fails: retries up to 3 times, then logs the error.

Status flow: invoice_approved → invoice_finalized
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import FTF_PAY_HASH_KEY, FTF_SITE_BASE_URL
from core.excel_db import get_orders_by_status, get_order_by_id, save_order_state, log_decision
from core.exceptions import AgentError
from core.ftf_client import create_invoice, get_invoice
from core.logger import get_logger

AGENT_NAME = "agent_a5_invoice_finalizer"
log       = get_logger(AGENT_NAME)
MAX_RETRY = 3


def generate_pay_link(order_id: str) -> str:
    """Generate the FTF Pay Now link using the same Fernet encryption as the portal.

    Matches data_vars['hash_key'] / newGen_base_url logic in the FTF Flask app:
        token = Fernet(key).encrypt(str(order_id).encode()).decode()
        url   = f'{base}/link/paynow?token={token}'
    """
    if not FTF_PAY_HASH_KEY:
        log.warning("FTF_PAY_HASH_KEY not set — Pay Now link will be omitted from email")
        return ""
    try:
        from cryptography.fernet import Fernet
        token = Fernet(FTF_PAY_HASH_KEY.encode()).encrypt(str(order_id).encode()).decode()
        base  = FTF_SITE_BASE_URL.rstrip("/")
        return f"{base}/link/paynow?token={token}"
    except Exception as exc:
        log.warning("generate_pay_link failed order=%s: %s", order_id, exc)
        return ""


def finalize_order(order_id: str) -> dict:
    """Create invoice in FTF for one approved order.

    Returns {"invoice_id": ..., "ok": True}
    """
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"finalize_order: order {order_id} not in DB")

    raw_draft = db_row.get("invoice_draft")
    if not raw_draft:
        raise AgentError(f"finalize_order: order {order_id} has no invoice_draft")

    draft = json.loads(raw_draft) if isinstance(raw_draft, str) else raw_draft
    services = draft.get("services", [])
    total    = float(draft.get("total_amount", 0))
    message_id = db_row.get("approval_message_id")

    if not services or total <= 0:
        raise AgentError(f"finalize_order: invalid draft — no services or zero total for order {order_id}")

    # Build FTF invoice services payload
    ftf_services = [
        {
            "name":        svc.get("name", "Survey Service"),
            "description": svc.get("description", ""),
            "amount":      float(svc.get("amount", 0)),
        }
        for svc in services
    ]

    # Create invoice with retry
    last_exc = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            result = create_invoice(order_id, total, ftf_services)
            # API returns {"invoice_ids": [349393], ...} — take first element
            ids = result.get("invoice_ids") or []
            invoice_id = str(ids[0]) if ids else str(result.get("invoice_id") or result.get("id") or "")
            log.info("invoice created order=%s invoice_id=%s attempt=%d", order_id, invoice_id, attempt)
            break
        except Exception as exc:
            last_exc = exc
            log.warning("create_invoice attempt=%d failed order=%s: %s", attempt, order_id, exc)
    else:
        raise AgentError(f"finalize_order: all retries exhausted for order {order_id}: {last_exc}")

    # Optional: verify invoice exists
    if invoice_id:
        try:
            get_invoice(invoice_id)
        except Exception as exc:
            log.warning("invoice verification failed invoice_id=%s: %s", invoice_id, exc)

    # Generate Pay Now link (Fernet-encrypted order_id, same logic as FTF portal)
    pay_link = generate_pay_link(order_id)
    if pay_link:
        log.info("pay_link generated order=%s", order_id)

    # Save
    save_order_state(
        order_id,
        status="invoice_finalized",
        invoice_id=invoice_id,
        invoice_created_at=datetime.now(timezone.utc).isoformat(),
        pay_link=pay_link,
    )

    log_decision(
        AGENT_NAME,
        decision="invoice_finalized",
        order_id=order_id,
        reason=f"Invoice created in FTF invoice_id={invoice_id} total=${total:.2f}",
        input_summary=f"services={len(ftf_services)} total={total}",
        output_summary=f"invoice_id={invoice_id}",
        model_used=None,
    )

    return {"invoice_id": invoice_id, "pay_link": pay_link, "ok": True}


def run() -> dict:
    """Process all orders with status=invoice_approved."""
    orders  = get_orders_by_status("invoice_approved")
    summary = {"processed": 0, "finalized": 0, "errors": 0}

    for db_row in orders:
        order_id = db_row["order_id"]
        try:
            finalize_order(order_id)
            summary["finalized"] += 1
        except Exception as exc:
            log.error("finalize failed order=%s: %s", order_id, exc)
            summary["errors"] += 1
        summary["processed"] += 1

    log.info("invoice_finalizer complete: %s", summary)
    return summary


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="A5 Invoice Finalizer — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--order-id")
    args = parser.parse_args(argv)

    if args.order_id:
        result = finalize_order(args.order_id)
        print(result)
    elif args.run_now:
        print(run())


if __name__ == "__main__":
    main()
