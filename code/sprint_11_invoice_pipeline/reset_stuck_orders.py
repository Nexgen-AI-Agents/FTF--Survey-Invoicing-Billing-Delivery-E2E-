"""reset_stuck_orders.py

Resets orders that are marked invoice_draft_posted in the pipeline state
but are NOT present in the OneDrive approval Excel sheet.

These are orders from the old MS Teams approval flow that were never
re-posted to the new Excel-based flow.  Resetting them to data_collected
allows A3 to pick them up on the next run and post them to Excel.

Run once from the repo root after deploying the A3 dedup/bug fixes:
    cd code/sprint_11_invoice_pipeline
    python reset_stuck_orders.py
"""

import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import httpx

from config.settings import (
    AZURE_APP_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID,
    ONEDRIVE_SHARE_URL, ONEDRIVE_SHEET_NAME, ONEDRIVE_TABLE_NAME,
)
from core.excel_db import get_orders_by_status, save_order_state
from core.logger import get_logger

log = get_logger("reset_stuck_orders")

_GRAPH = "https://graph.microsoft.com/v1.0"


def _get_token() -> str:
    r = httpx.post(
        f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": AZURE_APP_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=15.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _get_excel_order_ids(token: str) -> set:
    encoded = base64.urlsafe_b64encode(ONEDRIVE_SHARE_URL.encode()).decode().rstrip("=")
    share_id = f"u!{encoded}"
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    item = httpx.get(f"{_GRAPH}/shares/{share_id}/driveItem", headers=h, timeout=15.0)
    item.raise_for_status()
    drive_id = item.json()["parentReference"]["driveId"]
    item_id  = item.json()["id"]
    wb_base  = f"{_GRAPH}/drives/{drive_id}/items/{item_id}/workbook"

    ids = set()
    url = f"{wb_base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows"
    while url:
        resp = httpx.get(url, headers=h, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        for row in data.get("value", []):
            vals = row.get("values", [[]])[0]
            if vals:
                ids.add(str(vals[0]).strip())
        url = data.get("@odata.nextLink")

    return ids


def main():
    print("Fetching Excel order IDs...")
    token = _get_token()
    excel_ids = _get_excel_order_ids(token)
    print(f"  {len(excel_ids)} orders currently in Excel")

    stuck = get_orders_by_status("invoice_draft_posted")
    to_reset = [o for o in stuck if str(o["order_id"]) not in excel_ids]

    print(f"  {len(stuck)} orders in invoice_draft_posted status")
    print(f"  {len(to_reset)} are NOT in Excel (stuck from old Teams flow) — resetting to data_collected")

    if not to_reset:
        print("Nothing to reset.")
        return

    for i, order in enumerate(to_reset, 1):
        save_order_state(order["order_id"], status="data_collected")
        if i % 50 == 0:
            print(f"  Reset {i}/{len(to_reset)}...")

    print(f"Done. {len(to_reset)} orders reset to data_collected.")
    print("They will be picked up by A3 on the next pipeline run.")


if __name__ == "__main__":
    main()
