"""
onedrive_excel_client.py — Microsoft Graph Workbook API client.

Reads/writes rows in FTF-Invoicing Agent.xlsx on nesa@nexgenlogix.com's OneDrive.
Uses Azure AD app credentials via client_credentials grant (AZURE_TENANT_ID / AZURE_APP_ID / AZURE_CLIENT_SECRET).

Required Graph permissions (application):
  Files.ReadWrite.All  — read/write files in any user's OneDrive
"""

import base64
import json
import os
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
    "Amount ($)", "Confidence", "Escalate", "FTF Link",
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
    """Create the 'Pricing Rules' tab using Graph API (no file upload — works even when Excel is open).

    This tab is user-editable. Add rows directly in Excel:
      Service Pattern | County | Client Pattern | Price ($) | Priority | Notes
      Boundary Survey | Hillsborough | Hillsborough Title | 550.00 | 1 | Standard rate
      * = wildcard (matches anything). Lower Priority = higher priority.
    """
    if _cache.get("od_pricing_rules_done"):
        return

    h    = _session_headers()
    base = _wb_base()

    r_sheets = httpx.get(f"{base}/worksheets", headers=h, timeout=15.0)
    r_sheets.raise_for_status()
    existing_sheets = [s["name"] for s in r_sheets.json().get("value", [])]

    if PRICING_RULES_SHEET_NAME in existing_sheets:
        _cache["od_pricing_rules_done"] = True
        return

    log.info("Pricing Rules tab missing — creating via Graph API")
    try:
        # 1. Create worksheet
        httpx.post(
            f"{base}/worksheets/add",
            headers=h, json={"name": PRICING_RULES_SHEET_NAME}, timeout=15.0,
        ).raise_for_status()

        # 2. Write header + seed row in one call
        end_col = chr(ord("A") + _PR_COL_COUNT - 1)
        seed_row = ["1", "Active", "*", "*", "*", 0.0, 999,
                    "EXAMPLE — delete this. Set Price=0 to keep AI pricing. * = match anything."]
        httpx.patch(
            f"{base}/worksheets/{PRICING_RULES_SHEET_NAME}/range(address='A1:{end_col}2')",
            headers=h, json={"values": [PRICING_RULES_HEADERS, seed_row]}, timeout=15.0,
        ).raise_for_status()

        # 3. Create structured table so /tables/rows reads work
        httpx.post(
            f"{base}/worksheets/{PRICING_RULES_SHEET_NAME}/tables/add",
            headers=h, json={"address": f"A1:{end_col}2", "hasHeaders": True}, timeout=15.0,
        ).raise_for_status()

        # 4. Rename the table to our known name
        r_tabs = httpx.get(
            f"{base}/worksheets/{PRICING_RULES_SHEET_NAME}/tables",
            headers=h, timeout=10.0,
        )
        if r_tabs.is_success:
            tables = r_tabs.json().get("value", [])
            if tables:
                httpx.patch(
                    f"{base}/tables/{tables[-1]['id']}",
                    headers=h, json={"name": PRICING_RULES_TABLE_NAME}, timeout=10.0,
                )

        # 5. Bold header row
        httpx.patch(
            f"{base}/worksheets/{PRICING_RULES_SHEET_NAME}/range(address='A1:{end_col}1')/format/font",
            headers=h, json={"bold": True}, timeout=10.0,
        )

        log.info("Pricing Rules tab created via Graph API")
        _cache["od_pricing_rules_done"] = True

    except Exception as exc:
        log.warning("ensure_pricing_rules_sheet failed (non-fatal): %s", exc)


# ── Pricing rules — in-memory cache + git-backed JSON file ───────────────────
_pricing_rules_cache: list | None = None

# Committed to git every pipeline run — zero OneDrive dependency for reads
_PRICING_RULES_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pricing_rules.json")
)


