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
from zoneinfo import ZoneInfo

_EASTERN = ZoneInfo("America/New_York")

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

# Guide tab — bump version string whenever guide content changes to force a re-write
GUIDE_SHEET_NAME = "Pipeline Guide"
_GUIDE_VERSION   = "v5"   # increment when guide content changes

# Pricing Rules tab — user-editable table of override prices
PRICING_RULES_SHEET_NAME  = "Pricing Rules"
PRICING_RULES_TABLE_NAME  = "PricingRulesTable"
PRICING_RULES_HEADERS = [
    "Rule ID", "Status", "Service Pattern", "County", "Client Pattern",
    "Price ($)", "Priority", "Notes",
]
_PR_COL_COUNT = len(PRICING_RULES_HEADERS)   # 8

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


def ensure_pricing_rules_sheet() -> None:
    """Create the 'Pricing Rules' tab if it doesn't exist.

    This tab is user-editable. The pipeline reads it each run to apply explicit
    price overrides before the AI pricing step. Users add rows directly in Excel:

      Service Pattern | County | Client Pattern | Price ($) | Priority | Notes
      Boundary Survey | Hillsborough | Hillsborough Title | 550.00 | 1 | Standard rate
      *               | *            | CDS-Commercial     | 450.00 | 5 | All CDS orders

    * = wildcard (matches anything). Lower Priority number = higher priority.
    Set Status = Inactive to disable a rule without deleting it.
    """
    if _cache.get("od_pricing_rules_done"):
        return

    base = _wb_base()
    h    = _headers()

    r_sheets = httpx.get(f"{base}/worksheets", headers=h, timeout=15.0)
    r_sheets.raise_for_status()
    existing_sheets = [s["name"] for s in r_sheets.json().get("value", [])]

    if PRICING_RULES_SHEET_NAME in existing_sheets:
        _cache["od_pricing_rules_done"] = True
        return

    # Create via openpyxl upload — only way to add a table with proper headers
    log.info("Pricing Rules tab missing — creating it")
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.worksheet.table import Table, TableStyleInfo

    try:
        _close_session()
        raw = _download_workbook_bytes()
    except Exception as exc:
        log.warning("ensure_pricing_rules_sheet: download failed — skipping: %s", exc)
        return

    wb = openpyxl.load_workbook(io.BytesIO(raw))
    ws = wb.create_sheet(PRICING_RULES_SHEET_NAME)

    # ── Column widths ─────────────────────────────────────────────────────────
    col_widths = [8, 10, 28, 20, 30, 14, 10, 50]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w

    # ── Headers ────────────────────────────────────────────────────────────────
    HDR_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    for col_idx, hdr in enumerate(PRICING_RULES_HEADERS, 1):
        c = ws.cell(row=1, column=col_idx, value=hdr)
        c.font = Font(bold=True, color="FFFFFF", size=11)
        c.fill = HDR_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")

    # ── Seed row — example rule so users understand the format ────────────────
    EXAMPLE_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    seed = ["1", "Active", "*", "*", "*", 0.0, 999,
            "EXAMPLE — delete this row. Set Price=0 to keep AI pricing. * = match anything."]
    for col_idx, val in enumerate(seed, 1):
        c = ws.cell(row=2, column=col_idx, value=val)
        c.fill = EXAMPLE_FILL
        c.alignment = Alignment(vertical="center", wrap_text=(col_idx == _PR_COL_COUNT))

    # ── Excel Table ───────────────────────────────────────────────────────────
    end_col = chr(ord("A") + _PR_COL_COUNT - 1)
    tab = Table(displayName=PRICING_RULES_TABLE_NAME, ref=f"A1:{end_col}2")
    tab.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium7", showRowStripes=True,
        showFirstColumn=False, showLastColumn=False, showColumnStripes=False,
    )
    ws.add_table(tab)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    try:
        _upload_workbook_bytes(buf.read())
        log.info("Pricing Rules tab created")
    except Exception as exc:
        log.warning("Pricing Rules tab upload failed (non-fatal): %s", exc)
        return

    _cache["od_pricing_rules_done"] = True


# ── In-memory cache for pricing rules (refreshed once per pipeline run) ───────
_pricing_rules_cache: list | None = None


