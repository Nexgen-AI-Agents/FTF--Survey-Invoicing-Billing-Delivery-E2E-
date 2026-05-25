import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from core.ftf_client import get_orders
from core.db import order_exists, save_order_state, log_decision
from core.logger import get_logger

AGENT_NAME = "agent_02_monitor"
log = get_logger(AGENT_NAME)


def run() -> list[str]:
    """Poll FTF CRM for new Quote orders; persist new ones to state DB.

    Returns list of newly detected order IDs.
    Uses server-side status=Quote filter + full pagination — never misses orders.
    Orders already in processed_orders (any status) are skipped — never reset.
    No LLM calls — pure API + DB logic.
    """
    orders = get_orders(status="Quote")
    new_order_ids: list[str] = []

    for order in orders:
        order_id = str(order["order_id"])

        # Skip if estimate already sent — server filter gives us Quote orders only,
        # but estimate_sent is not a server-side filter so we check it here.
        if order.get("estimate_sent") is True:
            log.debug("skip already-estimated order=%s", order_id)
            continue

        if order_exists(order_id):
            log.debug("skip existing order=%s", order_id)
            continue

        save_order_state(order_id, status="pending")
        log_decision(
            AGENT_NAME,
            decision="new_order_detected",
            order_id=order_id,
            reason="Order not previously seen in state DB",
            input_summary=f"FTF API order id={order_id}",
            output_summary="Inserted into processed_orders with status=pending",
            model_used=None,
        )
        log.info("new order detected order=%s", order_id)
        new_order_ids.append(order_id)

    log.info("monitor complete new=%s", len(new_order_ids))
    return new_order_ids


def main(argv=None) -> list[str] | None:
    """CLI entrypoint for manual trigger.

    Usage:
      python -m agents.agent_02_monitor --run-now
    """
    import argparse

    parser = argparse.ArgumentParser(description="FTF Order Monitor — Agent 2")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Trigger a monitor run immediately and print new order IDs",
    )
    args = parser.parse_args(argv)

    if args.run_now:
        new_ids = run()
        log.info("CLI run-now complete new=%s", len(new_ids))
        for oid in new_ids:
            print(oid)
        return new_ids

    parser.print_help()
    return None


if __name__ == "__main__":
    main()
