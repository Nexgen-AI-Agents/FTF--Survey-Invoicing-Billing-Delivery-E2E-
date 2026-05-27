#!/usr/bin/env python3
"""
QA Order Seeding Utility
Usage:
  python scripts/qa_orders.py create              # insert all 8 test scenarios
  python scripts/qa_orders.py create --id boundary-flood   # one scenario
  python scripts/qa_orders.py list                # show QA orders + pipeline status
  python scripts/qa_orders.py cleanup             # delete all QA orders from DB

Why classified, not pending?
  The classifier (agent_03) calls GET /orders/{id} on the FTF API.
  QA order IDs don't exist in FTF, so a 'pending' injection would 404 there.
  Injecting at 'classified' (post-classifier) lets agents 5-8 run with real
  FTF pricing/Anthropic calls while bypassing the FTF API read dependency.
  Agents 2-3 are covered by unit tests and the Sprint 10 staging test.

QA order ID format:  QA-YYYYMMDD-<scenario-slug>
Cleanup filter:      order_id LIKE 'QA-%'
"""

import os
import sys
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import psycopg2.extras

from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from core.logger import get_logger

log = get_logger("qa_orders")

# --- Scenario catalogue -------------------------------------------------------
# Each scenario is what agent_03_classifier would have produced and persisted.
# Fields map directly to processed_orders columns.

QA_SCENARIOS: list[dict] = [
    {
        "id": "boundary-individual",
        "service_type": "Boundary Survey",
        "customer_email": "qa-buyer@nexgen-qa.invalid",
        "property_lat": 26.7998,
        "property_lng": -80.0642,
        "is_flood_zone": False,
        "customer_type": "individual",
        "status": "classified",
        "flag_reason": None,
        "note": "Standard individual boundary -- clean path through pricing->writer->reviewer",
    },
    {
        "id": "boundary-flood",
        "service_type": "Boundary Survey",
        "customer_email": "qa-flood@nexgen-qa.invalid",
        "property_lat": 25.7617,
        "property_lng": -80.1918,
        "is_flood_zone": True,
        "customer_type": "individual",
        "status": "classified",
        "flag_reason": None,
        "note": "AE flood zone -- elevation cert upcharge expected in pricing",
    },
    {
        "id": "topo-b2b",
        "service_type": "Topography Survey",
        "customer_email": "qa-b2b@acme-title.invalid",
        "property_lat": 28.5383,
        "property_lng": -81.3792,
        "is_flood_zone": False,
        "customer_type": "b2b",
        "status": "classified",
        "flag_reason": None,
        "note": "B2B topography -- should use b2b pricing tier",
    },
    {
        "id": "final-survey",
        "service_type": "Final Survey",
        "customer_email": "qa-final@nexgen-qa.invalid",
        "property_lat": 27.9506,
        "property_lng": -82.4572,
        "is_flood_zone": False,
        "customer_type": "individual",
        "status": "classified",
        "flag_reason": None,
        "note": "Final survey -- standard Tampa-area residential",
    },
    {
        "id": "form-board",
        "service_type": "Form Board Survey",
        "customer_email": "qa-formboard@nexgen-qa.invalid",
        "property_lat": 30.3322,
        "property_lng": -81.6557,
        "is_flood_zone": False,
        "customer_type": "individual",
        "status": "classified",
        "flag_reason": None,
        "note": "Form board survey -- Jacksonville area",
    },
    {
        "id": "update-survey",
        "service_type": "Update Survey",
        "customer_email": "qa-update@nexgen-qa.invalid",
        "property_lat": 29.6516,
        "property_lng": -82.3248,
        "is_flood_zone": False,
        "customer_type": "individual",
        "status": "classified",
        "flag_reason": None,
        "note": "Update survey -- Gainesville area",
    },
    {
        "id": "elevation-cert-flagged",
        "service_type": "Elevation Certificate",
        "customer_email": "qa-elev@nexgen-qa.invalid",
        "property_lat": 25.7617,
        "property_lng": -80.1918,
        "is_flood_zone": True,
        "customer_type": "individual",
        "status": "flagged",
        "flag_reason": "service requires human review: Elevation Certificate",
        "note": "ALWAYS_FLAG service -- should route to human gate (agent_04)",
    },
    {
        "id": "alta-b2b-flagged",
        "service_type": "ALTA Table A Survey",
        "customer_email": "qa-alta@acme-title.invalid",
        "property_lat": 26.1224,
        "property_lng": -80.1373,
        "is_flood_zone": False,
        "customer_type": "b2b",
        "status": "flagged",
        "flag_reason": "service requires human review: ALTA Table A Survey",
        "note": "ALWAYS_FLAG service -- human gate required before pricing",
    },
]

