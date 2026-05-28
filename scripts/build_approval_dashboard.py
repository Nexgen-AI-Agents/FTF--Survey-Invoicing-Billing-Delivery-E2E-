"""
build_approval_dashboard.py — Generate a live approval queue + flag stats HTML dashboard.

Reads from the processed_orders and decision_log tables.
Outputs docs/approval_dashboard.html — open in any browser.

Usage:
    python scripts/build_approval_dashboard.py
    python scripts/build_approval_dashboard.py --output /path/to/output.html
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.db import _get_conn   # reuse existing connection helper
from core.logger import get_logger

log = get_logger("build_approval_dashboard")

_DEFAULT_OUT = Path(__file__).parent.parent / "docs" / "approval_dashboard.html"


def _query(sql: str, params=None) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def _get_queue_stats() -> dict:
    now = datetime.now(timezone.utc)

    # Current queue
    queue_rows = _query(
        "SELECT order_id, service_type, flag_reason, estimate_amount, status, flagged_at "
        "FROM processed_orders WHERE status IN ('awaiting_approval','flagged','priced','deferred') "
        "ORDER BY flagged_at ASC NULLS LAST"
    )

    # Age calculation
    queue = []
    for r in queue_rows:
        age_h = None
        if r.get("flagged_at"):
            try:
                fa = r["flagged_at"]
                if hasattr(fa, "replace"):
                    fa = fa.replace(tzinfo=timezone.utc) if fa.tzinfo is None else fa
                age_h = round((now - fa).total_seconds() / 3600, 1)
            except Exception:
                pass
        queue.append({**r, "age_hours": age_h})

    # Flag trigger breakdown (last 30 days)
    flag_stats = _query(
        "SELECT flag_reason, COUNT(*) AS cnt "
        "FROM processed_orders WHERE flag_reason IS NOT NULL "
        "AND flagged_at >= NOW() - INTERVAL '30 days' "
        "GROUP BY flag_reason ORDER BY cnt DESC LIMIT 15"
    )

    # Daily volume (last 14 days)
    daily = _query(
        "SELECT DATE(flagged_at) AS day, COUNT(*) AS cnt "
        "FROM processed_orders WHERE flagged_at >= NOW() - INTERVAL '14 days' "
        "GROUP BY day ORDER BY day"
    )

    # Decision summary (last 30 days)
    decisions = _query(
        "SELECT decision, COUNT(*) AS cnt FROM decision_log "
        "WHERE created_at >= NOW() - INTERVAL '30 days' "
        "GROUP BY decision ORDER BY cnt DESC"
    )

    # Approved vs rejected (last 30 days)
    approved_ct = sum(r["cnt"] for r in decisions if r["decision"] == "approved")
    rejected_ct = sum(r["cnt"] for r in decisions if r["decision"] == "rejected")

    # Avg queue time (approved orders)
    avg_rows = _query(
        "SELECT AVG(EXTRACT(EPOCH FROM (updated_at - flagged_at))/3600) AS avg_h "
        "FROM processed_orders WHERE status='approved' AND flagged_at IS NOT NULL "
        "AND updated_at IS NOT NULL AND updated_at >= NOW() - INTERVAL '30 days'"
    )
    avg_queue_h = round(avg_rows[0]["avg_h"] or 0, 1) if avg_rows else 0

    return {
        "queue": queue,
        "flag_stats": flag_stats,
        "daily": daily,
        "approved_ct": approved_ct,
        "rejected_ct": rejected_ct,
        "avg_queue_h": avg_queue_h,
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


def _build_html(stats: dict) -> str:
    queue      = stats["queue"]
    flag_stats = stats["flag_stats"]
    approved   = stats["approved_ct"]
    rejected   = stats["rejected_ct"]
    avg_h      = stats["avg_queue_h"]
    generated  = stats["generated_at"]

    # Queue table rows
    queue_rows_html = ""
    for r in queue:
        age   = r.get("age_hours")
        age_s = f"{age}h" if age is not None else "—"
        warn  = " style='color:#e74c3c;font-weight:bold'" if (age or 0) >= 4 else ""
        amt   = f"${float(r['estimate_amount']):,.2f}" if r.get("estimate_amount") else "TBD"
        queue_rows_html += (
            f"<tr>"
            f"<td>{r['order_id']}</td>"
            f"<td>{r.get('service_type') or '—'}</td>"
            f"<td>{amt}</td>"
            f"<td>{(r.get('flag_reason') or '—')[:70]}</td>"
            f"<td>{r.get('status','—')}</td>"
            f"<td{warn}>{age_s}</td>"
            f"</tr>"
        )
    if not queue_rows_html:
        queue_rows_html = "<tr><td colspan='6' style='text-align:center;color:#27ae60'>Queue is clear ✓</td></tr>"

    # Flag stats rows
    flag_rows_html = ""
    max_cnt = flag_stats[0]["cnt"] if flag_stats else 1
    for r in flag_stats:
        pct   = round(r["cnt"] / max_cnt * 100)
        bar   = f"<div style='background:#3498db;height:12px;width:{pct}%;display:inline-block'></div>"
        flag_rows_html += f"<tr><td>{r['flag_reason'][:60]}</td><td>{r['cnt']}</td><td>{bar}</td></tr>"

    overdue_count = sum(1 for r in queue if (r.get("age_hours") or 0) >= 4)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="300">
<title>FTF Approval Dashboard</title>
<style>
  body{{font-family:Arial,sans-serif;background:#f4f6f9;margin:0;padding:20px;color:#2c3e50}}
  h1{{color:#2c3e50;margin-bottom:4px}}
  .meta{{color:#7f8c8d;font-size:13px;margin-bottom:24px}}
  .kpi-row{{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}}
  .kpi{{background:#fff;border-radius:8px;padding:20px 28px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:140px}}
  .kpi-val{{font-size:32px;font-weight:bold;color:#2c3e50}}
  .kpi-lbl{{font-size:12px;color:#7f8c8d;margin-top:4px}}
  .kpi.warn .kpi-val{{color:#e74c3c}}
  .kpi.green .kpi-val{{color:#27ae60}}
  .section{{background:#fff;border-radius:8px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:20px}}
  h2{{margin:0 0 14px;font-size:16px;color:#34495e}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{background:#ecf0f1;text-align:left;padding:8px 10px;font-weight:600}}
  td{{padding:7px 10px;border-bottom:1px solid #ecf0f1}}
  tr:last-child td{{border-bottom:none}}
</style>
</head>
<body>
<h1>FTF Approval Queue — Live Dashboard</h1>
<div class="meta">Auto-refreshes every 5 min &nbsp;|&nbsp; Generated: {generated}</div>

<div class="kpi-row">
  <div class="kpi {'warn' if len(queue) > 0 else 'green'}">
    <div class="kpi-val">{len(queue)}</div>
    <div class="kpi-lbl">Orders in Queue</div>
  </div>
  <div class="kpi {'warn' if overdue_count > 0 else 'green'}">
    <div class="kpi-val">{overdue_count}</div>
    <div class="kpi-lbl">Overdue (&ge;4h)</div>
  </div>
  <div class="kpi green">
    <div class="kpi-val">{approved}</div>
    <div class="kpi-lbl">Approved (30d)</div>
  </div>
  <div class="kpi">
    <div class="kpi-val">{rejected}</div>
    <div class="kpi-lbl">Rejected (30d)</div>
  </div>
  <div class="kpi">
    <div class="kpi-val">{avg_h}h</div>
    <div class="kpi-lbl">Avg Queue Time</div>
  </div>
</div>

<div class="section">
  <h2>Current Queue</h2>
  <table>
    <tr><th>Order ID</th><th>Service</th><th>Amount</th><th>Flag Reason</th><th>Status</th><th>Age</th></tr>
    {queue_rows_html}
  </table>
</div>

<div class="section">
  <h2>Top Flag Triggers (last 30 days)</h2>
  <table>
    <tr><th>Flag Reason</th><th>Count</th><th>Frequency</th></tr>
    {flag_rows_html if flag_rows_html else '<tr><td colspan="3" style="color:#7f8c8d">No flag data yet</td></tr>'}
  </table>
</div>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate FTF approval dashboard HTML")
    parser.add_argument("--output", default=str(_DEFAULT_OUT), help="Output HTML path")
    args = parser.parse_args()

    print("Querying database...")
    try:
        stats = _get_queue_stats()
    except Exception as exc:
        print(f"ERROR: could not read from database: {exc}")
        print("Make sure DATABASE_URL is set in .env and the DB is reachable.")
        sys.exit(1)

    html = _build_html(stats)
    out  = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    q = len(stats["queue"])
    print(f"Dashboard written: {out}")
    print(f"  Queue depth  : {q} order(s)")
    print(f"  Approved 30d : {stats['approved_ct']}")
    print(f"  Avg queue    : {stats['avg_queue_h']}h")


if __name__ == "__main__":
    main()
