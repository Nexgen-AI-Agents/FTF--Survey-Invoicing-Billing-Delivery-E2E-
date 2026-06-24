"""Agent A1 — Flag Hunter (Invoice Pipeline)

Replaces agent_02_monitor. Scans ALL orders (any status) for the
'order needs an invoice' flag (filter_by_flag=invoice_needed).
Every order with this flag = $ symbol visible in Track Flow UI.

Changes vs old monitor:
- Uses filter_by_flag=invoice_needed instead of status=Quote
- No status filter — catches orders in any FTF status
- Queues with status='invoice_needed' (new pipeline status)

Run: every 5 minutes via GitHub Actions.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import INTERNAL_SKIP_EMAILS
from core.ftf_mysql import get_invoice_needed_orders, get_max_ng_id
from core.excel_db import order_exists, save_order_state, log_decision
from core.intake_watermark import load_watermark, save_watermark
from core.logger import get_logger

AGENT_NAME = "agent_a1_flag_hunter"
log = get_logger(AGENT_NAME)

STATUS_INVOICE_NEEDED = "invoice_needed"

# Max new orders queued per run. Caps how many fresh orders enter the pipeline
# (and therefore how many fill the Excel sheet) each 30-min cycle. Env-overridable
# so it stays in lockstep with A2_MAX_PER_RUN / INVOICE_BATCH_SIZE.
MAX_NEW_PER_RUN = int(os.getenv("A1_MAX_NEW_PER_RUN", "10"))


def run() -> list[str]:
    """Scan for orders with invoice_needed flag; queue new ones (from today onward).

    Returns list of newly queued order IDs.

    Intake watermark: on the very first run (no watermark file yet) A1 records the
    current MAX(ng_id) and queues NOTHING — everything that already exists is treated
    as historical backlog and skipped. Every later run only queues orders with
    ng_id > watermark, so the pipeline processes orders created from the reset point
    forward. MySQL returns matching flagged orders newest-first; dedup via
    order_exists(); at most MAX_NEW_PER_RUN are queued per cycle.
    """
    watermark = load_watermark()
    if watermark is None:
        mx = get_max_ng_id()
        if mx <= 0:
            log.warning("flag_hunter: could not read MAX(ng_id) to init watermark — skipping this run")
            return []
        save_watermark(mx)
        log.info(
            "flag_hunter: intake watermark INITIALIZED at ng_id=%d. Historical backlog "
            "ignored; only orders newer than this will be queued from now on.", mx,
        )
        return []

    orders = get_invoice_needed_orders(min_ng_id=watermark)
    new_ids: list[str] = []

    for order in orders:
        if len(new_ids) >= MAX_NEW_PER_RUN:
            log.info(
                "flag_hunter: MAX_NEW_PER_RUN=%d reached — %d orders remain for next cycle",
                MAX_NEW_PER_RUN, len(orders) - MAX_NEW_PER_RUN,
            )
            break
        order_id = str(order.get("order_id", ""))
        if not order_id:
            continue

        if order_exists(order_id):
            log.debug("skip already-tracked order=%s", order_id)
            continue

        # Skip internal NexGen routing emails — no real client invoice target
        email = str(order.get("customer_email") or order.get("email") or "").strip().lower()
        if email in INTERNAL_SKIP_EMAILS:
            log.info("skip internal-email order=%s email=%s", order_id, email)
            continue

        save_order_state(
            order_id,
            status=STATUS_INVOICE_NEEDED,
            service_type=str(order.get("service_type") or order.get("job_type") or ""),
            customer_email=str(order.get("customer_email") or order.get("email") or ""),
            client_name=str(order.get("customer_name") or order.get("client_name") or ""),
            property_address=str(
                order.get("property_address") or
                order.get("address") or
                order.get("site_address") or ""
            ),
        )
        log_decision(
            AGENT_NAME,
            decision="invoice_needed_queued",
            order_id=order_id,
            reason="Order has invoice_needed flag — queued for data collection",
            input_summary=f"FTF order id={order_id} status={order.get('status')}",
            output_summary=f"Inserted into processed_orders status={STATUS_INVOICE_NEEDED}",
            model_used=None,
        )
        log.info("new invoice_needed order queued order=%s", order_id)
        new_ids.append(order_id)

    log.info("flag_hunter complete new_queued=%s total_flagged=%s", len(new_ids), len(orders))
    return new_ids


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="A1 Flag Hunter — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    args = parser.parse_args(argv)

    if args.run_now:
        ids = run()
        print(f"Queued {len(ids)} new orders:")
        for oid in ids:
            print(f"  {oid}")


if __name__ == "__main__":
    main()
