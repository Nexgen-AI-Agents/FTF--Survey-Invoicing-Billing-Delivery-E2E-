#!/usr/bin/env python3
"""
Sprint 11 — First-5 Estimate Monitor
Run from project root: python scripts/monitor_first5_estimates.py

Queries processed_orders for the first 5 sent production estimates.
Prints a detailed review report for Prateek / Robert / Mark.

Flags Sprint 11 as review-ready once 5 estimates are confirmed sent.
Optionally posts a Teams card to notify reviewers.

Usage:
  python scripts/monitor_first5_estimates.py            # console report
  python scripts/monitor_first5_estimates.py --teams    # console + Teams card
"""

import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import psycopg2.extras
import httpx

from config.settings import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    FTF_API_BASE_URL, TEAMS_WEBHOOK_URL,
)

REVIEW_LIMIT = 5
_FTF_PORTAL = FTF_API_BASE_URL.replace("/ftf-ai-api/v1", "")


def _connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def get_sent_estimates(limit: int = REVIEW_LIMIT) -> tuple[list[dict], int]:
    """Return (first-N-sent-estimates, total-sent-count)."""
    conn = _connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT order_id, service_type, customer_email, estimate_amount,
                           is_flood_zone, flag_reason, draft_estimate,
                           created_at, sent_at
                    FROM processed_orders
                    WHERE status = 'sent'
                    ORDER BY sent_at ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = [dict(r) for r in cur.fetchall()]

                cur.execute("SELECT COUNT(*) AS n FROM processed_orders WHERE status = 'sent'")
                total = cur.fetchone()["n"]
    finally:
        conn.close()
    return rows, int(total)


def get_pipeline_snapshot() -> dict[str, int]:
    """Count orders in each non-sent, non-error status for a pipeline health view."""
    conn = _connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status, COUNT(*) FROM processed_orders
                    WHERE status NOT IN ('sent', 'error')
                    GROUP BY status ORDER BY status
                    """
                )
                return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        conn.close()


def _fmt_sent_at(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M UTC")
    return str(value) if value else "—"


def _fmt_estimate(idx: int, est: dict) -> str:
    flood = "YES (upcharge applies)" if est.get("is_flood_zone") else "No"
    amount = float(est.get("estimate_amount") or 0)
    draft = est.get("draft_estimate") or ""
    preview = (draft[:400] + " [...]") if len(draft) > 400 else draft
    preview_indented = "\n    ".join(preview.splitlines()) if preview else "(no draft stored)"

    lines = [
        f"  {'─' * 58}",
        f"  #{idx + 1}  Order ID  : {est['order_id']}",
        f"       Service   : {est.get('service_type') or '—'}",
        f"       Customer  : {est.get('customer_email') or '—'}",
        f"       Amount    : ${amount:,.2f}",
        f"       Flood Zone: {flood}",
        f"       Sent At   : {_fmt_sent_at(est.get('sent_at'))}",
        f"       FTF Link  : {_FTF_PORTAL}/orders/{est['order_id']}",
    ]
    if est.get("flag_reason"):
        lines.append(f"       ⚠ Flag    : {est['flag_reason']}")
    lines += [
        f"\n  ESTIMATE DRAFT SENT TO CUSTOMER:",
        f"  ┌{'─' * 56}",
        f"  │ {preview_indented}",
        f"  └{'─' * 56}",
    ]
    return "\n".join(lines)


def post_teams_review_card(estimates: list[dict], total_sent: int) -> bool:
    if not TEAMS_WEBHOOK_URL:
        print("  [Teams] TEAMS_WEBHOOK_URL not set — skipping.")
        return False

    facts = [
        {
            "name": f"#{i + 1}  {est['order_id']}",
            "value": (
                f"{est.get('service_type', '?')} | "
                f"${float(est.get('estimate_amount') or 0):,.2f} | "
                f"{est.get('customer_email', '?')}"
            ),
        }
        for i, est in enumerate(estimates)
    ]

    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "0078D4",
        "summary": "Sprint 11 — First 5 Estimates Ready for Review",
        "sections": [
            {
                "activityTitle": "Sprint 11: First Real Estimates Need Your Review",
                "activitySubtitle": (
                    f"{total_sent} estimate(s) sent to real customers. "
                    "Please review the first 5 for accuracy, tone, and professionalism. "
                    "Reply with any issues within 24 hours."
                ),
                "facts": facts,
                "markdown": True,
            }
        ],
    }

    try:
        r = httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=10.0)
        r.raise_for_status()
        return True
    except Exception as exc:
        print(f"  [Teams] Post failed: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sprint 11 — monitor first 5 real estimates for Robert/Mark review"
    )
    parser.add_argument(
        "--teams", action="store_true",
        help="Post a Teams review card to notify Robert/Mark",
    )
    args = parser.parse_args()

    print()
    print("=" * 64)
    print("  Sprint 11 — First-5 Estimate Monitor")
    print("  NexGen Surveying — Production Estimate Review")
    print("=" * 64)
    print()

    try:
        estimates, total_sent = get_sent_estimates(REVIEW_LIMIT)
    except Exception as exc:
        print(f"  ERROR querying database: {exc}")
        sys.exit(1)

    try:
        pipeline = get_pipeline_snapshot()
    except Exception:
        pipeline = {}

    print(f"  Total estimates sent to real customers : {total_sent}")
    if pipeline:
        pipe_str = "  |  ".join(f"{k}: {v}" for k, v in sorted(pipeline.items()))
        print(f"  Orders still in pipeline              : {pipe_str or 'none'}")
    print()

    if not estimates:
        print("  No estimates sent yet.")
        print("  The estimate loop runs every 60 min via GitHub Actions (estimate_generation.yml).")
        print()
        sys.exit(0)

    sprint11_ready = total_sent >= REVIEW_LIMIT
    status_label = (
        f"READY FOR REVIEW ({total_sent} sent)"
        if sprint11_ready
        else f"IN PROGRESS — {total_sent}/{REVIEW_LIMIT} sent"
    )
    print(f"  Sprint 11 review status: {status_label}")
    print()

    for i, est in enumerate(estimates):
        print(_fmt_estimate(i, est))
        print()

    if args.teams:
        print("  Posting Teams review card...")
        ok = post_teams_review_card(estimates, total_sent)
        print(f"  Teams notification: {'sent' if ok else 'failed'}")
        print()

    print("─" * 64)
    if sprint11_ready:
        print(f"  All {REVIEW_LIMIT} estimates sent. Robert/Mark review required.")
        if not args.teams:
            print("  Run with --teams to send a Teams review card to Robert/Mark.")
    else:
        remaining = REVIEW_LIMIT - total_sent
        print(f"  {remaining} more estimate(s) needed before Sprint 11 review gate.")
    print()


if __name__ == "__main__":
    main()
