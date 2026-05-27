#!/usr/bin/env python3
"""
E2E QA Test Runner — FTF Agentic AI Pipeline
I-058: Traces one QA order through all 7 pipeline agents and validates each stage.

Usage:
  python scripts/e2e_qa_runner.py                   # seed + run + validate + cleanup
  python scripts/e2e_qa_runner.py --no-cleanup       # leave QA orders in DB after run
  python scripts/e2e_qa_runner.py --scenario boundary-flood  # test specific scenario
  python scripts/e2e_qa_runner.py --dry-run          # show what would run, no DB writes

QA Lifecycle (per I-058):
  1. Seed a QA order at status='classified' via qa_orders.py
  2. Run each agent in sequence: pricing -> writer -> reviewer (-> sender is skipped — no real email)
  3. Validate DB state at each stage
  4. Report PASS/FAIL per stage
  5. Cleanup QA orders

Agents 2+3 (monitor, classifier) are bypassed — QA orders inject at classified.
Agent 4 (human gate) is bypassed for non-flagged scenarios — classified goes straight to pricing.
Agent 8 (sender) is DRY-RUN only — no real email sent to customer.
Agent 9 (reporter) is skipped — tested separately.
"""

import os
import sys
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_02_classifier_pricing", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_03_human_gate", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_04_writer", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_05_reviewer", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_06_sender_reporter", "agents"))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import psycopg2.extras

from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

_DIVIDER = "=" * 68
_PASS = "PASS"
_FAIL = "FAIL"
_SKIP = "SKIP"


