"""fix_unknown_rows.py — Patch Excel rows that have 'Unknown' in Client Name or Property Address.

For each row with 'Unknown', finds another row with the same order_id that has real data
and copies those values. Falls back to pipeline_state.json if no good row exists.

Run locally — only needs Graph API (no MySQL).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import httpx
import base64

from config.settings import (
    AZURE_APP_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID,
    ONEDRIVE_FILE_USER, ONEDRIVE_SHARE_URL,
    ONEDRIVE_SHEET_NAME, ONEDRIVE_TABLE_NAME,
)
from core.logger import get_logger

log = get_logger("fix_unknown_rows")

_GRAPH = "https://graph.microsoft.com/v1.0"
_COL_COUNT = 13

_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pipeline_state.json")


def _get_token() -> str:
    r = httpx.post(
        f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": AZURE_APP_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
        }, timeout=15.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _get_item_id(token: str) -> tuple[str, str]:
    encoded = base64.urlsafe_b64encode(ONEDRIVE_SHARE_URL.encode()).decode().rstrip("=")
    r = httpx.get(f"{_GRAPH}/shares/u!{encoded}/driveItem",
                  headers={"Authorization": f"Bearer {token}"}, timeout=15.0)
    r.raise_for_status()
    item = r.json()
    return item["id"], item["parentReference"]["driveId"]


def main() -> None:
    # Load pipeline state for fallback data
    state: dict = {}
    try:
        with open(_STATE_FILE) as f:
            raw = json.load(f)
        for entry in raw.get("orders", raw) if isinstance(raw, dict) else raw:
            if isinstance(entry, dict) and entry.get("order_id"):
                state[str(entry["order_id"])] = entry
        log.info("loaded %d orders from pipeline_state.json", len(state))
    except Exception as exc:
        log.warning("could not load pipeline_state.json: %s", exc)

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

    # Build a map: order_id → list of (index, vals) sorted by best data quality
    order_rows: dict[str, list] = {}
    for row in rows:
        vals = row.get("values", [[]])[0]
        if not vals:
            continue
        oid = str(vals[0]).strip()
        if oid:
            order_rows.setdefault(oid, []).append((row["index"], vals))

    patched = 0
    for row in rows:
        vals = row.get("values", [[]])[0]
        if not vals:
            continue
        oid = str(vals[0]).strip()

        client_name  = str(vals[2]).strip() if len(vals) > 2 else ""
        address      = str(vals[3]).strip() if len(vals) > 3 else ""

        # Only patch rows where BOTH fields are Unknown (old A3 output)
        if client_name.lower() != "unknown" and address.lower() != "unknown":
            continue

        log.info("found Unknown row: order=%s index=%d client=%r address=%r",
                 oid, row["index"], client_name, address)

        # Look for a sibling row with real data
        real_client = ""
        real_address = ""
        for idx, sib_vals in order_rows.get(oid, []):
            if idx == row["index"]:
                continue
            sc = str(sib_vals[2]).strip() if len(sib_vals) > 2 else ""
            sa = str(sib_vals[3]).strip() if len(sib_vals) > 3 else ""
            if sc.lower() not in ("unknown", "") and sa.lower() not in ("unknown", ""):
                real_client  = sc
                real_address = sa
                log.info("  found sibling row (index=%d): client=%r address=%r", idx, sc, sa)
                break

        # Fallback: pipeline state
        if not real_client or not real_address:
            ps = state.get(oid, {})
            if not real_address:
                real_address = ps.get("property_address", "") or address
            if not real_client:
                real_client = ps.get("client_name", "") or ps.get("customer_email", "") or client_name

        if real_client == client_name and real_address == address:
            log.warning("  no better data found for order=%s — skipping", oid)
            continue

        new_vals = list(vals) + [""] * (_COL_COUNT - len(vals))
        if real_client and real_client.lower() != "unknown":
            new_vals[2] = real_client
        if real_address and real_address.lower() != "unknown":
            new_vals[3] = real_address

        patch_r = httpx.patch(
            f"{wb_base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}"
            f"/rows/itemAt(index={row['index']})",
            headers=h,
            json={"values": [new_vals[:_COL_COUNT]]},
            timeout=15.0,
        )
        patch_r.raise_for_status()
        log.info("  patched order=%s index=%d → client=%r address=%r",
                 oid, row["index"], new_vals[2], new_vals[3])
        patched += 1

    print(f"Done — patched {patched} rows")


if __name__ == "__main__":
    main()
