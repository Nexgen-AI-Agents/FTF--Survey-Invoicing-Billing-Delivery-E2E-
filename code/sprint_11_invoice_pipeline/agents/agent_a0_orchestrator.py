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
from core.onedrive_excel_client import (
    _close_session, consume_user_learnings, recompute_user_amounts, sync_pricing_rules_to_json,
)

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

    # Sync pricing rules from Excel → data/pricing_rules.json (git-backed fallback)
    try:
        n = sync_pricing_rules_to_json()
        log.info("pricing rules synced: %d active rules", n)
    except Exception as exc:
        log.warning("pricing rules sync failed (non-fatal): %s", exc)

    # Fold operator notes (Approvals "Learning provided by user" column) into the AI's
    # learning BEFORE A3 prices, so anything the approver taught us applies this run.
    try:
        ul = consume_user_learnings()
        log.info("user-learning consume: %s", ul)
    except Exception as exc:
        log.warning("consume_user_learnings failed (non-fatal): %s", exc)

    # Refresh "Amount ($) by User" (col H) = total of the user's edited breakdown (col G),
    # for every row, so the approver always sees the live total of their edits (before AND
    # after approval). Idempotent; single-cell PATCH only.
    try:
        ra = recompute_user_amounts()
        log.info("recompute user amounts: %s", ra)
    except Exception as exc:
        log.warning("recompute_user_amounts failed (non-fatal): %s", exc)

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
        results["a7_feedback_learner"] = run_a7()  # Always runs last — learns approved prices into learned_rules.json
    except Exception as exc:
        log.error("A7 failed: %s", exc)
        results["a7_feedback_learner"] = {"error": str(exc)}

    log.info("=== Invoice Pipeline Run Complete: %s ===", results)
    return results


if __name__ == "__main__":
    import json
    # try/finally guarantees the OneDrive workbook session is released even if run() or the
    # JSON dump raises — a leaked session locks the file and breaks the NEXT run. default=str
    # keeps json.dumps from crashing on any non-serializable value an agent might return.
    try:
        _result = run()
        print(json.dumps(_result, indent=2, default=str))
    finally:
        try:
            _close_session()
        except Exception as _exc:
            log.warning("close_session on exit failed (non-fatal): %s", _exc)
