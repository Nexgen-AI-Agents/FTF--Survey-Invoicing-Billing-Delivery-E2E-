"""Excel Approval Watcher — A4 → A5 → A6.

Polls FTF-Invoicing Agent.xlsx on OneDrive for rows where Action has been
set (Approve / Reject / On-hold) but Processed At is still empty.

For each pending decision:
  A4 — records the approval/rejection/hold in pipeline state
  A5 — creates the FTF invoice (approved orders only)
  A6 — delivers the invoice via FTF native send (approved orders only)

Triggered by GitHub Actions on a 5-minute schedule, or via workflow_dispatch
for an immediate check.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from agents.agent_a4_human_gate_v2     import process_dispatch_input
from agents.agent_a5_invoice_finalizer import run as run_a5
from agents.agent_a6_sender_v2         import run as run_a6
from core.logger import get_logger
from core.onedrive_excel_client        import get_pending_approvals

log = get_logger("run_excel_watcher")


if __name__ == "__main__":
    results: dict = {"pending": 0, "a4_results": [], "a5": {}, "a6": {}}

    # ── Step 1: read pending decisions from OneDrive Excel ────────────────────
    try:
        pending = get_pending_approvals()
    except Exception as exc:
        log.error("get_pending_approvals failed: %s", exc)
        print(json.dumps({"error": str(exc)}, indent=2))
        sys.exit(1)

    results["pending"] = len(pending)

    if not pending:
        log.info("excel_watcher: no pending approvals — nothing to do")
        print(json.dumps(results, indent=2, default=str))
        sys.exit(0)

    log.info("excel_watcher: %d pending decision(s) found", len(pending))

    # ── Step 2: A4 — process each decision ───────────────────────────────────
    for item in pending:
        order_id = item["order_id"]
        action   = item["action"]   # approve / reject / hold
        notes    = item["notes"]

        os.environ["INPUT_ORDER_ID"]  = order_id
        os.environ["INPUT_ACTION"]    = action
        os.environ["INPUT_NOTES"]     = notes
        os.environ["INPUT_AMOUNT"]    = str(item.get("amount_cell", ""))
        os.environ["INPUT_BREAKDOWN"] = str(item.get("breakdown_cell", ""))

        try:
            r = process_dispatch_input()
            results["a4_results"].append(r)
            log.info("a4 processed order=%s action=%s result=%s", order_id, action, r)
        except Exception as exc:
            log.error("a4 failed order=%s: %s", order_id, exc)
            results["a4_results"].append({"order_id": order_id, "error": str(exc)})

    # ── Step 3: A5 + A6 — finalize and deliver all newly approved invoices ───
    for label, fn in [("a5_invoice_finalizer", run_a5), ("a6_sender", run_a6)]:
        try:
            results[label.split("_")[0]] = fn()
        except Exception as exc:
            log.error("%s failed: %s", label, exc)
            results[label.split("_")[0]] = {"error": str(exc)}

    log.info("excel_watcher complete: %s", results)
    print(json.dumps(results, indent=2, default=str))