_SCENARIO_MAP = {s["id"]: s for s in QA_SCENARIOS}


# --- DB helpers --------------------------------------------------------------

def _connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def _make_order_id(scenario_id: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"QA-{today}-{scenario_id}"


def _slugify(name: str) -> str:
    """Convert a free-form name to a URL-safe slug for use in order IDs."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def insert_qa_order(scenario: dict, dry_run: bool = False) -> str:
    """Insert one QA scenario into processed_orders. Returns order_id."""
    order_id = _make_order_id(scenario["id"])
    now = datetime.now(timezone.utc).isoformat()

    if dry_run:
        print(f"  [dry-run] would insert order_id={order_id} status={scenario['status']}")
        return order_id

    conn = _connect()
    try:
        with conn:
            with conn.cursor() as cur:
                # Check for existing QA order with same ID today
                cur.execute(
                    "SELECT status FROM processed_orders WHERE order_id = %s",
                    (order_id,),
                )
                existing = cur.fetchone()
                if existing:
                    print(f"  SKIP  {order_id} -- already exists (status={existing[0]})")
                    return order_id

                cols = [
                    "order_id", "status", "service_type", "customer_email",
                    "property_lat", "property_lng", "is_flood_zone",
                    "classified_at",
                ]
                vals = [
                    order_id,
                    scenario["status"],
                    scenario["service_type"],
                    scenario["customer_email"],
                    scenario["property_lat"],
                    scenario["property_lng"],
                    scenario["is_flood_zone"],
                    now,
                ]

                if scenario.get("flag_reason"):
                    cols.append("flag_reason")
                    vals.append(scenario["flag_reason"])
                    cols.append("flagged_at")
                    vals.append(now)

                placeholders = ", ".join(["%s"] * len(cols))
                cur.execute(
                    f"INSERT INTO processed_orders ({', '.join(cols)}) VALUES ({placeholders})",
                    vals,
                )
    finally:
        conn.close()

    return order_id


def list_qa_orders() -> list[dict]:
    """Return all QA orders currently in processed_orders."""
    conn = _connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT order_id, status, service_type, customer_email,
                           estimate_amount, is_flood_zone, flag_reason,
                           classified_at, priced_at, written_at, reviewed_at, sent_at
                    FROM processed_orders
                    WHERE order_id LIKE 'QA-%'
                    ORDER BY classified_at DESC
                    """
                )
                return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def cleanup_qa_orders(dry_run: bool = False) -> int:
    """Delete all QA orders from processed_orders and agent_decision_log. Returns count."""
    if dry_run:
        conn = _connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM processed_orders WHERE order_id LIKE 'QA-%'"
                    )
                    n = cur.fetchone()[0]
        finally:
            conn.close()
        print(f"  [dry-run] would delete {n} QA order(s)")
        return n

    conn = _connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM agent_decision_log WHERE order_id LIKE 'QA-%'"
                )
                cur.execute(
                    "DELETE FROM processed_orders WHERE order_id LIKE 'QA-%'"
                )
                return cur.rowcount
    finally:
        conn.close()


