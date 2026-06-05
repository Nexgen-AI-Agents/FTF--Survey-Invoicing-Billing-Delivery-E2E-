"""set_excel_actions.py — One-shot script to set Action values in FTF-Invoicing Agent.xlsx.

Usage:
  python set_excel_actions.py --actions "1000283728:approve,1000283564:approve,..."

Runs via GitHub Actions (needs AZURE_* and ONEDRIVE_* env vars).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import httpx

from config.settings import (
    AZURE_APP_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID,
    ONEDRIVE_FILE_USER, ONEDRIVE_SHARE_URL,
    ONEDRIVE_SHEET_NAME, ONEDRIVE_TABLE_NAME,
)
from core.logger import get_logger

log = get_logger("set_excel_actions")

_GRAPH     = "https://graph.microsoft.com/v1.0"
_TOKEN_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
_COL_ACTION = 9   # column J (0-indexed)
_COL_COUNT  = 13


def _get_token() -> str:
    r = httpx.post(_TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": AZURE_APP_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }, timeout=15.0)
    r.raise_for_status()
    return r.json()["access_token"]


def _get_item_id(token: str) -> tuple[str, str]:
    import base64
    share_url = ONEDRIVE_SHARE_URL
    encoded = base64.urlsafe_b64encode(share_url.encode()).decode().rstrip("=")
    share_id = f"u!{encoded}"
    r = httpx.get(f"{_GRAPH}/shares/{share_id}/driveItem",
                  headers={"Authorization": f"Bearer {token}"}, timeout=15.0)
    r.raise_for_status()
    item = r.json()
    return item["id"], item["parentReference"]["driveId"]


def set_actions(actions: dict[str, str]) -> None:
    """actions: {order_id: "Approve"|"Reject"|"On-hold"}"""
    token = _get_token()
    item_id, drive_id = _get_item_id(token)
    wb_base = f"{_GRAPH}/drives/{drive_id}/items/{item_id}/workbook"
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    r = httpx.get(
        f"{wb_base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=h, timeout=20.0,
    )
    r.raise_for_status()
    rows = r.json().get("value", [])

    updated = 0
    for row in rows:
        vals = row.get("values", [[]])[0]
        if not vals:
            continue
        order_id = str(vals[0]).strip()
        if order_id not in actions:
            continue

        action_val = actions[order_id]
        current_action = str(vals[_COL_ACTION]).strip() if len(vals) > _COL_ACTION else ""
        processed_at   = str(vals[12]).strip() if len(vals) > 12 else ""

        if processed_at:
            log.info("order=%s already processed — skipping", order_id)
            continue
        if current_action == action_val:
            log.info("order=%s already has Action=%s — skipping", order_id, action_val)
            continue

        new_vals = list(vals) + [""] * (_COL_COUNT - len(vals))
        new_vals[_COL_ACTION] = action_val

        idx = row["index"]
        patch_r = httpx.patch(
            f"{wb_base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows/itemAt(index={idx})",
            headers=h,
            json={"values": [new_vals[:_COL_COUNT]]},
            timeout=15.0,
        )
        patch_r.raise_for_status()
        log.info("set Action=%s for order=%s (row index %d)", action_val, order_id, idx)
        updated += 1

    not_found = set(actions) - {str(row.get("values", [[]])[0][0]).strip() for row in rows if row.get("values", [[]])[0]}
    if not_found:
        log.warning("orders not found in Excel: %s", not_found)

    print(f"Done — updated {updated} rows, not found: {not_found or 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actions", required=True,
                        help="Comma-separated order:action pairs, e.g. 1000283728:Approve,1000282430:Reject")
    args = parser.parse_args()

    actions = {}
    for item in args.actions.split(","):
        item = item.strip()
        if ":" not in item:
            continue
        oid, act = item.split(":", 1)
        actions[oid.strip()] = act.strip()

    log.info("setting actions: %s", actions)
    set_actions(actions)


if __name__ == "__main__":
    main()
