#!/usr/bin/env python3
"""data-quality-check: Full data quality scan of pipeline_state.json.

Reports: status distribution, sentinel values, missing fields, phantom rows,
duplicate addresses, escalated orders. Single command to spot all data issues.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXCEL_PATH  = os.path.join(BASE_DIR, "data", "invoice_pipeline_state.xlsx")
STATE_FILE  = os.path.join(BASE_DIR, "data", "pipeline_state.json")  # fallback only

_SENTINELS = {"unknown", "n/a", "none", "not available", "not found", ""}

NUMERIC_ID = re.compile(r'^\d{7,12}$')


def _is_sentinel(val) -> bool:
    return str(val or "").strip().lower() in _SENTINELS


def load() -> list[dict]:
    """Load orders from Excel (live source). Falls back to JSON snapshot if Excel locked."""
    if os.path.exists(EXCEL_PATH):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
            ws = wb["pipeline_state"]
            rows = list(ws.iter_rows(values_only=True))
            if len(rows) < 2:
                return []
            headers = [str(h) if h is not None else "" for h in rows[0]]
            orders = [
                {headers[i]: (row[i] if i < len(row) else None) for i in range(len(headers))}
                for row in rows[1:]
            ]
            wb.close()
            print(f"  Source: Excel ({len(orders)} rows)  [live]")
            return orders
        except Exception as exc:
            print(f"  Excel locked/unreadable ({exc}), falling back to JSON snapshot")

    if not os.path.exists(STATE_FILE):
        sys.exit(f"Neither Excel nor pipeline_state.json found.")
    with open(STATE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    orders = data.get("orders", data) if isinstance(data, dict) else data
    print(f"  Source: JSON snapshot ({len(orders)} rows)  [may be stale]")
    return orders


def check(orders: list[dict]) -> dict:
    results = {
        "total": len(orders),
        "status_dist": Counter(),
        "phantom_rows": [],
        "sentinel_client": [],
        "sentinel_address": [],
        "null_service_type": [],
        "null_estimate": [],
        "zero_estimate": [],
        "escalated": [],
        "duplicate_addresses": defaultdict(list),
    }

    for o in orders:
        oid    = str(o.get("order_id") or "")
        status = str(o.get("status") or "NULL")

        # phantom rows
        if not NUMERIC_ID.match(oid):
            results["phantom_rows"].append(oid)
            continue  # skip rest of checks for phantoms

        results["status_dist"][status] += 1

        # sentinel checks
        if _is_sentinel(o.get("client_name")):
            results["sentinel_client"].append((oid, status, o.get("client_name")))
        if _is_sentinel(o.get("property_address")):
            results["sentinel_address"].append((oid, status, o.get("property_address")))

        # missing service_type
        if not o.get("service_type"):
            results["null_service_type"].append((oid, status))

        # estimate_amount
        amt = o.get("estimate_amount")
        if amt is None or str(amt).strip() == "":
            results["null_estimate"].append((oid, status))
        elif str(amt).strip() in ("0", "0.0"):
            results["zero_estimate"].append((oid, status))

        # escalated
        if o.get("escalate_flag"):
            results["escalated"].append((oid, status))

        # duplicate addresses
        addr = str(o.get("property_address") or "").strip().upper()
        if addr and not _is_sentinel(addr):
            results["duplicate_addresses"][addr].append(oid)

    # keep only actually duplicated addresses
    results["duplicate_addresses"] = {
        addr: ids for addr, ids in results["duplicate_addresses"].items()
        if len(ids) > 1
    }

    return results


def report(r: dict) -> int:
    """Print report. Returns exit code: 0=PASS, 1=issues found."""
    W = 66
    print(f"\n{'='*W}")
    print("  DATA QUALITY CHECK")
    print(f"  Total orders: {r['total']}")
    print(f"{'='*W}\n")

    # Status distribution
    print("STATUS DISTRIBUTION:")
    for status, count in sorted(r["status_dist"].items(), key=lambda x: -x[1]):
        print(f"  {status:<35} {count:>4}")
    print()

    issues = 0

    def section(title, items, fmt=None):
        nonlocal issues
        if not items:
            print(f"[PASS] {title}: 0")
            return
        issues += len(items)
        print(f"[FAIL] {title}: {len(items)}")
        for item in items[:8]:
            print(f"       {fmt(item) if fmt else item}")
        if len(items) > 8:
            print(f"       ... and {len(items) - 8} more")
        print()

    print("-" * W)
    section("Phantom rows (non-numeric order_id)", r["phantom_rows"],
            fmt=lambda x: x)
    section("Sentinel client_name",   r["sentinel_client"],
            fmt=lambda x: f"{x[0]}  status={x[1]}  value={x[2]!r}")
    section("Sentinel property_address", r["sentinel_address"],
            fmt=lambda x: f"{x[0]}  status={x[1]}  value={x[2]!r}")
    section("Null service_type",      r["null_service_type"],
            fmt=lambda x: f"{x[0]}  status={x[1]}")
    section("Null estimate_amount",   r["null_estimate"],
            fmt=lambda x: f"{x[0]}  status={x[1]}")
    section("Zero estimate_amount",   r["zero_estimate"],
            fmt=lambda x: f"{x[0]}  status={x[1]}")

    # Escalated — informational, not a data quality failure
    esc = r["escalated"]
    print(f"[INFO] Escalated orders (escalate_flag=True): {len(esc)}")
    print()

    # Duplicate addresses — informational
    dups = r["duplicate_addresses"]
    print(f"[INFO] Duplicate address groups: {len(dups)}")
    for addr, ids in list(dups.items())[:5]:
        print(f"       {addr[:50]:<52}  {ids}")
    if len(dups) > 5:
        print(f"       ... and {len(dups) - 5} more groups")
    print()

    # Verdict
    print("=" * W)
    if issues == 0:
        print("  VERDICT: PASS -- no data quality issues")
    else:
        print(f"  VERDICT: FAIL -- {issues} issue(s) found")
    print("=" * W)
    print()
    return 1 if issues else 0


def main():
    orders  = load()
    results = check(orders)
    sys.exit(report(results))


if __name__ == "__main__":
    main()
