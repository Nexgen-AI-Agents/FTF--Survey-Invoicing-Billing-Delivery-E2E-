"""Agent A0 — Invoice Pipeline Orchestrator

Runs the full invoice pipeline in sequence.
Called by GitHub Actions (manual or scheduled).

Pipeline:
  A1 → A2 → A3 → A4 → A5 → A6 → A7

  A1: MySQL flag scan — queues invoice_needed orders
  A2: Data collection — FTF API, email, property appraiser, aerial image
  A3: AI pricing — writes draft row to OneDrive Excel (FTF-Invoicing Agent.xlsx)
  A4: No-op in this run — approval comes from Power Automate workflow_dispatch
  A5: FTF invoice creation — runs after A4 approves (via approval_poller.yml)
  A6: Email send — sends invoice to client (via approval_poller.yml)
  A7: Feedback learner — no-op stub (Teams retired; Excel learning TBD)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from core.logger import get_logger
from core.onedrive_excel_client import _close_session

log = get_logger("agent_a0_orchestrator")

# Import all agents
from agents.agent_a1_flag_hunter      import run as run_a1
from agents.agent_a2_data_collector   import run as run_a2
from agents.agent_a3_invoice_compiler import run as run_a3
from agents.agent_a4_human_gate_v2    import run as run_a4
from agents.agent_a5_invoice_finalizer import run as run_a5
from agents.agent_a6_sender_v2        import run as run_a6
from agents.agent_a7_feedback_learner import run as run_a7


def run() -> dict:
    """Run the full invoice pipeline. Returns summary of all agent runs."""
    results = {}

    log.info("=== Invoice Pipeline Run Started ===")

    try:
        results["a1_flag_hunter"]     = {"new_queued": len(run_a1())}
    except Exception as exc:
        log.error("A1 failed: %s", exc)
        results["a1_flag_hunter"] = {"error": str(exc)}

    try:
        results["a2_data_collector"]  = run_a2()
    except Exception as exc:
        log.error("A2 failed: %s", exc)
        results["a2_data_collector"] = {"error": str(exc)}

    try:
        results["a3_invoice_compiler"] = run_a3()
    except Exception as exc:
        log.error("A3 failed: %s", exc)
        results["a3_invoice_compiler"] = {"error": str(exc)}

    try:
        results["a4_human_gate"]      = run_a4()  # Always run — checks for replies
    except Exception as exc:
        log.error("A4 failed: %s", exc)
        results["a4_human_gate"] = {"error": str(exc)}

    try:
        results["a5_invoice_finalizer"] = run_a5()
    except Exception as exc:
        log.error("A5 failed: %s", exc)
        results["a5_invoice_finalizer"] = {"error": str(exc)}

    try:
        results["a6_sender"]          = run_a6()
    except Exception as exc:
        log.error("A6 failed: %s", exc)
        results["a6_sender"] = {"error": str(exc)}

    try:
        results["a7_feedback_learner"] = run_a7()  # Always runs last — no-op stub until Excel learning is implemented
    except Exception as exc:
        log.error("A7 failed: %s", exc)
        results["a7_feedback_learner"] = {"error": str(exc)}

    log.info("=== Invoice Pipeline Run Complete: %s ===", results)

    # Release the OneDrive workbook session so the file is not locked for raw uploads
    _close_session()

    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
