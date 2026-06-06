"""cleanup_stale_excel_rows.py — Mark all unprocessed duplicate rows as processed.

For orders that already have at least one processed row (Processed At filled),
any other rows for the same order that still have Action set but Processed At blank
are stale — mark them processed now to prevent the watcher from re-processing them.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import httpx
import base64

from config.settings import (
    AZURE_APP_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID,
    ONEDRIVE_SHARE_URL, ONEDRIVE_SHEET_NAME, ONEDRIVE_TABLE_NAME,
)
from core.logger import get_logger

log = get_logger("cleanup_stale_excel_rows")

_GRAPH = "https://graph.microsoft.com/v1.0"
_COL_ACTION       = 9
_COL_PROCESSED_AT = 12
_COL_COUNT        = 13


def _get_token() -> str:
    r = httpx.post(
        f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
        data={"grant_type": "client_credentials", "client_id": AZURE_APP_ID,
              "client_secret": AZURE_CLIENT_SECRET,
              "scope": "https://graph.microsoft.com/.default"}, timeout=15.0)
    r.raise_for_status()
    return r.json()["access_token"]


def _get_item_id(token):
    encoded = base64.urlsafe_b64encode(ONEDRIVE_SHARE_URL.encode()).decode().rstrip("=")
    r = httpx.get(f"{_GRAPH}/shares/u!{encoded}/driveItem",
                  headers={"Authorization": f"Bearer {token}"}, timeout=15.0)
    r.raise_for_status()
    item = r.json()
    return item["id"], item["parentReference"]["driveId"]


def main():
    token = _get_token()
    item_id, drive_id = _get_item_id(token)
    wb_base = f"{_GRAPH}/drives/{drive_id}/items/{item_id}/workbook"
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    r = httpx.get(
        f"{wb_base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=h, timeout=20.0)
    r.raise_for_status()
    rows = r.json().get("value", [])

    # Build per-order: which rows have Processed At already set
    processed_orders: set[str] = set()
    for row in rows:
        vals = row.get("values", [[]])[0]
        if not vals:
            continue
        oid = str(vals[0]).strip()
        processed_at = str(vals[_COL_PROCESSED_AT]).strip() if len(vals) > _COL_PROCESSED_AT else ""
        if oid and processed_at:
            processed_orders.add(oid)

    log.info("%d orders already have a processed row", len(processed_orders))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cleaned = 0

    for row in rows:
        vals = row.get("values", [[]])[0]
        if not vals:
            continue
        oid = str(vals[0]).strip()
        action       = str(vals[_COL_ACTION]).strip() if len(vals) > _COL_ACTION else ""
        processed_at = str(vals[_COL_PROCESSED_AT]).strip() if len(vals) > _COL_PROCESSED_AT else ""

        # Stale: order already processed elsewhere + this row has Action set but no Processed At
        if oid in processed_orders and action and not processed_at:
            new_vals = list(vals) + [""] * (_COL_COUNT - len(vals))
            new_vals[_COL_PROCESSED_AT] = f"cleaned-{now}"
            idx = row["index"]
            httpx.patch(
                f"{wb_base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows/itemAt(index={idx})",
                headers=h, json={"values": [new_vals[:_COL_COUNT]]}, timeout=15.0,
            ).raise_for_status()
            log.info("cleaned stale row order=%s index=%d action=%s", oid, idx, action)
            cleaned += 1

    print(f"Done — cleaned {cleaned} stale rows")


if __name__ == "__main__":
    main()
