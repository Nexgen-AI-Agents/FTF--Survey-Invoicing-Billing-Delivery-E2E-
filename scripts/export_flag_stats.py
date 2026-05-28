"""
export_flag_stats.py — Export flag trigger statistics for calibration review.

After 1 week of production data, run this to see:
  - Which triggers fire most
  - What % of flagged orders get instantly approved (over-aggressive trigger?)
  - Avg time from flag to decision
  - Orders that were flagged then approved with no reason → good auto-quote candidates

Usage:
    python scripts/export_flag_stats.py              # last 7 days, print to console
    python scripts/export_flag_stats.py --days 30    # last 30 days
    python scripts/export_flag_stats.py --csv flag_stats.csv
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.db import _get_conn
from core.logger import get_logger

log = get_logger("export_flag_stats")


def _query(sql: str, params=None) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def get_flag_stats(days: int = 7) -> dict:
    interval = f"{days} days"

    # Flag trigger breakdown
    triggers = _query(
        "SELECT flag_reason, COUNT(*) AS total_flagged, "
        "SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS instantly_approved, "
        "SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected "
        "FROM processed_orders "
        f"WHERE flag_reason IS NOT NULL AND flagged_at >= NOW() - INTERVAL '{interval}' "
        "GROUP BY flag_reason ORDER BY total_flagged DESC"
    )

    # Enrich with approval rate and avg decision time
    enriched = []
    for t in triggers:
        total    = t["total_flagged"]
        approved = t["instantly_approved"] or 0
        rejected = t["rejected"] or 0
        approval_rate = round(approved / total * 100, 1) if total else 0
        enriched.append({
            "flag_reason":        t["flag_reason"],
            "total_flagged":      total,
            "approved":           approved,
            "rejected":           rejected,
            "pending":            total - approved - rejected,
            "approval_rate_pct":  approval_rate,
            "recommendation":     _recommendation(approval_rate, total),
        })

    # Avg decision time (flagged_at → updated_at) for decided orders
    avg_time = _query(
        "SELECT AVG(EXTRACT(EPOCH FROM (updated_at - flagged_at))/3600) AS avg_h, "
        "MIN(EXTRACT(EPOCH FROM (updated_at - flagged_at))/3600) AS min_h, "
        "MAX(EXTRACT(EPOCH FROM (updated_at - flagged_at))/3600) AS max_h "
        "FROM processed_orders WHERE flagged_at IS NOT NULL AND updated_at IS NOT NULL "
        "AND status IN ('approved','rejected') "
        f"AND flagged_at >= NOW() - INTERVAL '{interval}'"
    )

    # Orders auto-flagged then approved instantly (< 15 min) with no reason — strong auto-quote candidates
    instant_approvals = _query(
        "SELECT order_id, service_type, flag_reason, estimate_amount "
        "FROM processed_orders "
        "WHERE flagged_at IS NOT NULL AND updated_at IS NOT NULL AND status='approved' "
        "AND EXTRACT(EPOCH FROM (updated_at - flagged_at)) < 900 "
        f"AND flagged_at >= NOW() - INTERVAL '{interval}' "
        "ORDER BY flagged_at DESC LIMIT 50"
    )

    timing = avg_time[0] if avg_time else {}
    return {
        "period_days":          days,
        "generated_at":         datetime.now(timezone.utc).isoformat(),
        "trigger_breakdown":    enriched,
        "avg_decision_hours":   round(timing.get("avg_h") or 0, 1),
        "min_decision_hours":   round(timing.get("min_h") or 0, 1),
        "max_decision_hours":   round(timing.get("max_h") or 0, 1),
        "instant_approvals":    instant_approvals,
    }


def _recommendation(approval_rate: float, total: int) -> str:
    """Suggest whether to keep, tune, or remove a flag trigger."""
    if total < 3:
        return "too few samples — wait"
    if approval_rate >= 90:
        return "REVIEW — 90%+ instantly approved: consider removing or relaxing this trigger"
    if approval_rate >= 70:
        return "MONITOR — high approval rate: may be over-flagging"
    if approval_rate <= 10:
        return "KEEP — rarely approved: trigger is well-calibrated"
    return "OK"


def print_report(stats: dict) -> None:
    print(f"\nFTF Flag Calibration Report — last {stats['period_days']} days")
    print(f"Generated: {stats['generated_at']}")
    print(f"Avg decision time: {stats['avg_decision_hours']}h "
          f"(min {stats['min_decision_hours']}h / max {stats['max_decision_hours']}h)\n")

    print(f"{'Flag Reason':<55} {'Total':>6} {'Approved':>9} {'Rejected':>9} {'Approval%':>10}  Recommendation")
    print("-" * 130)
    for t in stats["trigger_breakdown"]:
        print(
            f"{str(t['flag_reason'])[:55]:<55} "
            f"{t['total_flagged']:>6} "
            f"{t['approved']:>9} "
            f"{t['rejected']:>9} "
            f"{t['approval_rate_pct']:>9.1f}%  "
            f"{t['recommendation']}"
        )

    ia = stats["instant_approvals"]
    if ia:
        print(f"\nInstant approvals (<15 min) — {len(ia)} orders — potential auto-quote candidates:")
        for r in ia[:10]:
            amt = f"${float(r['estimate_amount']):,.0f}" if r.get("estimate_amount") else "TBD"
            print(f"  {r['order_id']}  {r.get('service_type','?'):<30}  {amt:<10}  {r.get('flag_reason','?')[:50]}")
        if len(ia) > 10:
            print(f"  ... +{len(ia)-10} more")


def write_csv(stats: dict, path: str) -> None:
    rows = stats["trigger_breakdown"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV written: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export flag trigger stats for calibration")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default 7)")
    parser.add_argument("--csv", metavar="PATH", help="Write trigger breakdown to CSV file")
    parser.add_argument("--json", metavar="PATH", help="Write full stats to JSON file")
    args = parser.parse_args()

    try:
        stats = get_flag_stats(days=args.days)
    except Exception as exc:
        print(f"ERROR: database query failed: {exc}")
        print("Ensure DATABASE_URL is set in .env and the DB is reachable.")
        sys.exit(1)

    print_report(stats)

    if args.csv:
        write_csv(stats, args.csv)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, default=str)
        print(f"JSON written: {args.json}")


if __name__ == "__main__":
    main()
