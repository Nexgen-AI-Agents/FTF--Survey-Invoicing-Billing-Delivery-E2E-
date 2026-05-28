"""
send_daily_approval_reminder.py — Daily reminder for unanswered approval orders.

Runs every weekday morning (via GitHub Actions approval_reminder.yml).
Finds all orders still in awaiting_approval or flagged status from PREVIOUS day(s),
and re-posts them to the FTF-Approvals Teams channel with the original pending
timestamp so the team knows how long they've been waiting.

Keeps posting every day until a decision (APPROVE or REJECT) is made.

Usage:
    python scripts/send_daily_approval_reminder.py
    python scripts/send_daily_approval_reminder.py --dry-run
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from config.settings import FTF_ORDER_URL
from core.db import get_all_awaiting_orders, get_all_flagged_orders
from core.logger import get_logger
from core.teams_graph_client import send_channel_message

log = get_logger("send_daily_approval_reminder")


def _age_label(pending_since: datetime, now: datetime) -> str:
    delta = now - pending_since
    hours = int(delta.total_seconds() / 3600)
    if hours < 24:
        return f"{hours}h ago"
    days = delta.days
    return f"{days} day{'s' if days != 1 else ''} ago"


def run_reminder(dry_run: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=12)   # only remind about orders pending > 12h

    flagged  = get_all_flagged_orders()
    awaiting = get_all_awaiting_orders()
    all_pending = flagged + awaiting

    # Filter to orders pending longer than the cutoff
    leftover = []
    for row in all_pending:
        ts = row.get("flagged_at") or row.get("created_at")
        if ts:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts <= cutoff:
                leftover.append((row, ts))

    if not leftover:
        log.info("daily reminder: no leftover orders pending > 12h")
        return {"sent": 0, "orders": 0}

    # Sort oldest first
    leftover.sort(key=lambda x: x[1])

    now_str = now.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"&#9888; <strong>LEFTOVER ORDERS — Action Required</strong> &nbsp;|&nbsp; {now_str}",
        f"The following <strong>{len(leftover)} order(s)</strong> are still pending your decision:",
        "",
        "&#9472;" * 40,
        "",
    ]

    for row, ts in leftover:
        oid      = row["order_id"]
        svc      = row.get("service_type", "Unknown")
        amt      = row.get("estimate_amount")
        amt_str  = f"${float(amt):,.2f}" if amt else "TBD"
        reason   = (row.get("flag_reason") or "pending review")[:60]
        age      = _age_label(ts, now)
        url      = f"{FTF_ORDER_URL}/{oid}"
        date_str = ts.strftime("%Y-%m-%d %H:%M UTC")

        lines += [
            f"&nbsp;&nbsp;<strong>{oid}</strong> &nbsp;|&nbsp; {svc} &nbsp;|&nbsp; {amt_str}",
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Pending since : {date_str} ({age})",
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Reason &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {reason}",
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;FTF Link &nbsp;&nbsp;&nbsp;&nbsp;: <a href=\"{url}\">{url}</a>",
            "",
        ]

    lines += [
        "&#9472;" * 40,
        "",
        "<strong>Reply to this message with your decision:</strong>",
        "",
        "&nbsp;&nbsp;Approve one &nbsp;&nbsp;&nbsp;&nbsp;: <strong>APPROVE &lt;order-id&gt;</strong>",
        "&nbsp;&nbsp;Approve all &nbsp;&nbsp;&nbsp;&nbsp;: <strong>APPROVE ALL</strong>",
        "&nbsp;&nbsp;Reject one &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <strong>REJECT &lt;order-id&gt; &lt;reason&gt;</strong>",
        "&nbsp;&nbsp;Mixed &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <strong>APPROVE A, B &nbsp;REJECT C reason</strong>",
        "",
        "(Only Robert, Ryan, or Prateek can approve/reject)",
    ]

    msg = "<br>".join(lines)

    if dry_run:
        print(f"[DRY RUN] Would send reminder for {len(leftover)} order(s):")
        for row, ts in leftover:
            print(f"  {row['order_id']} (pending since {ts.strftime('%Y-%m-%d %H:%M')})")
        return {"sent": 0, "orders": len(leftover), "dry_run": True}

    send_channel_message(msg, subject=f"FTF Estimates — {len(leftover)} Leftover Order(s) Need Decision")
    log.info("daily reminder sent orders=%d", len(leftover))
    return {"sent": 1, "orders": len(leftover)}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Send daily approval reminder to Teams")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be sent without posting to Teams")
    args = parser.parse_args(argv)
    result = run_reminder(dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
