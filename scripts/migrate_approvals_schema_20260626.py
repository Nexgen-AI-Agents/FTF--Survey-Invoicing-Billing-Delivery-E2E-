"""One-off migration (2026-06-26): Approvals sheet schema rework.

  * remove the legacy 'FTF Link' table column (the Order ID cell becomes the link),
  * add the 'Learning provided by user' column,
  * backfill existing rows: make Order ID a clickable HYPERLINK, flatten any multi-line
    'AI Learning' cell to one line,
  * apply the gray (AI-managed) / blue (approver-editable) column color scheme.

Run AFTER pausing the server crons and deploying the new code. Defensive: backs up every
row first, deletes the column by ID (no name-encoding issues), and ABORTS if the resulting
header set does not exactly match APPROVAL_HEADERS — so it can never silently corrupt.
Safe to re-run (each step checks current state).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

import httpx  # noqa: E402
from config.settings import FTF_ORDER_URL  # noqa: E402
from core import onedrive_excel_client as oc  # noqa: E402

SHEET = oc.ONEDRIVE_SHEET_NAME
TABLE = oc.ONEDRIVE_TABLE_NAME
Q = chr(39)
BACKUP = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "approvals_backup_premigration.json"))


def _cols(base):
    return oc._graph_get_retry(f"{base}/worksheets/{SHEET}/tables/{TABLE}/columns",
                               headers=oc._headers(), timeout=20.0).json().get("value", [])


def _rows(base):
    return oc._graph_get_retry(f"{base}/worksheets/{SHEET}/tables/{TABLE}/rows",
                               headers=oc._headers(), timeout=20.0).json().get("value", [])


def main():
    base = oc._wb_base()
    h = oc._session_headers()

    # 1. BACKUP every row before touching anything.
    rows = _rows(base)
    backup = [r.get("values", [[]])[0] for r in rows]
    with open(BACKUP, "w", encoding="utf-8") as f:
        json.dump({"headers_before": [c["name"] for c in _cols(base)], "rows": backup}, f, indent=2, default=str)
    print(f"BACKED_UP {len(backup)} rows -> {BACKUP}")

    # 2. Delete legacy 'FTF Link' by column ID (reliable; no space-encoding).
    ftf = next((c for c in _cols(base) if c["name"] == "FTF Link"), None)
    if ftf:
        dr = httpx.delete(f"{base}/worksheets/{SHEET}/tables/{TABLE}/columns/{ftf['id']}", headers=h, timeout=20.0)
        print("DELETE 'FTF Link' ->", dr.status_code)
        dr.raise_for_status()
    else:
        print("'FTF Link' already absent — skip delete")

    # 3. Add 'Learning provided by user' at the end if missing.
    if "Learning provided by user" not in [c["name"] for c in _cols(base)]:
        ar = httpx.post(f"{base}/worksheets/{SHEET}/tables/{TABLE}/columns", headers=h,
                        json={"name": "Learning provided by user"}, timeout=20.0)
        print("ADD 'Learning provided by user' ->", ar.status_code)
        ar.raise_for_status()
    else:
        print("'Learning provided by user' already present — skip add")

    # 4. VERIFY headers now exactly match the code's schema, else ABORT (no recolor/backfill).
    final = [c["name"] for c in _cols(base)]
    print("FINAL_HEADERS", final)
    if final != oc.APPROVAL_HEADERS:
        raise SystemExit(f"ABORT: header mismatch\n got: {final}\n want: {oc.APPROVAL_HEADERS}")
    print("HEADERS_MATCH_SCHEMA ok")

    # 5. Backfill rows: Order ID -> HYPERLINK, flatten multi-line AI Learning.
    rows = _rows(base)
    last_row = 1 + len(rows)
    for row in rows:
        idx = row.get("index")
        vals = row.get("values", [[]])[0]
        if idx is None or not vals:
            continue
        er = idx + 2
        oid = str(vals[oc._COL_ORDER_ID]).strip()
        if oid:
            link = f"{FTF_ORDER_URL}/?order={oid}"
            httpx.patch(
                f"{base}/worksheets/{SHEET}/range(address={Q}{oc._col_letter(oc._COL_ORDER_ID)}{er}{Q})",
                headers=h, json={"formulas": [[f'=HYPERLINK("{link}","{oid}")']]}, timeout=10.0,
            ).raise_for_status()
        ai = str(vals[oc._COL_AI_LEARNING]) if len(vals) > oc._COL_AI_LEARNING else ""
        if "\n" in ai or "\r" in ai:
            flat = ai.replace("\r", "").replace("\n", " | ")
            httpx.patch(
                f"{base}/worksheets/{SHEET}/range(address={Q}{oc._col_letter(oc._COL_AI_LEARNING)}{er}{Q})",
                headers=h, json={"values": [[flat]]}, timeout=10.0,
            ).raise_for_status()
    print(f"BACKFILLED {len(rows)} rows (order-id hyperlink + flattened AI Learning)")

    # 6. Apply gray/blue column colors across header + all data rows.
    for c1, c2, color in oc._color_runs():
        httpx.patch(
            f"{base}/worksheets/{SHEET}/range(address={Q}{c1}1:{c2}{last_row}{Q})/format/fill",
            headers=h, json={"color": color}, timeout=15.0,
        ).raise_for_status()
    print(f"COLORS_APPLIED A1:{oc._END_COL}{last_row}")

    # 7. Refresh the guide + how-to tabs (version-gated; new column docs + color key).
    try:
        oc.ensure_guide_sheet()
        oc.ensure_howto_sheet()
        print("GUIDE_HOWTO_REFRESHED")
    except Exception as exc:  # noqa: BLE001
        print("guide/howto refresh warning:", exc)

    oc._close_session()
    print("MIGRATION_DONE")


if __name__ == "__main__":
    main()