def _parse_rules_from_excel_rows(rows: list) -> list[dict]:
    """Parse raw Graph API table rows into rule dicts. Shared by fetch and sync."""
    rules = []
    for row in rows:
        vals = (row.get("values") or [[]])[0]
        if len(vals) < _PR_COL_COUNT:
            vals = list(vals) + [""] * (_PR_COL_COUNT - len(vals))

        if str(vals[1]).strip().lower() != "active":
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
    return rules


def get_pricing_rules() -> list[dict]:
    """Return active pricing rules, sorted by Priority (lower = higher priority).

    Read order:
      1. In-memory cache (fastest — populated by sync_pricing_rules_to_json at run start)
      2. data/pricing_rules.json (git-backed — survives OneDrive outages)
      3. OneDrive Excel API (fresh fetch — used when JSON file is absent)

    Each rule dict: {rule_id, service, county, client, price, priority, notes}
    Pattern values: '*' matches anything; otherwise case-insensitive substring match.
    """
    global _pricing_rules_cache
    if _pricing_rules_cache is not None:
        return _pricing_rules_cache

    # Try git-backed JSON file first (no API call needed)
    if os.path.exists(_PRICING_RULES_FILE):
        try:
            with open(_PRICING_RULES_FILE) as f:
                data = json.load(f)
            rules = data.get("rules", [])
            _pricing_rules_cache = rules
            log.info("get_pricing_rules: %d rules loaded from pricing_rules.json", len(rules))
            return rules
        except Exception as exc:
            log.warning("get_pricing_rules: JSON file unreadable (%s) — falling back to Excel", exc)

    # Fall back to Excel API
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

        rules = _parse_rules_from_excel_rows(r.json().get("value", []))
        _pricing_rules_cache = rules
        log.info("get_pricing_rules: %d active rules loaded from Excel", len(rules))
        return rules

    except Exception as exc:
        log.warning("get_pricing_rules failed — no rules applied: %s", exc)
        _pricing_rules_cache = []
        return []


