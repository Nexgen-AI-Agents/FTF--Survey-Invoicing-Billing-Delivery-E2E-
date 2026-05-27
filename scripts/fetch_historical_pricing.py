#!/usr/bin/env python3
"""
Historical Pricing Fetcher — FTF Agentic AI (I-066)
Fetches completed/delivered orders from FTF staging API and builds a pricing
reference knowledge base for the AI pricing engine.

Ryan (2026-05-26): "Take the last 1-2 years. AI should know what we've done
and see the differences."

Usage:
  python scripts/fetch_historical_pricing.py                    # fetch all, save JSON
  python scripts/fetch_historical_pricing.py --days 365         # last 1 year only
  python scripts/fetch_historical_pricing.py --dry-run          # show counts, no file write
  python scripts/fetch_historical_pricing.py --output path.json # custom output path

Output:
  code/shared/config/knowledge_base/historical_pricing_data.json
  Loaded by pricing engine as context when AI generates estimates.

Fields extracted per order:
  order_id, service_type, county, total_amount, completed_date,
  property_lat, property_lng, pricing_tier
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from dotenv import load_dotenv
load_dotenv()

from core.ftf_client import get_orders
from core.logger import get_logger

log = get_logger("fetch_historical_pricing")

_DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(__file__), "..", "code", "shared", "config", "knowledge_base",
    "historical_pricing_data.json",
)
_DIVIDER = "=" * 60

# Statuses that indicate a completed, invoiced job — priced data is reliable
_COMPLETE_STATUSES = {"Complete", "Delivered"}


def _extract_fields(order: dict) -> dict | None:
    """Extract pricing-relevant fields from a raw FTF order dict.

    Returns None if the order lacks amount data (uninvoiced/free orders).
    """
    amount = order.get("total_amount") or order.get("amount") or order.get("estimate_amount")
    if not amount or float(amount) <= 0:
        return None

    return {
        "order_id":      order.get("id") or order.get("order_id"),
        "service_type":  order.get("service_type") or order.get("job_type"),
        "county":        order.get("county") or order.get("property_county"),
        "total_amount":  float(amount),
        "pricing_tier":  order.get("pricing_tier") or order.get("customer_type") or "individual",
        "property_lat":  order.get("property_lat"),
        "property_lng":  order.get("property_lng"),
        "completed_date": (
            order.get("completed_at") or order.get("delivered_at") or order.get("updated_at")
        ),
        "is_flood_zone": order.get("is_flood_zone") or False,
    }


def fetch_historical(days: int = 730, dry_run: bool = False) -> list[dict]:
    """Fetch completed orders from FTF API within the last `days` days.

    Returns a list of extracted pricing records.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    print(f"\n  Fetching FTF completed orders since {since} (last {days} days)...")

    records: list[dict] = []
    fetched_total = 0
    skipped = 0

    for status in _COMPLETE_STATUSES:
        log.info("fetching status=%s since=%s", status, since)
        try:
            orders = get_orders(
                status=status.lower(),
                extra_params={"date_from": since},
                max_results=5000,
            )
        except Exception as exc:
            log.error("FTF API fetch failed for status=%s: %s", status, exc)
            print(f"  WARNING: could not fetch '{status}' orders — {exc}")
            continue

        fetched_total += len(orders)
        for order in orders:
            rec = _extract_fields(order)
            if rec:
                records.append(rec)
            else:
                skipped += 1

    log.info(
        "historical fetch complete: fetched=%d extracted=%d skipped=%d",
        fetched_total, len(records), skipped,
    )
    return records


def build_summary(records: list[dict]) -> dict:
    """Build aggregate statistics from the extracted records."""
    by_service: dict[str, list[float]] = {}
    by_county: dict[str, list[float]] = {}

    for rec in records:
        svc = rec.get("service_type") or "Unknown"
        amt = rec["total_amount"]
        by_service.setdefault(svc, []).append(amt)

        cty = rec.get("county") or "Unknown"
        by_county.setdefault(cty, []).append(amt)

    def _stats(amounts: list[float]) -> dict:
        n = len(amounts)
        return {
            "count": n,
            "avg":   round(sum(amounts) / n, 2) if n else 0,
            "min":   round(min(amounts), 2) if n else 0,
            "max":   round(max(amounts), 2) if n else 0,
        }

    return {
        "total_orders": len(records),
        "by_service_type": {svc: _stats(amts) for svc, amts in sorted(by_service.items())},
        "by_county": {cty: _stats(amts) for cty, amts in sorted(by_county.items())},
    }


def save_output(records: list[dict], output_path: str, dry_run: bool) -> None:
    """Save records + summary to JSON knowledge base file."""
    summary = build_summary(records)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "summary": summary,
        "records": records,
    }

    if dry_run:
        print(f"\n  [dry-run] Would write {len(records)} records to {output_path}")
        print(f"  Summary: {summary['total_orders']} orders across "
              f"{len(summary['by_service_type'])} service types, "
              f"{len(summary['by_county'])} counties")
        return

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"\n  Saved {len(records)} records → {output_path}")
    log.info("historical pricing data saved: %d records → %s", len(records), output_path)


def print_summary_table(summary: dict) -> None:
    print()
    print(_DIVIDER)
    print("  PRICING SUMMARY BY SERVICE TYPE")
    print(_DIVIDER)
    print(f"  {'Service Type':<35} {'Count':>6} {'Avg':>8} {'Min':>8} {'Max':>8}")
    print("  " + "-" * 58)
    for svc, stats in summary["by_service_type"].items():
        print(f"  {svc:<35} {stats['count']:>6} ${stats['avg']:>7,.0f} "
              f"${stats['min']:>7,.0f} ${stats['max']:>7,.0f}")

    print()
    print(_DIVIDER)
    print("  PRICING SUMMARY BY COUNTY")
    print(_DIVIDER)
    print(f"  {'County':<25} {'Count':>6} {'Avg':>8} {'Min':>8} {'Max':>8}")
    print("  " + "-" * 50)
    for cty, stats in list(summary["by_county"].items())[:20]:
        print(f"  {cty:<25} {stats['count']:>6} ${stats['avg']:>7,.0f} "
              f"${stats['min']:>7,.0f} ${stats['max']:>7,.0f}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch FTF historical pricing data for AI pricing engine"
    )
    parser.add_argument("--days",    type=int, default=730, help="How many days back to fetch (default: 730)")
    parser.add_argument("--output",  type=str, default=_DEFAULT_OUTPUT, help="Output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Show stats only, do not write file")
    args = parser.parse_args()

    print()
    print(_DIVIDER)
    print("  FTF Historical Pricing Fetcher")
    print(f"  Lookback : {args.days} days")
    print(f"  Output   : {args.output}")
    print(f"  Dry Run  : {args.dry_run}")
    print(_DIVIDER)

    records = fetch_historical(days=args.days, dry_run=args.dry_run)

    if not records:
        print("\n  No records extracted — check FTF API connectivity and credentials.")
        sys.exit(1)

    summary = build_summary(records)
    print_summary_table(summary)
    save_output(records, args.output, args.dry_run)

    print()
    print(f"  Total orders extracted : {summary['total_orders']}")
    print(f"  Service types found    : {len(summary['by_service_type'])}")
    print(f"  Counties found         : {len(summary['by_county'])}")
    print()


if __name__ == "__main__":
    main()
