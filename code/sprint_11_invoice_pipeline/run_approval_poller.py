"""Approval poller — A4 → A5 → A6.

Triggered by Power Automate via GitHub Actions workflow_dispatch when the user
changes a row Status in the OneDrive approval spreadsheet (FTF-Invoicing Agent.xlsx).

Inputs (from workflow_dispatch):
  INPUT_ORDER_ID  — order to process
  INPUT_ACTION    — approve / reject / hold
  INPUT_NOTES     — optional notes

A4 reads these inputs, applies the action, then A5 creates the FTF invoice
and A6 sends the email to the client.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from agents.agent_a4_human_gate_v2     import process_dispatch_input
from agents.agent_a5_invoice_finalizer import run as run_a5
from agents.agent_a6_sender_v2         import run as run_a6
from core.logger import get_logger

log = get_logger("run_approval_poller")

if __name__ == "__main__":
    results = {}

    # A4 — process the dispatch input (approve/reject/hold one order)
    try:
        results["a4_human_gate"] = process_dispatch_input()
    except Exception as exc:
        log.error("a4_human_gate failed: %s", exc)
        results["a4_human_gate"] = {"error": str(exc)}

    # A5 + A6 — pick up any newly approved orders and send invoices
    for label, fn in [("a5_invoice_finalizer", run_a5), ("a6_sender", run_a6)]:
        try:
            results[label] = fn()
        except Exception as exc:
            log.error("%s failed: %s", label, exc)
            results[label] = {"error": str(exc)}

    log.info("approval poller complete: %s", results)
    print(json.dumps(results, indent=2, default=str))