# --- CLI ---------------------------------------------------------------------

def cmd_create(args) -> None:
    if getattr(args, "name", None):
        # Free-form named order -- use boundary-individual as base, override id
        slug = _slugify(args.name)
        base = dict(_SCENARIO_MAP.get(args.id or "boundary-individual"))
        base["id"] = slug
        base["note"] = f"Named test order: {args.name}"
        scenarios = [base]
    elif args.id:
        scenario = _SCENARIO_MAP.get(args.id)
        if not scenario:
            valid = ", ".join(_SCENARIO_MAP.keys())
            print(f"  ERROR: unknown scenario '{args.id}'. Valid: {valid}")
            sys.exit(1)
        scenarios = [scenario]
    else:
        scenarios = QA_SCENARIOS

    print()
    print(f"  Creating {len(scenarios)} QA order(s)...")
    print()

    created = []
    for s in scenarios:
        order_id = insert_qa_order(s, dry_run=args.dry_run)
        flag_tag = " [FLAGGED]" if s["status"] == "flagged" else ""
        action = "dry-run" if args.dry_run else "inserted"
        print(f"  {action.upper():8}  {order_id}{flag_tag}")
        print(f"           {s['service_type']} | {s['customer_type']} | flood={s['is_flood_zone']}")
        print(f"           {s['note']}")
        print()
        created.append(order_id)

    if not args.dry_run:
        print(f"  {len(created)} QA order(s) seeded at 'classified' (or 'flagged') status.")
        print()
        print("  Next steps:")
        print("   - Run the estimate loop (GitHub Actions -> workflow_dispatch) to process them")
        print("   - Or run locally: python code/sprint_09_memory_loop/agents/agent_01_orchestrator.py")
        print("   - Cleanup when done: python scripts/qa_orders.py cleanup")
    print()


def cmd_list(args) -> None:
    orders = list_qa_orders()
    print()
    print(f"  QA Orders in DB: {len(orders)}")
    if not orders:
        print("  (none -- run: python scripts/qa_orders.py create)")
        print()
        return

    print()
    header = f"  {'ORDER ID':<32}  {'STATUS':<12}  {'SERVICE TYPE':<24}  {'AMOUNT':>8}  FLAG"
    print(header)
    print("  " + "-" * 90)
    for o in orders:
        amount = f"${float(o['estimate_amount']):,.0f}" if o.get("estimate_amount") else "--"
        flag = "!" if o.get("flag_reason") else ""
        print(
            f"  {o['order_id']:<32}  {o['status']:<12}  "
            f"{(o.get('service_type') or '--'):<24}  {amount:>8}  {flag}"
        )
    print()

    # Pipeline stage summary
    from collections import Counter
    status_counts = Counter(o["status"] for o in orders)
    print("  Pipeline stages: " + " | ".join(f"{k}: {v}" for k, v in sorted(status_counts.items())))
    print()


def cmd_cleanup(args) -> None:
    print()
    n = cleanup_qa_orders(dry_run=args.dry_run)
    if args.dry_run:
        pass
    else:
        print(f"  Deleted {n} QA order(s) and their decision log entries.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QA order seeding utility -- create/list/cleanup test orders in processed_orders"
    )
    parser.add_argument("command", choices=["create", "list", "cleanup"],
                        help="create: seed test orders | list: show QA orders | cleanup: delete all QA orders")
    parser.add_argument("--name", metavar="NAME",
                        help="(create) free-form order name; creates a named test order with a slugified ID")
    parser.add_argument("--id", metavar="SCENARIO_ID",
                        help="(create) insert only this scenario; omit for all 8")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would happen without writing to DB")
    args = parser.parse_args()

    print()
    print("=" * 64)
    print("  qa_orders.py -- NexGen FTF Pipeline QA Utility")
    print("=" * 64)

    if args.command == "create":
        cmd_create(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)


if __name__ == "__main__":
    main()