def get_pricing_rules() -> list[dict]:
    """Return active pricing rules from the 'Pricing Rules' tab.

    Rules are sorted by Priority (ascending — lower number = higher priority).
    Cached for the duration of the pipeline run — call invalidate if needed.

    Each rule dict: {service, county, client, price, priority, notes}
    Pattern values: '*' matches anything; otherwise case-insensitive substring match.
    """
    global _pricing_rules_cache
    if _pricing_rules_cache is not None:
        return _pricing_rules_cache

    try:
        ensure_pricing_rules_sheet()
        r = httpx.get(
            f"{_wb_base()}/worksheets/{PRICING_RULES_SHEET_NAME}/tables/{PRICING_RULES_TABLE_NAME}/rows",
            headers=_session_headers(),
            timeout=15.0,
        )
        if not r.is_success:
            log.warning("get_pricing_rules: table read failed (%d) — no rules applied", r.status_code)
            _pricing_rules_cache = []
            return []

        rules = []
        for row in r.json().get("value", []):
            vals = (row.get("values") or [[]])[0]
            if len(vals) < _PR_COL_COUNT:
                vals = list(vals) + [""] * (_PR_COL_COUNT - len(vals))

            status  = str(vals[1]).strip()
            if status.lower() != "active":
                continue

            price = 0.0
            try:
                price = float(vals[5])
            except (ValueError, TypeError):
                pass

            priority = 999
            try:
                priority = int(float(vals[6]))
            except (ValueError, TypeError):
                pass

            rules.append({
                "rule_id":  str(vals[0]).strip(),
                "service":  str(vals[2]).strip() or "*",
                "county":   str(vals[3]).strip() or "*",
                "client":   str(vals[4]).strip() or "*",
                "price":    price,
                "priority": priority,
                "notes":    str(vals[7]).strip() if len(vals) > 7 else "",
            })

        rules.sort(key=lambda r: r["priority"])
        _pricing_rules_cache = rules
        log.info("get_pricing_rules: %d active rules loaded", len(rules))
        return rules

    except Exception as exc:
        log.warning("get_pricing_rules failed — no rules applied: %s", exc)
        _pricing_rules_cache = []
        return []


def match_pricing_rule(service: str, county: str, client: str) -> dict | None:
    """Return the highest-priority matching rule, or None if no match.

    Matching logic (all three must match):
      * = wildcard (matches any non-empty string)
      Otherwise: case-insensitive substring match
      Rule with price=0 means "keep AI pricing" (no override).
    """
    s_lower = service.lower()
    c_lower = county.lower()
    cl_lower = client.lower()

    for rule in get_pricing_rules():
        svc_pat = rule["service"]
        cty_pat = rule["county"]
        cli_pat = rule["client"]

        svc_match = (svc_pat == "*") or (svc_pat.lower() in s_lower)
        cty_match = (cty_pat == "*") or (cty_pat.lower() in c_lower)
        cli_match = (cli_pat == "*") or (cli_pat.lower() in cl_lower)

        if svc_match and cty_match and cli_match:
            return rule

    return None


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
    # Always ensure the guide tab is current (version-gated — skips if already up to date)
    ensure_guide_sheet()
    # Ensure the user-editable Pricing Rules tab exists
    ensure_pricing_rules_sheet()


