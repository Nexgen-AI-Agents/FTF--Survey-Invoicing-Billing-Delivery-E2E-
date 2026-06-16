"""Full pipeline reset — empty the approval sheet AND all pipeline state.

Use when you want the pipeline to start completely fresh from live FTF data,
posting ONLY orders that still carry the invoice-needed ($) flag.

What it clears:
  1. OneDrive "Approvals" table — every data row deleted (header/schema kept)
  2. data/invoice_pipeline_state.xlsx "pipeline_state" sheet — data rows wiped
     (learnings / pricing_examples / any other sheets are PRESERVED)
  3. data/pipeline_state.json — orders[] emptied (dashboard export)

What it PRESERVES:
  • Pricing Rules tab (user inputs)            • learned_rules.json (A7 learning)
  • Pipeline Guide / How-To tabs               • learnings sheet in the xlsx

Run from project root:
  python scripts/reset_all_state.py            # clear everything
  python scripts/reset_all_state.py --trigger  # clear, then dispatch the pipeline
"""

import argparse
import json
import os
import sys

import httpx
import openpyxl
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.onedrive_excel_client import (  # noqa: E402
    ONEDRIVE_SHEET_NAME,
    ONEDRIVE_TABLE_NAME,
    ensure_action_dropdown,
    _session_headers,
    _wb_base,
)

_REPO_ROOT     = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
XLSX_STATE     = os.path.join(_REPO_ROOT, "data", "invoice_pipeline_state.xlsx")
JSON_STATE     = os.path.join(_REPO_ROOT, "data", "pipeline_state.json")

GITHUB_PAT  = os.getenv("GITHUB_PAT", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Nexgen-AI-Agents/FTF--Survey-Invoicing-Billing-Delivery-E2E-")


# ── 1. OneDrive Approvals table ───────────────────────────────────────────────

def clear_onedrive_approvals() -> int:
    print("[1/3] Clearing OneDrive Approvals table...")
    base = _wb_base()
    h    = _session_headers()
    r = httpx.get(
        f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=h, timeout=30.0,
    )
    r.raise_for_status()
    rows = r.json().get("value", [])
    print(f"  {len(rows)} data rows found.")

    deleted = 0
    # Delete from the highest index down so earlier indices stay valid.
    for row in sorted(rows, key=lambda x: x.get("index", 0), reverse=True):
        idx = row.get("index")
        if idx is None:
            continue
        resp = httpx.delete(
            f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows/itemAt(index={idx})",
            headers=h, timeout=20.0,
        )
        if resp.is_success:
            deleted += 1
        else:
            print(f"  [!] failed to delete row index={idx}: {resp.status_code} {resp.text[:120]}")
    print(f"  Deleted {deleted}/{len(rows)} rows. Header + schema preserved.")
    # Row deletion strips the Action-column dropdown — re-apply it.
    ensure_action_dropdown()
    print("  Action dropdown (Approve/Reject/On-hold) re-applied.")
    return deleted


# ── 2. Authoritative xlsx state store ─────────────────────────────────────────

def clear_xlsx_state() -> int:
    print("[2/3] Clearing pipeline_state sheet in invoice_pipeline_state.xlsx...")
    if not os.path.exists(XLSX_STATE):
        print(f"  [!] {XLSX_STATE} not found — skipping.")
        return 0

    wb = openpyxl.load_workbook(XLSX_STATE)
    if "pipeline_state" not in wb.sheetnames:
        print("  [!] 'pipeline_state' sheet missing — skipping.")
        return 0

    ws = wb["pipeline_state"]
    data_rows = ws.max_row - 1  # exclude header
    if data_rows > 0:
        ws.delete_rows(2, ws.max_row - 1)  # keep row 1 (header)
    wb.save(XLSX_STATE)
    print(f"  Removed {max(data_rows, 0)} data rows. Header kept. "
          f"Preserved sheets: {[s for s in wb.sheetnames if s != 'pipeline_state']}")
    return max(data_rows, 0)


# ── 3. JSON dashboard export ──────────────────────────────────────────────────

def clear_json_state() -> int:
    print("[3/3] Emptying pipeline_state.json (dashboard export)...")
    if not os.path.exists(JSON_STATE):
        print(f"  [!] {JSON_STATE} not found — writing fresh empty file.")
        state = {}
    else:
        with open(JSON_STATE) as f:
            state = json.load(f)
    before = len(state.get("orders", []))
    state["orders"] = []
    with open(JSON_STATE, "w") as f:
        json.dump(state, f, indent=2, default=str)
    print(f"  orders[]: {before} -> 0")
    return before


def trigger_pipeline() -> None:
    print("\n[trigger] Dispatching invoice_pipeline workflow...")
    if not GITHUB_PAT:
        print("  [!] GITHUB_PAT not set — commit + dispatch manually.")
        return
    resp = httpx.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/invoice_pipeline.yml/dispatches",
        headers={
            "Authorization": f"Bearer {GITHUB_PAT}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"ref": "main"},
        timeout=15.0,
    )
    print("  HTTP 204 — triggered." if resp.status_code == 204
          else f"  [!] {resp.status_code}: {resp.text[:200]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full pipeline state reset")
    parser.add_argument("--trigger", action="store_true", help="dispatch pipeline after reset")
    args = parser.parse_args()

    print("\n=== FULL PIPELINE STATE RESET ===\n")
    try:
        clear_onedrive_approvals()
    except Exception as exc:
        print(f"  [!] OneDrive clear failed (continuing): {exc}")
    print()
    clear_xlsx_state()
    print()
    clear_json_state()

    if args.trigger:
        trigger_pipeline()

    print("\nDone. Commit data/ changes and the next run starts fresh from live FTF $-flagged orders.")
