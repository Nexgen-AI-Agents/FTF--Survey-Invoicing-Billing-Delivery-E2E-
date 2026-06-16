"""One-off: clear stale red fills left on recycled Excel rows.

A row should be red ONLY if it is a genuinely flagged order (canceled / delivered / condo /
manual-pricing). Graph row-deletes leave direct cell fills behind, so normal rows recycled
into a previously-red physical position inherit a stale red. This walks every current row and
sets the fill deterministically: red for flagged rows, cleared for everything else.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
from dotenv import load_dotenv
load_dotenv()
import httpx
from core.onedrive_excel_client import (
    _wb_base, _session_headers, ONEDRIVE_SHEET_NAME, ONEDRIVE_TABLE_NAME, _END_COL,
)

# Explicit red fill is applied by A3 ONLY for canceled/delivered orders (incl. a delivered
# order held for manual pricing). Condo rows are NOT explicitly red (they go light-pink via
# conditional formatting once auto-rejected); non-delivered manual-pricing rows are not red
# either. So the source of truth is the Order Status column, not note text.
_FLAG_STATUSES = {"canceled", "cancelled", "delivered"}

base = _wb_base()
h = _session_headers()
r = httpx.get(f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
              headers=h, timeout=30.0)
r.raise_for_status()
rows = r.json().get("value", [])
print(f"{len(rows)} rows")

cleared = reddened = 0
for row in rows:
    idx = row.get("index")
    vals = row.get("values", [[]])[0]
    if idx is None or not vals:
        continue
    order_id = str(vals[0]).strip()
    status   = str(vals[1]).strip().lower() if len(vals) > 1 else ""
    should_be_red = status in _FLAG_STATUSES
    excel_row = idx + 2
    rng = f"A{excel_row}:{_END_COL}{excel_row}"
    if should_be_red:
        httpx.patch(f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='{rng}')/format/fill",
                    headers=h, json={"color": "#FF4444"}, timeout=10.0).raise_for_status()
        reddened += 1
        print(f"  RED   {order_id} (row {excel_row}) status={status}")
    else:
        httpx.post(f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='{rng}')/format/fill/clear",
                   headers=h, timeout=10.0).raise_for_status()
        cleared += 1
        print(f"  clear {order_id} (row {excel_row})")

print(f"\nDone. cleared={cleared} red={reddened}")
