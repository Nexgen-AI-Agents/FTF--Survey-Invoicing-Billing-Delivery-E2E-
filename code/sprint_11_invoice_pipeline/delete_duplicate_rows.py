"""delete_duplicate_rows.py — Delete rows marked 'cleaned-*' in Processed At (orphan duplicates)."""
import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import httpx
from config.settings import (
    AZURE_APP_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID,
    ONEDRIVE_SHARE_URL, ONEDRIVE_SHEET_NAME, ONEDRIVE_TABLE_NAME,
)

_GRAPH = "https://graph.microsoft.com/v1.0"
_COL_PROCESSED_AT = 12


def get_token():
    r = httpx.post(
        f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
        data={"grant_type": "client_credentials", "client_id": AZURE_APP_ID,
              "client_secret": AZURE_CLIENT_SECRET,
              "scope": "https://graph.microsoft.com/.default"}, timeout=15.0)
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    token = get_token()
    encoded = base64.urlsafe_b64encode(ONEDRIVE_SHARE_URL.encode()).decode().rstrip("=")
    r = httpx.get(f"{_GRAPH}/shares/u!{encoded}/driveItem",
                  headers={"Authorization": f"Bearer {token}"}, timeout=15.0)
    r.raise_for_status()
    item = r.json()
    item_id = item["id"]
    drive_id = item["parentReference"]["driveId"]
    wb = f"{_GRAPH}/drives/{drive_id}/items/{item_id}/workbook"
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    rows_r = httpx.get(
        f"{wb}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=h, timeout=20.0)
    rows_r.raise_for_status()
    rows = rows_r.json().get("value", [])

    to_delete = []
    for row in rows:
        vals = row.get("values", [[]])[0]
        if not vals:
            continue
        processed = str(vals[_COL_PROCESSED_AT]).strip() if len(vals) > _COL_PROCESSED_AT else ""
        if processed.startswith("cleaned-"):
            to_delete.append((row["index"], str(vals[0])))

    print(f"Found {len(to_delete)} duplicate rows to delete: {[o for _, o in to_delete]}")

    # Delete highest index first so indices stay valid
    for idx, oid in sorted(to_delete, reverse=True):
        d = httpx.delete(
            f"{wb}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows/itemAt(index={idx})",
            headers=h, timeout=15.0)
        d.raise_for_status()
        print(f"Deleted row index={idx} order={oid}")

    print(f"Done — deleted {len(to_delete)} rows")


if __name__ == "__main__":
    main()
