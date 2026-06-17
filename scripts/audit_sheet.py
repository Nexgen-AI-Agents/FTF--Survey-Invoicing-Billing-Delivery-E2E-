"""Audit the live OneDrive Approvals sheet for bugs: invoiced-in-sheet, wrong red fills,
duplicate order rows, missing dropdown, and blank/garbled rows. Read-only."""
import io, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
from dotenv import load_dotenv
load_dotenv()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import httpx, openpyxl
from core.onedrive_excel_client import (
    _wb_base, _session_headers, _download_workbook_bytes,
    ONEDRIVE_SHEET_NAME, ONEDRIVE_TABLE_NAME, APPROVAL_HEADERS, _COL_ACTION, _END_COL,
)
from core.ftf_client import get_order

base, h = _wb_base(), _session_headers()
rows = httpx.get(f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
                 headers=h, timeout=30).json().get("value", [])
print(f"=== {len(rows)} rows in Approvals sheet ===\n")

# fills + dropdown from the workbook
wb = openpyxl.load_workbook(io.BytesIO(_download_workbook_bytes()))
ws = wb[ONEDRIVE_SHEET_NAME]
fills = {}
for r in ws.iter_rows(min_row=2):
    oid = str(r[0].value).strip() if r[0].value is not None else ""
    f = r[0].fill
    fills[r[0].row] = (f.fgColor.rgb if f and f.patternType else None)
dvs = [str(d.sqref) for d in ws.data_validations.dataValidation if d.type == "list" and "J" in str(d.sqref)]
print(f"Action dropdown validation ranges: {dvs}")
canonical = any(s.replace(" ", "") == f"J2:J10000" for s in dvs)
print(f"  canonical J2:J10000 present: {canonical}\n")

seen, bugs = {}, []
for row in rows:
    v = row.get("values", [[]])[0]
    if not v:
        continue
    oid = str(v[0]).strip()
    status = str(v[1]).strip() if len(v) > 1 else ""
    amount = v[5] if len(v) > 5 else ""
    action = str(v[_COL_ACTION]).strip() if len(v) > _COL_ACTION else ""
    notes = str(v[10])[:60] if len(v) > 10 else ""
    excel_row = row.get("index", -1) + 2
    fill = fills.get(excel_row)
    is_red = fill in ("FFFF4444", "00FF4444") or (fill and "FF4444" in str(fill))

    # duplicate order ids
    if oid in seen:
        bugs.append(f"DUPLICATE row: order {oid} appears in rows {seen[oid]} and {excel_row}")
    seen.setdefault(oid, excel_row)

    # cross-check FTF
    ftf = "?"
    try:
        d = get_order(oid)
        invoiced = bool(d.get("invoiced"))
        ftf_status = d.get("status", "")
        ftf = f"invoiced={invoiced} ftf_status={ftf_status!r}"
        if invoiced and not action:
            bugs.append(f"INVOICED-IN-SHEET (awaiting action): order {oid} is invoiced in FTF but sits unactioned (status col={status!r})")
        # canceled-after-posting: FTF now Canceled but row still awaiting action and priced
        if str(ftf_status).lower() in ("canceled", "cancelled") or d.get("status_code") == 0:
            if not action and status.lower() not in ("canceled", "cancelled"):
                bugs.append(f"CANCELED-IN-SHEET (stale): order {oid} is Canceled in FTF but row shows status={status!r} amt={amount} unactioned — approving it would invoice a canceled order")
        # red-fill correctness: red iff Canceled/Delivered
        should_red = status.lower() in ("canceled", "cancelled", "delivered")
        if is_red and not should_red:
            bugs.append(f"WRONG RED: order {oid} row{excel_row} red but status={status!r} (only Canceled/Delivered should be red)")
        if should_red and not is_red:
            bugs.append(f"MISSING RED: order {oid} row{excel_row} status={status!r} should be red but isn't")
    except Exception as e:
        ftf = f"FTF-ERR {e}"

    if not oid:
        bugs.append(f"BLANK order id at row {excel_row}")
    print(f"r{excel_row} {oid} | {status:14} | amt={amount} | act={action or '-'} | red={is_red} | {ftf} | {notes!r}")

print("\n=== BUGS ===")
if not bugs:
    print("  none found")
for b in bugs:
    print("  •", b)
