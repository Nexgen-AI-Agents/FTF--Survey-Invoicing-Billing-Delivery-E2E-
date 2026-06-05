"""release_test_orders.py — Reset test orders back to data_collected so the cron picks them up.

invoice_sent orders are left untouched (invoices already exist in FTF).
rejected/on_hold orders are reset to data_collected so A3 re-queues them.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from core.excel_db import get_order_by_id, save_order_state
from core.logger import get_logger

log = get_logger("release_test_orders")

# Orders to release back to data_collected
RESET_ORDERS = [
    "1000282430",  # rejected
    "1000282337",  # rejected
    "1000282280",  # rejected
    "1000282846",  # on_hold
    "1000283289",  # on_hold
]

# invoice_sent orders — leave these alone (FTF invoices already created)
SKIP_ORDERS = {"1000282513", "1000283728", "1000283564", "1000283486"}


def main():
    for order_id in RESET_ORDERS:
        row = get_order_by_id(order_id)
        if not row:
            log.warning("order %s not in pipeline state — skipping", order_id)
            continue
        current = row.get("status", "")
        save_order_state(order_id, status="data_collected")
        log.info("reset order=%s  %s → data_collected", order_id, current)

    print(f"Done — reset {len(RESET_ORDERS)} orders to data_collected")
    print(f"Skipped invoice_sent orders: {sorted(SKIP_ORDERS)}")


if __name__ == "__main__":
    main()
