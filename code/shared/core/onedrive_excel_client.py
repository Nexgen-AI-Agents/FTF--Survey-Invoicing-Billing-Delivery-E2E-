"""
onedrive_excel_client.py — Microsoft Graph Workbook API client.

Reads/writes rows in FTF-Invoicing Agent.xlsx on nesa@nexgenlogix.com's OneDrive.
Uses Azure AD app credentials via client_credentials grant (AZURE_TENANT_ID / AZURE_APP_ID / AZURE_CLIENT_SECRET).

Required Graph permissions (application):
  Files.ReadWrite.All  — read/write files in any user's OneDrive
"""

import base64
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import httpx

from config.settings import (
    AZURE_APP_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID,
    ONEDRIVE_FILE_USER, ONEDRIVE_FILE_PATH, ONEDRIVE_SHARE_URL,
    ONEDRIVE_SHEET_NAME, ONEDRIVE_TABLE_NAME,
)
from core.exceptions import AgentError
from core.logger import get_logger

log = get_logger("onedrive_excel_client")

_GRAPH     = "https://graph.microsoft.com/v1.0"
_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_SCOPE     = "https://graph.microsoft.com/.default"

_cache: dict = {}

# Column order must stay in sync with append_approval_row() values list
APPROVAL_HEADERS = [
    "Order ID", "Order Status", "Client Name", "Property Address", "Service",
    "Amount", "Confidence", "Escalate", "FTF Link",
    "Action", "Notes", "Posted At", "Processed At",
]
_COL_COUNT        = len(APPROVAL_HEADERS)   # 13
_END_COL          = chr(ord("A") + _COL_COUNT - 1)   # "M"
_COL_ACTION       = 9    # J  — dropdown: Approve / Reject / On-hold
_COL_PROCESSED_AT = 12   # M