def ensure_guide_sheet() -> None:
    """Create or update the 'Pipeline Guide' tab in the OneDrive workbook.

    Version-gated: skips the download+upload cycle if the tab already has the
    current _GUIDE_VERSION stamped in cell A2.  Bump _GUIDE_VERSION whenever
    guide content changes to force a re-write on the next run.
    """
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    # ── Check whether an update is actually needed ────────────────────────────
    try:
        base = _wb_base()
        h    = _headers()
        r = httpx.get(
            f"{base}/worksheets/{GUIDE_SHEET_NAME}/range(address='B2')/values",
            headers=h,
            timeout=10.0,
        )
        if r.is_success:
            existing_version = (r.json().get("values") or [[""]])[0][0]
            if str(existing_version).strip() == _GUIDE_VERSION:
                log.debug("guide sheet already at %s — skipping update", _GUIDE_VERSION)
                return
    except Exception:
        pass  # sheet doesn't exist yet — fall through to create it

    log.info("guide sheet missing or outdated — writing %s", _GUIDE_VERSION)

    # ── Download workbook, write guide tab, upload ────────────────────────────
    try:
        _close_session()
        raw = _download_workbook_bytes()
    except Exception as exc:
        log.warning("ensure_guide_sheet: download failed — skipping: %s", exc)
        return

    wb = openpyxl.load_workbook(io.BytesIO(raw))

    if GUIDE_SHEET_NAME in wb.sheetnames:
        del wb[GUIDE_SHEET_NAME]

    ws = wb.create_sheet(GUIDE_SHEET_NAME)

    # ── Styling helpers ───────────────────────────────────────────────────────
    def _hdr_fill(hex_color: str) -> PatternFill:
        return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")

    def _thin_border() -> Border:
        s = Side(style="thin", color="CCCCCC")
        return Border(left=s, right=s, top=s, bottom=s)

    COLOR_SECTION  = "1F4E79"   # dark navy  — section header text
    FILL_SECTION   = "BDD7EE"   # light blue — section header row
    FILL_ALT       = "F2F2F2"   # light grey — alternating content rows
    FILL_WARN      = "FFF2CC"   # yellow     — warning rows
    FILL_GOOD      = "E2EFDA"   # green      — good/approved rows
    FILL_BAD       = "FCE4D6"   # salmon     — blocked/rejected rows

    def _write(row: int, col: int, value, bold=False, fill=None, wrap=False,
               color=None, size=11, align="left"):
        c = ws.cell(row=row, column=col, value=value)
        c.font = Font(bold=bold, color=color or "000000", size=size)
        if fill:
            c.fill = _hdr_fill(fill)
        c.border = _thin_border()
        c.alignment = Alignment(
            wrap_text=wrap,
            vertical="center",
            horizontal=align,
        )
        return c

    def _section(row: int, title: str) -> int:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        c = ws.cell(row=row, column=1, value=title)
        c.font      = Font(bold=True, color=COLOR_SECTION, size=12)
        c.fill      = _hdr_fill(FILL_SECTION)
        c.border    = _thin_border()
        c.alignment = Alignment(vertical="center", horizontal="left")
        ws.row_dimensions[row].height = 22
        return row + 1

    # ── Column widths ─────────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 90

    # ── Row 1 — title ─────────────────────────────────────────────────────────
    ws.merge_cells("A1:B1")
    c = ws.cell(row=1, column=1, value="FTF Invoice Pipeline — Field Guide")
    c.font      = Font(bold=True, size=14, color="FFFFFF")
    c.fill      = _hdr_fill("1F4E79")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # ── Row 2 — version stamp ─────────────────────────────────────────────────
    _write(2, 1, "Last Updated", bold=True, fill="DEEAF1")
    _write(2, 2, f"{_GUIDE_VERSION} — {datetime.now(_EASTERN).strftime('%Y-%m-%d %H:%M %Z')}",
           fill="DEEAF1")
    ws.row_dimensions[2].height = 18

    r = 3  # current row cursor

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 1 — COLUMN REFERENCE
    # ═════════════════════════════════════════════════════════════════════════
    r = _section(r, "COLUMN REFERENCE  (Invoices – Pending Approval tab)")
    cols_guide = [
        ("Order ID",        "Unique FTF order number. Click the FTF Link to open it in FieldToFinish."),
        ("Order Status",    "Current status of the order inside the FTF system (e.g. In Progress, Complete, Field)."),
        ("Client Name",     "Name of the client or title company who placed the order."),
        ("Property Address","Survey site address — the property to be surveyed."),
        ("Service",         "Survey service type the AI identified (e.g. Boundary Survey, Corner Staking, ALTA/NSPS, "
                            "Elevation Certificate). 'CONDO — Cannot Survey' means the order cannot be processed."),
        ("Amount",          "Invoice amount in USD set by the AI. For MANUAL PRICING rows: type the correct amount "
                            "directly in this cell before setting Action = Approve."),
        ("Confidence",      "How certain the AI is about the price. See the CONFIDENCE LEVELS section below."),
        ("Escalate",        "Yes = the AI flagged this order as unusual. Robert or Ryan should review "
                            "before you approve."),
        ("FTF Link",        "Hyperlink — click 'View Order' to open the order directly in FieldToFinish."),
        ("Action",          "YOUR DECISION. Select from the dropdown: Approve / Reject / On-hold. "
                            "Leave blank to defer. The pipeline checks this every 30 minutes."),
        ("Notes",           "Pre-filled by the pipeline with the reason for escalation, issue description, "
                            "or the manual action step required. Read this before acting."),
        ("Posted At",       "Date and time the pipeline posted this row for your review (Eastern Time)."),
        ("Processed At",    "Auto-filled by the pipeline when it processes your Action decision. "
                            "Once filled, the row is complete."),
    ]
    for i, (col, desc) in enumerate(cols_guide):
        fill = FILL_ALT if i % 2 == 0 else None
        _write(r, 1, col,  bold=True, fill=fill)
        _write(r, 2, desc, fill=fill, wrap=True)
        ws.row_dimensions[r].height = 30
        r += 1

    r += 1  # blank gap

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 2 — CONFIDENCE LEVELS
    # ═════════════════════════════════════════════════════════════════════════
    r = _section(r, "CONFIDENCE LEVELS")
    conf_guide = [
        ("HIGH",   FILL_GOOD,
         "Price is very likely correct. AI matched the exact service type, found historical pricing "
         "data for this county, and the client has a negotiated rate on file. Safe to approve quickly."),
        ("MEDIUM", FILL_ALT,
         "Reasonable estimate but some data gaps. The AI may have inferred the service type from order "
         "notes rather than the FTF service field, or there was no county-specific pricing history. "
         "Do a quick sanity check — does the amount look right for this service?"),
        ("LOW",    FILL_WARN,
         "AI had limited data and had to guess. Thin pricing history, unclear service type, or missing "
         "property details. Review carefully before approving. Consider adjusting the amount."),
        ("N/A",    FILL_BAD,
         "Not applicable. Order is either a CONDO (cannot survey — no land parcel exists) or requires "
         "manual pricing (enter amount in the Amount column)."),
    ]
    for level, fill, desc in conf_guide:
        _write(r, 1, level, bold=True, fill=fill)
        _write(r, 2, desc,  fill=fill, wrap=True)
        ws.row_dimensions[r].height = 45
        r += 1

    r += 1

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 3 — NOTES FIELD GUIDE
    # ═════════════════════════════════════════════════════════════════════════
    r = _section(r, "NOTES FIELD GUIDE  —  what to do based on the Notes content")
    notes_guide = [
        ("CONDO ORDER —",
         FILL_BAD,
         "Land survey is NOT possible on this property (condo / airspace unit — no land parcel to survey). "
         "Row is AUTO-REJECTED by the pipeline. Your action: contact the client to explain, arrange a refund "
         "or redirect to an appropriate service (e.g. interior unit measurement). Do NOT approve."),
        ("MANUAL PRICING REQUIRED —",
         FILL_WARN,
         "The AI could not determine the correct price (complex job, unusual service, or missing data). "
         "Enter the correct amount in the Amount cell for that row, then set Action = Approve."),
        ("ESCALATE —",
         FILL_WARN,
         "The AI flagged unusual characteristics (large lot, commercial property, FEMA zone, high value, "
         "duplicate address, etc.). Details follow the dash. Get Robert or Ryan to review before approving."),
        ("(empty)",
         FILL_GOOD,
         "Standard order. The AI is confident in the price. Review the amount and service, "
         "then approve if everything looks correct."),
    ]
    for prefix, fill, desc in notes_guide:
        _write(r, 1, prefix, bold=True, fill=fill)
        _write(r, 2, desc,   fill=fill, wrap=True)
        ws.row_dimensions[r].height = 55
        r += 1

    r += 1

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 4 — ACTION GUIDE
    # ═════════════════════════════════════════════════════════════════════════
    r = _section(r, "ACTION GUIDE  —  what each dropdown choice does")
    action_guide = [
        ("Approve",    FILL_GOOD,
         "Pipeline creates a real invoice in FTF and emails it to the client. "
         "This CANNOT be undone from the pipeline — if you approve by mistake, "
         "cancel the invoice manually in FTF."),
        ("Reject",     FILL_BAD,
         "Order is marked rejected. No invoice is created. No email is sent to the client. "
         "The order remains in FTF with ng_invoice_needed=1 — manually clear that flag in FTF "
         "if the order should not be re-picked-up."),
        ("On-hold",    FILL_WARN,
         "Pipeline pauses the order and does not process it. The row stays in the sheet. "
         "Come back to it later — change Action to Approve or Reject when ready."),
        ("(leave blank)", FILL_ALT,
         "Pipeline ignores this row on every 30-minute cycle until you select an action."),
    ]
    for action, fill, desc in action_guide:
        _write(r, 1, action, bold=True, fill=fill)
        _write(r, 2, desc,   fill=fill, wrap=True)
        ws.row_dimensions[r].height = 50
        r += 1

    r += 1

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 5 — PIPELINE FLOW
    # ═════════════════════════════════════════════════════════════════════════
    r = _section(r, "ORDER PIPELINE FLOW  (runs automatically every 30 minutes via GitHub Actions)")
    flow_steps = [
        ("A1 — Flag Hunter",
         "Scans FTF database for orders with ng_invoice_needed = 1. Adds new orders to the pipeline queue."),
        ("A2 — Data Collector",
         "Collects data from FTF API, client emails, county property appraiser, and aerial imagery. "
         "Uses Claude AI to build a structured order packet."),
        ("A3 — Invoice Compiler",
         "Detects condos (hard stop). Prices the order using FTF pricing history and negotiated rates. "
         "Posts the row to this Excel sheet for your review. If AI cannot price → marks MANUAL PRICING REQUIRED."),
        ("A4 — Human Gate",
         "Reads your Action decision from this sheet every 30 minutes. Routes to A5 (approve) or "
         "marks rejected/on-hold."),
        ("A5 — Invoice Finalizer",
         "Creates the actual invoice in FTF (real record in the system). Retrieves the pay link."),
        ("A6 — Email Sender",
         "Emails the invoice and pay link to the client. All emails currently redirect to "
         "ai@nexgen.enterprises during staging (EMAIL_OVERRIDE_ALL active)."),
        ("A7 — Feedback Learner",
         "Learns from approved/rejected decisions to improve future pricing accuracy."),
    ]
    for i, (step, desc) in enumerate(flow_steps):
        fill = FILL_ALT if i % 2 == 0 else None
        _write(r, 1, step, bold=True, fill=fill)
        _write(r, 2, desc, fill=fill, wrap=True)
        ws.row_dimensions[r].height = 35
        r += 1

    r += 1

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 6 — PIPELINE STATUS DEFINITIONS
    # ═════════════════════════════════════════════════════════════════════════
    r = _section(r, "PIPELINE STATUS DEFINITIONS  (internal — for reference)")
    statuses = [
        ("invoice_needed",      "Order picked up from FTF — queued for A2 data collection."),
        ("data_collected",      "A2 collected all data — ready for A3 pricing and Excel posting."),
        ("invoice_draft_posted","AI priced and posted to this Excel sheet — awaiting your action."),
        ("pricing_needed",      "AI could not price this order. Row posted to Excel — enter amount manually."),
        ("condo_rejected",      "Condo detected — cannot survey. Posted to Excel as auto-rejected. Contact client."),
        ("invoice_approved",    "You approved — pipeline is creating the FTF invoice (A5 running)."),
        ("invoice_sent",        "Invoice created in FTF and emailed to client (A6 complete)."),
        ("invoice_rejected",    "You rejected (or auto-rejected: condo). No invoice created or sent."),
        ("on_hold",             "You selected On-hold. Pipeline is paused for this order."),
        ("details_missing",     "FTF has insufficient data (blank service field + no notes). Pipeline cannot process. "
                                "Update the order in FTF or handle manually."),
        ("permanently_excluded", "Order will never be processed — e.g., canceled in FTF, internal routing email. Skipped forever."),
    ]
    for i, (status, desc) in enumerate(statuses):
        fill = FILL_ALT if i % 2 == 0 else None
        _write(r, 1, status, bold=True, fill=fill)
        _write(r, 2, desc,   fill=fill, wrap=True)
        ws.row_dimensions[r].height = 30
        r += 1

    r += 1

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION 7 — HOW TO TEACH THE AI (PRICING RULES)
    # ═════════════════════════════════════════════════════════════════════════
    r = _section(r, "HOW TO TEACH THE AI  —  'Pricing Rules' tab")
    teaching_rows = [
        ("What it is",
         FILL_GOOD,
         "The 'Pricing Rules' tab is your direct line to teach the AI how to price orders. "
         "Any rule you add there is applied on the NEXT pipeline run — no coding needed."),
        ("When to use it",
         FILL_ALT,
         "Use it when: (1) You know the correct price for a specific client or service. "
         "(2) The AI keeps getting a price wrong. (3) You have a negotiated flat rate for a client. "
         "(4) You want to override AI pricing for a specific county."),
        ("How to add a rule",
         FILL_ALT,
         "Go to the 'Pricing Rules' tab → add a new row → set Status = Active → fill in patterns → save. "
         "Use * as a wildcard (matches anything). Examples:\n"
         "  Boundary Survey | Hillsborough | Hillsborough Title | $550 | priority 1\n"
         "  * | * | CDS-Commercial | $450 | priority 5  (all CDS orders)"),
        ("Priority",
         FILL_WARN,
         "Lower number = higher priority. If two rules match, the one with the lower Priority wins. "
         "Keep client-specific rules at priority 1-10. County/service rules at 50+. Global fallbacks at 999."),
        ("Service & Client patterns",
         FILL_ALT,
         "Patterns are substring matches (not exact). 'Boundary' matches 'Boundary Survey'. "
         "'Title' matches 'Hillsborough Title', 'Southern Title', etc. "
         "Set to * to match any value."),
        ("Price = 0 means no override",
         FILL_WARN,
         "If Price is 0, the rule matches but the AI still sets the price (useful for testing pattern logic). "
         "Set a non-zero price to actually override the AI."),
    ]
    for label, fill, desc in teaching_rows:
        _write(r, 1, label, bold=True, fill=fill)
        _write(r, 2, desc,  fill=fill, wrap=True)
        ws.row_dimensions[r].height = 55
        r += 1

    # ── Upload ────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    try:
        _upload_workbook_bytes(buf.read())
        log.info("guide sheet '%s' written (%s)", GUIDE_SHEET_NAME, _GUIDE_VERSION)
    except Exception as exc:
        log.warning("guide sheet upload failed (non-fatal): %s", exc)