def sync_pricing_rules_to_json() -> int:
    """Fetch latest pricing rules from Excel and write to data/pricing_rules.json.

    Called once at pipeline start (A0). Subsequent calls to get_pricing_rules()
    within the same run hit the in-memory cache — no further API calls.

    If OneDrive is unreachable, the existing pricing_rules.json (committed to git
    from the previous run) is left untouched and used as fallback.

    Returns number of active rules synced.
    """
    global _pricing_rules_cache
    # Clear cache so we force a fresh fetch from Excel
    _pricing_rules_cache = None

    try:
        ensure_pricing_rules_sheet()
        r = httpx.get(
            f"{_wb_base()}/worksheets/{PRICING_RULES_SHEET_NAME}/tables/{PRICING_RULES_TABLE_NAME}/rows",
            headers=_session_headers(),
            timeout=15.0,
        )
        if not r.is_success:
            log.warning("sync_pricing_rules_to_json: Excel read failed (%d) — keeping existing JSON", r.status_code)
            return 0

        rules = _parse_rules_from_excel_rows(r.json().get("value", []))

        os.makedirs(os.path.dirname(_PRICING_RULES_FILE), exist_ok=True)
        with open(_PRICING_RULES_FILE, "w") as f:
            json.dump({"rules": rules, "synced_at": datetime.now(_EASTERN).isoformat()}, f, indent=2)

        _pricing_rules_cache = rules
        log.info("sync_pricing_rules_to_json: %d rules synced → pricing_rules.json", len(rules))
        return len(rules)

    except Exception as exc:
        log.warning("sync_pricing_rules_to_json failed — existing JSON unchanged: %s", exc)
        return 0


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
    """Create or update the 'Pipeline Guide' tab using Graph API.

    No file download/upload — works even when Excel is open in browser or desktop.
    Version-gated: skips the write if the tab already has the current _GUIDE_VERSION.
    """
    # ── Version check — skip if already current ───────────────────────────────
    try:
        h    = _session_headers()
        base = _wb_base()
        r = httpx.get(
            f"{base}/worksheets/{GUIDE_SHEET_NAME}/range(address='B2')",
            headers=h, timeout=10.0,
        )
        if r.is_success:
            existing_version = (r.json().get("values") or [[""]])[0][0]
            if str(existing_version).strip() == _GUIDE_VERSION:
                log.debug("guide sheet already at %s — skipping update", _GUIDE_VERSION)
                return
    except Exception:
        pass

    log.info("guide sheet missing or outdated — writing %s via Graph API", _GUIDE_VERSION)

    try:
        h    = _session_headers()
        base = _wb_base()

        # Ensure worksheet exists
        r_sheets = httpx.get(f"{base}/worksheets", headers=h, timeout=15.0)
        r_sheets.raise_for_status()
        existing = [s["name"] for s in r_sheets.json().get("value", [])]

        if GUIDE_SHEET_NAME not in existing:
            httpx.post(
                f"{base}/worksheets/add",
                headers=h, json={"name": GUIDE_SHEET_NAME}, timeout=15.0,
            ).raise_for_status()
            log.info("guide sheet tab created")
        else:
            httpx.post(
                f"{base}/worksheets/{GUIDE_SHEET_NAME}/range(address='A1:B100')/clear",
                headers=h, json={"applyTo": "Contents"}, timeout=15.0,
            )

        stamp = f"{_GUIDE_VERSION} — {datetime.now(_EASTERN).strftime('%Y-%m-%d %H:%M %Z')}"
        rows = [
            ["FTF Invoice Pipeline — Field Guide", ""],
            ["Version", stamp],
            ["", ""],
            ["── COLUMN REFERENCE (Approvals tab) ──", ""],
            ["Order ID",          "Unique FTF order number. Click FTF Link to open in FieldToFinish."],
            ["Order Status",      "Current FTF status (In Progress, Complete, Field, etc.)"],
            ["Client Name",       "Client or title company who placed the order."],
            ["Property Address",  "Survey site address — the property to be surveyed."],
            ["Service",           "Survey service type. 'CONDO — Cannot Survey' = order cannot be processed."],
            ["Amount ($)",        "Invoice amount in USD. For MANUAL PRICING rows: type correct amount here before setting Action = Approve."],
            ["Confidence",        "HIGH = very likely correct. MEDIUM = reasonable estimate. LOW = AI had limited data. N/A = condo or manual pricing."],
            ["Escalate",          "Yes = AI flagged unusual order. Robert or Ryan should review before approving."],
            ["FTF Link",          "Click 'View Order' to open in FieldToFinish."],
            ["Action",            "YOUR DECISION — Approve / Reject / On-hold. Leave blank to defer. Pipeline checks every 30 min."],
            ["Notes",             "Pre-filled by pipeline with reason for escalation or required action. Read before acting."],
            ["Posted At",         "Date/time pipeline posted this row (Eastern Time)."],
            ["Processed At",      "Auto-filled when pipeline processes your decision. Once filled = complete."],
            ["", ""],
            ["── ACTION GUIDE ──", ""],
            ["Approve",           "Pipeline creates a real FTF invoice and emails client. CANNOT be undone from pipeline."],
            ["Reject",            "No invoice created. No email sent. Manually clear ng_invoice_needed=1 flag in FTF if order should not re-appear."],
            ["On-hold",           "Pipeline pauses this order. Change to Approve or Reject when ready."],
            ["(leave blank)",     "Pipeline ignores this row every 30-min cycle until you select an action."],
            ["", ""],
            ["── NOTES FIELD GUIDE ──", ""],
            ["CONDO ORDER —",             "Cannot survey. Row is AUTO-REJECTED. Contact client — arrange refund or redirect to interior measurement."],
            ["MANUAL PRICING REQUIRED —", "AI could not price. Enter correct amount in Amount ($) cell, then set Action = Approve."],
            ["ESCALATE —",               "Unusual order (large lot, commercial, FEMA zone, duplicate). Get Robert or Ryan to review."],
            ["(empty notes)",             "Standard order. AI is confident. Review amount and service, then approve if correct."],
            ["", ""],
            ["── HOW TO TEACH THE AI — Pricing Rules tab ──", ""],
            ["What it is",     "The 'Pricing Rules' tab sets fixed prices for specific clients, counties, or service types. No coding required."],
            ["When to use it", "Use when: AI keeps getting a price wrong, you have a negotiated flat rate for a client, or you know the correct price."],
            ["How to add a rule", "Go to 'Pricing Rules' tab → add a row → Status=Active → fill in patterns → save. * = wildcard (matches anything)."],
            ["Example",        "Boundary Survey | Hillsborough | Hillsborough Title | $550 | priority 1"],
            ["Priority",       "Lower number = higher priority. Client-specific: 1-10. County/service: 50+. Global: 999."],
            ["Price = 0",      "If Price is 0, rule matches but AI still sets the price. Set non-zero to override AI."],
            ["", ""],
            ["── PIPELINE STATUS DEFINITIONS ──", ""],
            ["invoice_needed",        "Order picked up from FTF — queued for A2 data collection."],
            ["data_collected",        "A2 collected all data — ready for A3 pricing and Excel posting."],
            ["invoice_draft_posted",  "AI priced and posted to this sheet — awaiting your action."],
            ["pricing_needed",        "AI could not price. Row posted — enter amount manually."],
            ["condo_rejected",        "Condo detected — cannot survey. Posted as auto-rejected. Contact client."],
            ["invoice_approved",      "You approved — pipeline creating FTF invoice (A5 running)."],
            ["invoice_sent",          "Invoice created in FTF and emailed to client (A6 complete)."],
            ["invoice_rejected",      "Rejected (or auto-rejected: condo). No invoice created or sent."],
            ["on_hold",               "You selected On-hold. Pipeline paused for this order."],
            ["details_missing",       "FTF has insufficient data. Update in FTF or handle manually."],
            ["permanently_excluded",  "Order will never be processed — canceled in FTF, internal email, etc."],
            ["", ""],
            ["── PIPELINE FLOW (every 30 min via GitHub Actions) ──", ""],
            ["A1 — Flag Hunter",      "Scans FTF DB for orders with ng_invoice_needed=1. Queues new orders."],
            ["A2 — Data Collector",   "Collects FTF API, emails, county appraiser, aerial image. AI builds order packet."],
            ["A3 — Invoice Compiler", "Detects condos. Checks Pricing Rules tab first. Then AI pricing. Posts to this sheet."],
            ["A4 — Human Gate",       "Reads your Action decision every 30 min. Routes to A5 (approve) or rejected/on-hold."],
            ["A5 — Invoice Finalizer","Creates real FTF invoice. Retrieves pay link."],
            ["A6 — Email Sender",     "Emails invoice and pay link. Redirects to ai@nexgen.enterprises during staging."],
            ["A7 — Feedback Learner", "Learns from decisions to improve future pricing."],
        ]

        end_row = len(rows)
        httpx.patch(
            f"{base}/worksheets/{GUIDE_SHEET_NAME}/range(address='A1:B{end_row}')",
            headers=h, json={"values": rows}, timeout=30.0,
        ).raise_for_status()

        # Bold the section header rows (lines starting with "──")
        section_rows = [i + 1 for i, row in enumerate(rows) if str(row[0]).startswith("──")]
        for sr in section_rows:
            try:
                httpx.patch(
                    f"{base}/worksheets/{GUIDE_SHEET_NAME}/range(address='A{sr}:B{sr}')/format/font",
                    headers=h, json={"bold": True}, timeout=10.0,
                )
            except Exception:
                pass

        # Title row bold + larger font
        try:
            httpx.patch(
                f"{base}/worksheets/{GUIDE_SHEET_NAME}/range(address='A1:B1')/format/font",
                headers=h, json={"bold": True, "size": 14}, timeout=10.0,
            )
        except Exception:
            pass

        log.info("guide sheet '%s' written via Graph API (%s)", GUIDE_SHEET_NAME, _GUIDE_VERSION)

    except Exception as exc:
        log.warning("guide sheet write failed (non-fatal): %s", exc)



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
