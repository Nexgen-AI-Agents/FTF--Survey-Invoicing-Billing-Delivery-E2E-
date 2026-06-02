"""Approval poller — A4 → A5 → A6 only.

Called every 2 minutes by .github/workflows/approval_poller.yml.
Checks Teams threads for replies, creates invoices, and sends emails.
Does NOT run A1/A2/A3 (new order discovery/pricing) — those stay in the
30-minute main pipeline so this loop stays fast (~30s per cycle).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from agents.agent_a4_human_gate_v2     import run as run_a4
from agents.agent_a5_invoice_finalizer import run as run_a5
from agents.agent_a6_sender_v2         import run as run_a6
from core.logger import get_logger

log = get_logger("run_approval_poller")

if __name__ == "__main__":
    results = {}
    for label, fn in [("a4_human_gate", run_a4), ("a5_invoice_finalizer", run_a5), ("a6_sender", run_a6)]:
        try:
            results[label] = fn()
        except Exception as exc:
            log.error("%s failed: %s", label, exc)
            results[label] = {"error": str(exc)}

    log.info("approval poller complete: %s", results)
    print(json.dumps(results, indent=2, default=str))