# Row fill colors for Action dropdown choices (light palette, Excel-compatible hex)
_ACTION_COLORS = {
    "Approve": "#C6EFCE",
    "Reject":  "#FFC7CE",
    "On-hold": "#FFEB9C",
}


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_token() -> str:
    now = time.monotonic()
    if _cache.get("od_token") and _cache.get("od_exp", 0) > now + 60:
        return _cache["od_token"]

    if not all([AZURE_TENANT_ID, AZURE_APP_ID, AZURE_CLIENT_SECRET]):
        raise AgentError("Graph API credentials not configured (AZURE_TENANT_ID / AZURE_APP_ID / AZURE_CLIENT_SECRET)")

    r = httpx.post(
        _TOKEN_URL.format(tenant=AZURE_TENANT_ID),
        data={
            "grant_type":    "client_credentials",
            "client_id":     AZURE_APP_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "scope":         _SCOPE,
        },
        timeout=15.0,
    )
    r.raise_for_status()
    data = r.json()
    _cache["od_token"] = data["access_token"]
    _cache["od_exp"]   = now + int(data.get("expires_in", 3600))
    log.debug("onedrive token refreshed")
    return _cache["od_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


# ── File + session resolution ─────────────────────────────────────────────────

def _share_id(share_url: str) -> str:
    """Encode a sharing URL into a Graph API share ID (u! prefix + base64url, no padding)."""
    encoded = base64.urlsafe_b64encode(share_url.encode("utf-8")).decode("utf-8").rstrip("=")
    return f"u!{encoded}"


def _get_item_id() -> str:
    """Return the OneDrive driveItem ID, caching drive_id alongside it.

    Tries ONEDRIVE_SHARE_URL first (resolves directly by sharing link — no path guessing).
    Falls back to ONEDRIVE_FILE_PATH lookup if the share URL is not set.
    """
    if _cache.get("od_item_id"):
        return _cache["od_item_id"]

    if ONEDRIVE_SHARE_URL:
        r = httpx.get(
            f"{_GRAPH}/shares/{_share_id(ONEDRIVE_SHARE_URL)}/driveItem",
            headers=_headers(),
            timeout=15.0,
        )
        if r.status_code == 403:
            raise AgentError(
                "Graph API cannot access this file via sharing link. "
                "Ensure the Azure app has Files.ReadWrite.All permission."
            )
        r.raise_for_status()
        item = r.json()
        _cache["od_item_id"] = item["id"]
        _cache["od_drive_id"] = item["parentReference"]["driveId"]
        log.info("onedrive item resolved via share URL: item=%s drive=%s",
                 item["id"], item["parentReference"]["driveId"])
        return _cache["od_item_id"]

    # Fallback: path-based lookup
    encoded = urllib.parse.quote(ONEDRIVE_FILE_PATH, safe="/")
    r = httpx.get(
        f"{_GRAPH}/users/{ONEDRIVE_FILE_USER}/drive/root:/{encoded}",
        headers=_headers(),
        timeout=15.0,
    )
    if r.status_code == 404:
        raise AgentError(
            f"OneDrive file not found: '{ONEDRIVE_FILE_PATH}' for user '{ONEDRIVE_FILE_USER}'. "
            "Set ONEDRIVE_SHARE_URL with the file's sharing link or fix ONEDRIVE_FILE_PATH."
        )
    r.raise_for_status()
    _cache["od_item_id"] = r.json()["id"]
    log.info("onedrive item resolved via path: %s", _cache["od_item_id"])
    return _cache["od_item_id"]


def _wb_base() -> str:
    item_id  = _get_item_id()
    drive_id = _cache.get("od_drive_id")
    if drive_id:
        return f"{_GRAPH}/drives/{drive_id}/items/{item_id}/workbook"
    return f"{_GRAPH}/users/{ONEDRIVE_FILE_USER}/drive/items/{item_id}/workbook"


def _session_headers() -> dict:
    """Add workbook-session-id header for batched operations (faster)."""
    h = _headers()
    if not _cache.get("od_session"):
        try:
            r = httpx.post(
                f"{_wb_base()}/createSession",
                headers=h,
                json={"persistChanges": True},
                timeout=20.0,
            )
            r.raise_for_status()
            _cache["od_session"] = r.json()["id"]
            log.debug("workbook session created")
        except Exception as exc:
            log.warning("workbook session failed (sessionless fallback): %s", exc)
    if _cache.get("od_session"):
        h["workbook-session-id"] = _cache["od_session"]
    return h


# ── Sheet + table setup ───────────────────────────────────────────────────────

def _setup_full_sheet_via_openpyxl() -> None:
    """Create/recreate the Approvals sheet with all formatting via openpyxl download → modify → upload.

    This is the ONLY way to set data validation and conditional formatting on an Excel workbook
    in OneDrive — the Graph API workbook REST endpoints do not expose these operations.

    The file must NOT have an active workbook session when this runs (PUT upload returns 423 if
    the session lock is held). Call _close_session() before invoking.
    """
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.worksheet.table import Table, TableStyleInfo

    try:
        raw = _download_workbook_bytes()
    except Exception as exc:
        log.warning("_setup_full_sheet_via_openpyxl: download failed — skipping: %s", exc)
        return

    wb = openpyxl.load_workbook(io.BytesIO(raw))

    # Remove stale Approvals sheet (clean slate on every schema change)
    if ONEDRIVE_SHEET_NAME in wb.sheetnames:
        del wb[ONEDRIVE_SHEET_NAME]

    ws = wb.create_sheet(ONEDRIVE_SHEET_NAME)

    # ── Headers ───────────────────────────────────────────────────────────────
    for col_idx, header in enumerate(APPROVAL_HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)

    # ── Excel Table (so Graph API /tables/{name}/rows/add works) ─────────────
    table_ref = f"A1:{_END_COL}1"
    tab = Table(displayName=ONEDRIVE_TABLE_NAME, ref=table_ref)
    tab.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium9", showFirstColumn=False,
        showLastColumn=False, showRowStripes=True, showColumnStripes=False,
    )
    ws.add_table(tab)

    # ── Dropdown on Action column ─────────────────────────────────────────────
    action_letter = chr(ord("A") + _COL_ACTION)   # "J"
    dv = DataValidation(
        type="list",
        formula1='"Approve,Reject,On-hold"',
        allow_blank=True,
        showDropDown=False,   # False = show the dropdown arrow in Excel
    )
    dv.error      = "Select Approve, Reject, or On-hold"
    dv.errorTitle = "Invalid action"
    dv.sqref      = f"{action_letter}2:{action_letter}10000"
    ws.add_data_validation(dv)

    # ── Row colors by Action value ────────────────────────────────────────────
    full_range = f"A2:{_END_COL}10000"
    for action_val, hex_color in [("Approve", "C6EFCE"), ("Reject", "FFC7CE"), ("On-hold", "FFEB9C")]:
        fill = PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")
        ws.conditional_formatting.add(
            full_range,
            FormulaRule(formula=[f'${action_letter}2="{action_val}"'], fill=fill),
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    try:
        _upload_workbook_bytes(buf.read())
        log.info(
            "_setup_full_sheet_via_openpyxl: Approvals sheet created — %d cols, dropdown + row colors applied",
            _COL_COUNT,
        )
    except Exception as exc:
        log.warning("_setup_full_sheet_via_openpyxl: upload failed: %s", exc)


def ensure_approval_sheet() -> None:
    """Ensure the Approvals sheet and ApprovalTable exist with the correct schema.

    Uses plain auth headers (no workbook session) for read-only checks so the session
    is never opened before a potential file upload (_setup_full_sheet_via_openpyxl uploads
    the raw file — which returns 423 Locked if a session is held).
    """
    if _cache.get("od_formatting_done"):
        return   # Already verified this session

    base = _wb_base()
    h    = _headers()   # intentionally NOT _session_headers() — avoid opening a session

    # ── Check sheet + table ───────────────────────────────────────────────────
    needs_setup = False

    r_sheets = httpx.get(f"{base}/worksheets", headers=h, timeout=15.0)
    r_sheets.raise_for_status()
    existing_sheets = [s["name"] for s in r_sheets.json().get("value", [])]

    if ONEDRIVE_SHEET_NAME not in existing_sheets:
        log.info("ensure_approval_sheet: sheet missing — will create via openpyxl")
        needs_setup = True
    else:
        r_cols = httpx.get(
            f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/columns",
            headers=h, timeout=15.0,
        )
        if not r_cols.is_success:
            log.info("ensure_approval_sheet: table missing or unreadable (status %d) — will recreate", r_cols.status_code)
            needs_setup = True
        else:
            actual_cols = len(r_cols.json().get("value", []))
            if actual_cols != _COL_COUNT:
                log.info(
                    "ensure_approval_sheet: schema mismatch (%d cols vs expected %d) — will recreate",
                    actual_cols, _COL_COUNT,
                )
                needs_setup = True

    if needs_setup:
        _close_session()   # release any server-side lock before raw file upload
        _setup_full_sheet_via_openpyxl()

    _cache["od_formatting_done"] = True


# ── Public write API ──────────────────────────────────────────────────────────

def get_pending_order_ids() -> set:
    """Return order IDs that already have a row in the approval table with blank Action (awaiting decision)."""
    try:
        ensure_approval_sheet()
        r = httpx.get(
            f"{_wb_base()}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
            headers=_session_headers(),
            timeout=15.0,
        )
        r.raise_for_status()
        pending = set()
        for row in r.json().get("value", []):
            vals = row.get("values", [[]])[0]
            # Action column (index _COL_ACTION) is blank → awaiting decision
            if len(vals) > _COL_ACTION and not str(vals[_COL_ACTION]).strip():
                pending.add(str(vals[0]).strip())
        log.info("get_pending_order_ids: %d awaiting-action rows in Excel", len(pending))
        return pending
    except Exception as exc:
        log.warning("get_pending_order_ids failed (dedup disabled): %s", exc)
        return set()


def _close_session() -> None:
    """Close the current workbook session on the Graph API server, releasing the file lock."""
    session_id = _cache.pop("od_session", None)
    if not session_id:
        return
    try:
        base = _wb_base()
        httpx.post(
            f"{base}/closeSession",
            headers={
                "Authorization": f"Bearer {_get_token()}",
                "workbook-session-id": session_id,
            },
            timeout=10.0,
        )
        log.debug("workbook session closed")
    except Exception as exc:
        log.debug("session close error (ignored): %s", exc)


def _download_workbook_bytes() -> bytes:
    """Download the workbook file content as raw bytes."""
    drive_id = _cache.get("od_drive_id")
    item_id  = _get_item_id()
    url = (
        f"{_GRAPH}/drives/{drive_id}/items/{item_id}/content"
        if drive_id else
        f"{_GRAPH}/users/{ONEDRIVE_FILE_USER}/drive/items/{item_id}/content"
    )
    r = httpx.get(url, headers={"Authorization": f"Bearer {_get_token()}"}, follow_redirects=True, timeout=30.0)
    r.raise_for_status()
    return r.content


def _upload_workbook_bytes(data: bytes) -> None:
    """Replace the workbook file with new content (PUT upload). Retries once on 423."""
    import time
    drive_id = _cache.get("od_drive_id")
    item_id  = _get_item_id()
    url = (
        f"{_GRAPH}/drives/{drive_id}/items/{item_id}/content"
        if drive_id else
        f"{_GRAPH}/users/{ONEDRIVE_FILE_USER}/drive/items/{item_id}/content"
    )
    put_headers = {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/octet-stream"}
    for attempt in range(3):
        r = httpx.put(url, headers=put_headers, content=data, timeout=60.0)
        if r.status_code == 423:
            wait = (attempt + 1) * 4
            log.warning("upload 423 Locked — retrying in %ds (attempt %d/3)", wait, attempt + 1)
            time.sleep(wait)
            put_headers["Authorization"] = f"Bearer {_get_token()}"  # refresh token
            continue
        r.raise_for_status()
        # Invalidate session — file changed on disk
        _cache.pop("od_session", None)
        log.info("workbook re-uploaded (%d bytes)", len(data))
        return
    raise AgentError("workbook upload failed: file locked after 3 retries (423)")


def append_approval_row(
    order_id:     str,
    client_name:  str,
    address:      str,
    service:      str,
    amount:       float,
    confidence:   str,
    escalate:     bool,
    ftf_link:     str,
    order_status: str = "",
    posted_at:    Optional[str] = None,
    notes:        str = "",
) -> None:
    """Append a new row to the approval table. Action column is blank — user picks from dropdown."""
    ensure_approval_sheet()

    if not posted_at:
        posted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    values = [[
        str(order_id),
        str(order_status),          # Order Status — FTF stage status (ng_status_desc)
        str(client_name),
        str(address)[:120],
        str(service),
        float(amount),
        str(confidence),
        "Yes" if escalate else "No",
        str(ftf_link),
        "",                         # Action — blank; user selects Approve/Reject/On-hold
        str(notes),                 # Notes — pre-filled for escalations
        posted_at,
        "",                         # Processed At — filled after pipeline processes decision
    ]]

    r = httpx.post(
        f"{_wb_base()}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows/add",
        headers=_session_headers(),
        json={"values": values},
        timeout=15.0,
    )
    r.raise_for_status()
    log.info("excel row appended order_id=%s amount=%.2f status=%s", order_id, amount, order_status)


def mark_row_processed(order_id: str) -> None:
    """Set Processed At timestamp on the most recent blank-Action row matching order_id."""
    base = _wb_base()
    h    = _session_headers()

    r = httpx.get(
        f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=h, timeout=15.0,
    )
    r.raise_for_status()
    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for row in reversed(r.json().get("value", [])):
        vals = row.get("values", [[]])[0]
        if len(vals) >= 1 and str(vals[0]) == str(order_id):
            idx = row["index"]
            new_vals = list(vals) + [""] * (_COL_COUNT - len(vals))
            new_vals[_COL_PROCESSED_AT] = processed_at
            httpx.patch(
                f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows/itemAt(index={idx})",
                headers=h,
                json={"values": [new_vals[:_COL_COUNT]]},
                timeout=15.0,
            ).raise_for_status()
            log.info("marked processed order_id=%s at=%s", order_id, processed_at)
            return

    log.warning("mark_row_processed: order_id=%s not found in Excel", order_id)