def _connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def _get_order(order_id: str) -> dict | None:
    conn = _connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM processed_orders WHERE order_id = %s LIMIT 1",
                    (order_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        conn.close()


def _status(order_id: str) -> str | None:
    row = _get_order(order_id)
    return row["status"] if row else None


def _check(label: str, actual, expected, results: list) -> bool:
    ok = actual == expected
    tag = _PASS if ok else _FAIL
    print(f"  [{tag}] {label}: expected={expected!r} actual={actual!r}")
    results.append((label, ok))
    return ok


def _header(text: str):
    print()
    print(_DIVIDER)
    print(f"  {text}")
    print(_DIVIDER)


def seed_qa_order(scenario_id: str, dry_run: bool) -> str | None:
    """Seed a QA order and return its order_id."""
    _header(f"STEP 0 — Seed QA order: {scenario_id}")
    from qa_orders import _SCENARIO_MAP, insert_qa_order, _make_order_id
    scenario = _SCENARIO_MAP.get(scenario_id)
    if not scenario:
        print(f"  ERROR: unknown scenario '{scenario_id}'")
        return None
    order_id = insert_qa_order(scenario, dry_run=dry_run)
    if dry_run:
        print(f"  [dry-run] would seed {order_id}")
        return order_id
    row = _get_order(order_id)
    if row:
        print(f"  Seeded {order_id} status={row['status']}")
    return order_id


def run_pricing(order_id: str, dry_run: bool, results: list) -> bool:
    """Run Agent 5 — Pricing Engine."""
    _header("STEP 1 — Agent 5: Pricing Engine")
    if dry_run:
        print("  [dry-run] would call agent_05_pricing_engine.run()")
        results.append(("pricing agent", True))
        return True
    try:
        import agent_05_pricing_engine as pricing
        result = pricing.run()
        if result is None:
            _check("pricing.run() found classified order", False, True, results)
            return False
        _check("pricing result has order_id", result.get("order_id"), order_id, results)
        _check("status after pricing", _status(order_id), "priced", results)
        _check("estimate_amount set", result.get("total_amount", 0) > 0, True, results)
        print(f"  Priced at ${result.get('total_amount', 0):,.2f} tier={result.get('pricing_tier')}")
        return True
    except Exception as exc:
        _check("pricing agent ran without exception", str(exc)[:60], "no exception", results)
        return False


def run_writer(order_id: str, dry_run: bool, results: list) -> bool:
    """Run Agent 6 — Estimate Writer."""
    _header("STEP 2 — Agent 6: Estimate Writer")
    if dry_run:
        print("  [dry-run] would call agent_06_writer.run()")
        results.append(("writer agent", True))
        return True
    try:
        import agent_06_writer as writer
        result = writer.run()
        if result is None:
            _check("writer.run() found priced order", False, True, results)
            return False
        _check("status after writer", _status(order_id), "written", results)
        row = _get_order(order_id)
        _check("draft_estimate not empty", bool(row and row.get("draft_estimate")), True, results)
        print(f"  Draft written ({len((row or {}).get('draft_estimate') or '')} chars)")
        return True
    except Exception as exc:
        _check("writer agent ran without exception", str(exc)[:60], "no exception", results)
        return False


def run_reviewer(order_id: str, dry_run: bool, results: list) -> bool:
    """Run Agent 7 — Estimate Reviewer."""
    _header("STEP 3 — Agent 7: Estimate Reviewer")
    if dry_run:
        print("  [dry-run] would call agent_07_reviewer.run()")
        results.append(("reviewer agent", True))
        return True
    try:
        import agent_07_reviewer as reviewer
        result = reviewer.run()
        if result is None:
            _check("reviewer.run() found written order", False, True, results)
            return False
        _check("status after reviewer", _status(order_id), "reviewed", results)
        print(f"  Reviewer result: {result}")
        return True
    except Exception as exc:
        _check("reviewer agent ran without exception", str(exc)[:60], "no exception", results)
        return False


def validate_final_state(order_id: str, results: list):
    """Validate the final DB record has all expected timestamps."""
    _header("STEP 4 — Final State Validation")
    row = _get_order(order_id)
    if not row:
        _check("order exists in DB", False, True, results)
        return
    _check("classified_at is set", row.get("classified_at") is not None, True, results)
    _check("priced_at is set", row.get("priced_at") is not None, True, results)
    _check("written_at is set", row.get("written_at") is not None, True, results)
    _check("reviewed_at is set", row.get("reviewed_at") is not None, True, results)
    _check("status = reviewed", row.get("status"), "reviewed", results)
    _check("estimate_amount > 0", float(row.get("estimate_amount") or 0) > 0, True, results)


def cleanup(order_id: str, dry_run: bool):
    """Remove the QA order and its decision log entries."""
    _header("STEP 5 — Cleanup")
    if dry_run:
        print("  [dry-run] would delete QA order")
        return
    conn = _connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM agent_decision_log WHERE order_id = %s", (order_id,))
                cur.execute("DELETE FROM processed_orders WHERE order_id = %s", (order_id,))
        print(f"  Deleted {order_id} and its decision log entries.")
    finally:
        conn.close()


def print_summary(order_id: str, results: list, elapsed_s: float):
    _header("QA SUMMARY")
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed
    print(f"  Order ID : {order_id}")
    print(f"  Tests    : {total}")
    print(f"  Passed   : {passed}")
    print(f"  Failed   : {failed}")
    print(f"  Elapsed  : {elapsed_s:.1f}s")
    print()
    if failed == 0:
        print("  RESULT: ALL CHECKS PASSED - E2E pipeline healthy")
    else:
        print(f"  RESULT: {failed} CHECK(S) FAILED - investigate before production")
        for label, ok in results:
            if not ok:
                print(f"    FAILED: {label}")
    print()
    return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="E2E QA runner for FTF Agentic AI pipeline"
    )
    parser.add_argument("--scenario", default="boundary-individual",
                        help="QA scenario ID (default: boundary-individual)")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Leave QA order in DB after test run")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would run without DB writes or API calls")
    args = parser.parse_args()

    print()
    print(_DIVIDER)
    print("  FTF Agentic AI — E2E QA Runner")
    print(f"  Scenario  : {args.scenario}")
    print(f"  Dry Run   : {args.dry_run}")
    print(f"  Cleanup   : {not args.no_cleanup}")
    print(_DIVIDER)

    results = []
    start = datetime.now(timezone.utc)

    # Step 0: Seed
    order_id = seed_qa_order(args.scenario, dry_run=args.dry_run)
    if not order_id:
        print("\nABORTED: could not seed QA order.")
        sys.exit(1)

    try:
        # Step 1-3: Pipeline agents
        pricing_ok  = run_pricing(order_id,  dry_run=args.dry_run, results=results)
        writer_ok   = run_writer(order_id,   dry_run=args.dry_run, results=results) if pricing_ok  else False
        reviewer_ok = run_reviewer(order_id, dry_run=args.dry_run, results=results) if writer_ok   else False

        if not pricing_ok:
            print("\n  [SKIP] Writer + Reviewer skipped — pricing failed")
        elif not writer_ok:
            print("\n  [SKIP] Reviewer skipped — writer failed")

        # Step 4: Final state validation
        if not args.dry_run:
            validate_final_state(order_id, results)

    finally:
        # Step 5: Cleanup (always — unless --no-cleanup)
        if not args.no_cleanup:
            cleanup(order_id, dry_run=args.dry_run)
        else:
            print()
            print(f"  --no-cleanup set: QA order {order_id} left in DB")

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    all_passed = print_summary(order_id, results, elapsed)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
