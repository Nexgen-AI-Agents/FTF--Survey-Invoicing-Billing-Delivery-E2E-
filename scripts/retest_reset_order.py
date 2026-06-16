"""One-off script: reset order 1000284017 for retest of per-service breakdown feature.

Steps:
  1. Delete the existing Excel row (so A3 dedup check passes)
  2. Reset pipeline_state.json: status=data_collected, clear invoice_draft + draft_posted_at
  3. Trigger GitHub Actions invoice_pipeline workflow_dispatch

Run from project root:
  python scripts/retest_reset_order.py
"""

import json
import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

ORDER_ID = "1000284017"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.onedrive_excel_client import (
    ONEDRIVE_SHEET_NAME,
    ONEDRIVE_TABLE_NAME,
    _session_headers,
    _wb_base,
)

PIPELINE_STATE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "pipeline_state.json")
)

GITHUB_PAT  = os.getenv("GITHUB_PAT", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "Nexgen-AI-Agents/FTF--Survey-Invoicing-Billing-Delivery-E2E-")


# ── Step 1: Delete the Excel row ─────────────────────────────────────────────

def clear_excel_row_id(order_id: str) -> int:
    """Blank out col A (Order ID) of the existing row so A3's dedup check won't block the retest.
    Returns the excel row number (1-based) that was cleared.
    """
    print(f"[1/3] Finding Excel row for order {order_id}...")
    r = httpx.get(
        f"{_wb_base()}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=_session_headers(),
        timeout=20.0,
    )
    r.raise_for_status()
    rows = r.json().get("value", [])

    target_index = None
    for row in rows:
        vals = row.get("values", [[]])[0]
        if vals and str(vals[0]).strip() == str(order_id):
            target_index = row.get("index")
            break

    if target_index is None:
        print(f"  [!] Row not found in Excel — may have already been removed.")
        return -1

    # 0-based table index + 1 header row + 1 for 1-based = index + 2
    excel_row = target_index + 2
    print(f"  Found at table index {target_index} (Excel row {excel_row}). Clearing Order ID cell...")

    patch_r = httpx.patch(
        f"{_wb_base()}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='A{excel_row}')",
        headers=_session_headers(),
        json={"values": [["RETEST_OLD"]]},
        timeout=15.0,
    )
    patch_r.raise_for_status()
    print(f"  Col A overwritten with 'RETEST_OLD' — dedup guard bypassed.")
    return excel_row


# ── Step 2: Reset pipeline_state.json ────────────────────────────────────────

def reset_pipeline_state(order_id: str) -> dict:
    print(f"[2/3] Resetting pipeline state for order {order_id}...")
    with open(PIPELINE_STATE) as f:
        state = json.load(f)

    order = None
    for o in state["orders"]:
        if o["order_id"] == order_id:
            order = o
            break

    if not order:
        raise ValueError(f"Order {order_id} not found in pipeline_state.json")

    before = {
        "status":          order["status"],
        "invoice_draft":   bool(order.get("invoice_draft")),
        "draft_posted_at": order.get("draft_posted_at"),
    }

    order["status"]          = "data_collected"
    order["invoice_draft"]   = None
    order["draft_posted_at"] = None
    order["invoice_id"]      = None

    with open(PIPELINE_STATE, "w") as f:
        json.dump(state, f, indent=2, default=str)

    print(f"  Status: {before['status']} -> data_collected")
    print(f"  invoice_draft cleared: {before['invoice_draft']} -> None")
    print(f"  draft_posted_at cleared: {before['draft_posted_at']} -> None")
    return before


# ── Step 3: Trigger GitHub Actions workflow_dispatch ─────────────────────────

def trigger_pipeline() -> None:
    print(f"[3/3] Triggering invoice_pipeline workflow on GitHub Actions...")
    if not GITHUB_PAT:
        print("  [!] GITHUB_PAT not set — cannot trigger workflow. Push state and run manually.")
        return

    resp = httpx.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/invoice_pipeline.yml/dispatches",
        headers={
            "Authorization": f"Bearer {GITHUB_PAT}",
            "Accept":        "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"ref": "main"},
        timeout=15.0,
    )
    if resp.status_code == 204:
        print("  Workflow triggered successfully (HTTP 204).")
    else:
        print(f"  [!] Unexpected response: {resp.status_code} — {resp.text[:200]}")


if __name__ == "__main__":
    print(f"\n=== Retest reset: order {ORDER_ID} ===\n")

    clear_excel_row_id(ORDER_ID)
    print()

    before = reset_pipeline_state(ORDER_ID)
    print()

    trigger_pipeline()

    print(f"\nDone. Order {ORDER_ID} is now at status=data_collected.")
    print("Pipeline triggered — A3 will re-process it and write the new breakdown format to Excel.")
    print("\nExpected new col E value:")
    print('  "Land Survey (Negotiated Rate): $500.00 | Waterfront / Canal Complexity Upcharge: $87.00 | Pool Upcharge: $62.00 | Lot Size Upcharge (0.51-1.00 ac): $137.00"')
