"""
update_build_timeline.py — refreshes the LIVE PIPELINE STATS section of build_timeline.txt.

Reads data/pipeline_state.json, counts orders by status, and patches the stats
table in-place. Safe to run multiple times — idempotent.

Called automatically from the GitHub Actions pipeline commit step after every run.
Can also be run locally:
    python scripts/update_build_timeline.py
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta

REPO_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE     = os.path.join(REPO_ROOT, "data", "pipeline_state.json")
TIMELINE_FILE  = os.path.join(REPO_ROOT, "build_timeline.txt")

ET = timezone(timedelta(hours=-4))

STATUS_DISPLAY = [
    ("invoice_draft_posted",   "invoice_draft_posted       "),
    ("pricing_needed",         "pricing_needed              "),
    ("condo_rejected",         "condo_rejected              "),
    ("invoice_sent",           "invoice_sent                "),
    ("invoice_rejected",       "invoice_rejected            "),
    ("on_hold",                "on_hold                     "),
    ("details_missing",        "details_missing             "),
    ("permanently_excluded",   "permanently_excluded        "),
]


def load_state() -> dict:
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def count_by_status(orders: list) -> dict:
    counts: dict[str, int] = {}
    for o in orders:
        s = o.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts


def build_stats_block(counts: dict, total: int, today: str, env: str) -> str:
    rows = ""
    for key, label in STATUS_DISPLAY:
        n = counts.get(key, 0)
        if n > 0:
            rows += f"  │ {label}│ {n:>6}  │\n"

    # any unexpected statuses
    known = {k for k, _ in STATUS_DISPLAY}
    for key, n in sorted(counts.items()):
        if key not in known and n > 0:
            label = f"{key:<29}"
            rows += f"  │ {label}│ {n:>6}  │\n"

    sent      = counts.get("invoice_sent", 0)
    posted    = counts.get("invoice_draft_posted", 0)
    pricing   = counts.get("pricing_needed", 0)
    condo     = counts.get("condo_rejected", 0)

    block = (
        f"================================================================================\n"
        f"LIVE PIPELINE STATS                               (updated by pipeline each run)\n"
        f"================================================================================\n"
        f"\n"
        f"  Last pipeline run   : {today}\n"
        f"  Environment         : Stage ({env})\n"
        f"  Total orders tracked: {total}\n"
        f"\n"
        f"  ┌─────────────────────────────┬────────┐\n"
        f"  │ Status                      │ Count  │\n"
        f"  ├─────────────────────────────┼────────┤\n"
        f"{rows}"
        f"  ├─────────────────────────────┼────────┤\n"
        f"  │ TOTAL TRACKED               │ {total:>6}  │\n"
        f"  └─────────────────────────────┴────────┘\n"
        f"\n"
        f"  Invoices sent to customers    : {sent:>5}\n"
        f"  Awaiting human approval       : {posted:>5}\n"
        f"  Needs manual pricing          : {pricing:>5}\n"
        f"  Condos (auto-rejected)        : {condo:>5}\n"
    )
    return block


def patch_timeline(new_block: str) -> None:
    with open(TIMELINE_FILE, encoding="utf-8") as f:
        content = f.read()

    start_marker = "================================================================================\nLIVE PIPELINE STATS"
    end_marker   = "================================================================================\nCUMULATIVE BUILD STATS"

    start = content.find(start_marker)
    end   = content.find(end_marker)

    if start == -1 or end == -1:
        print("[update_build_timeline] Markers not found — skipping patch.")
        return

    updated = content[:start] + new_block + "\n" + content[end:]
    with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"[update_build_timeline] Stats section updated.")


def patch_last_activity(today: str) -> None:
    with open(TIMELINE_FILE, encoding="utf-8") as f:
        content = f.read()

    updated = re.sub(
        r"(  Last activity\s+: )\d{4}-\d{2}-\d{2}[^\n]*",
        rf"\g<1>{today}        ← auto-updated each session",
        content,
    )
    with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
        f.write(updated)


def main() -> None:
    state    = load_state()
    orders   = state.get("orders", [])
    counts   = count_by_status(orders)
    total    = len(orders)
    today    = datetime.now(ET).strftime("%Y-%m-%d")
    env_name = "stage.fieldtofinish.jobs"

    block = build_stats_block(counts, total, today, env_name)
    patch_timeline(block)
    patch_last_activity(today)
    print(f"[update_build_timeline] Done. {total} orders, last run {today}.")


if __name__ == "__main__":
    main()