def auto_reject_condo_row(order_id: str) -> None:
    """Set Action = 'Reject' and Processed At on the condo row in the approval table.

    Called immediately after append_approval_row for condo orders so the row is
    auto-rejected without waiting for a human to click the dropdown.
    A4 will see Processed At is already filled and skip re-processing.
    """
    try:
        ensure_approval_sheet()
        r = httpx.get(
            f"{_wb_base()}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
            headers=_session_headers(),
            timeout=15.0,
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
            log.warning("auto_reject_condo_row: order %s not found in Excel table", order_id)
            return

        excel_row  = target_index + 2   # 0-based table index + header + 1
        action_col = chr(ord("A") + _COL_ACTION)        # "J"
        proc_col   = chr(ord("A") + _COL_PROCESSED_AT)  # "M"
        stamped_at = datetime.now(_EASTERN).strftime("%Y-%m-%d %H:%M %Z")
        wb_b       = _wb_base()
        h          = _session_headers()

        # Update Action and Processed At in separate calls — they are not adjacent
        # (Notes and Posted At columns sit between them and must NOT be overwritten).
        httpx.patch(
            f"{wb_b}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='{action_col}{excel_row}')",
            headers=h, json={"values": [["Reject"]]}, timeout=10.0,
        ).raise_for_status()
        httpx.patch(
            f"{wb_b}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='{proc_col}{excel_row}')",
            headers=h, json={"values": [[stamped_at]]}, timeout=10.0,
        ).raise_for_status()

        log.info("auto_reject_condo_row: order %s auto-rejected in Excel row %d", order_id, excel_row)
    except Exception as exc:
        log.warning("auto_reject_condo_row failed order=%s (non-fatal): %s", order_id, exc)


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


def get_all_approval_order_ids() -> set:
    """Return ALL order IDs already in the approval table regardless of action status.

    Used by backfill scripts to avoid writing duplicate rows for orders that were
    already posted (e.g. condo_rejected rows with Action=Reject already filled).
    """
    try:
        ensure_approval_sheet()
        r = httpx.get(
            f"{_wb_base()}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
            headers=_session_headers(),
            timeout=15.0,
        )
        r.raise_for_status()
        ids = set()
        for row in r.json().get("value", []):
            vals = row.get("values", [[]])[0]
            if vals:
                ids.add(str(vals[0]).strip())
        log.info("get_all_approval_order_ids: %d total rows in Excel", len(ids))
        return ids
    except Exception as exc:
        log.warning("get_all_approval_order_ids failed: %s", exc)
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


def _format_new_row(table_row_index: int, ftf_link: str = "") -> None:
    """Apply thin borders, currency format, and clickable FTF hyperlink to a newly added row."""
    excel_row = table_row_index + 2  # 0-based table index + header row + 1
    row_range = f"A{excel_row}:{_END_COL}{excel_row}"
    wb = _wb_base()
    h  = _session_headers()

    for side in ["EdgeTop", "EdgeBottom", "EdgeLeft", "EdgeRight", "InsideVertical"]:
        httpx.patch(
            f"{wb}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='{row_range}')/format/borders/{side}",
            headers=h,
            json={"style": "Continuous", "weight": "Thin", "color": "#000000"},
            timeout=10.0,
        ).raise_for_status()

    httpx.patch(
        f"{wb}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='F{excel_row}')/format",
        headers=h,
        json={"numberFormat": [["$#,##0.00"]]},
        timeout=10.0,
    ).raise_for_status()

    if ftf_link and ftf_link.startswith("http"):
        httpx.patch(
            f"{wb}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='I{excel_row}')",
            headers=h,
            json={"formulas": [[f'=HYPERLINK("{ftf_link}","View Order")']]},
            timeout=10.0,
        ).raise_for_status()

    log.debug("row %d formatted (borders + currency + hyperlink)", excel_row)


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
        posted_at = datetime.now(_EASTERN).strftime("%Y-%m-%d %H:%M %Z")

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

    # Apply borders, currency format, and hyperlink to the new row
    try:
        new_index = r.json().get("index")   # 0-based table row index
        if new_index is not None:
            _format_new_row(new_index, ftf_link=ftf_link)
    except Exception as exc:
        log.warning("row formatting failed (non-fatal) order_id=%s: %s", order_id, exc)


_ACTION_NORMALIZE = {
    "approve": "approve",
    "reject":  "reject",
    "on-hold": "hold",
    "on hold": "hold",
    "hold":    "hold",
}


def get_pending_approvals() -> list[dict]:
    """Return rows where Action is set (Approve/Reject/On-hold) and Processed At is empty.

    Used by the Excel Approval Watcher to pick up decisions made in the spreadsheet
    without needing Power Automate or any external trigger.

    Returns list of dicts: {order_id, action (normalized), notes}
    """
    ensure_approval_sheet()
    r = httpx.get(
        f"{_wb_base()}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=_session_headers(),
        timeout=15.0,
    )
    r.raise_for_status()

    results = []
    for row in r.json().get("value", []):
        vals = row.get("values", [[]])[0]
        if len(vals) < _COL_COUNT:
            vals = list(vals) + [""] * (_COL_COUNT - len(vals))

        order_id     = str(vals[0]).strip()
        action_raw   = str(vals[_COL_ACTION]).strip()
        processed_at = str(vals[_COL_PROCESSED_AT]).strip()
        notes        = str(vals[10]).strip()   # col K

        if not order_id or not action_raw or processed_at:
            continue   # blank action or already processed

        action_norm = _ACTION_NORMALIZE.get(action_raw.lower())
        if not action_norm:
            continue   # unrecognised value in Action column

        results.append({"order_id": order_id, "action": action_norm, "notes": notes})

    log.info("get_pending_approvals: %d pending decisions found", len(results))
    return results


def mark_row_processed(order_id: str) -> None:
    """Set Processed At timestamp on the most recent blank-Action row matching order_id."""
    base = _wb_base()
    h    = _session_headers()

    r = httpx.get(
        f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=h, timeout=15.0,
    )
    r.raise_for_status()
    processed_at = datetime.now(_EASTERN).strftime("%Y-%m-%d %H:%M %Z")

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
