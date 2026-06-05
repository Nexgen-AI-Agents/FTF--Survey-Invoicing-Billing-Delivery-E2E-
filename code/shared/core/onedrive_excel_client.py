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

def _create_table(base: str, h: dict) -> None:
    """Create ApprovalTable with headers, then set up dropdown + conditional formatting."""
    range_addr = f"A1:{_END_COL}1"
    httpx.patch(
        f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='{range_addr}')",
        headers=h,
        json={"values": [APPROVAL_HEADERS]},
        timeout=15.0,
    ).raise_for_status()

    r5 = httpx.post(
        f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/add",
        headers=h,
        json={"address": f"{ONEDRIVE_SHEET_NAME}!{range_addr}", "hasHeaders": True},
        timeout=15.0,
    )
    r5.raise_for_status()
    table_id = r5.json()["id"]

    httpx.patch(
        f"{base}/tables/{table_id}",
        headers=h,
        json={"name": ONEDRIVE_TABLE_NAME},
        timeout=15.0,
    ).raise_for_status()
    log.info("created table: %s", ONEDRIVE_TABLE_NAME)

    _cache.pop("od_formatting_done", None)
    _setup_table_formatting()


def ensure_approval_sheet() -> None:
    """Create the Approvals sheet and ApprovalTable if they don't already exist.

    Also detects schema mismatch (wrong column count) and recreates the table cleanly.
    """
    base = _wb_base()
    h    = _session_headers()

    # ── Check sheet ───────────────────────────────────────────────────────────
    r = httpx.get(f"{base}/worksheets", headers=h, timeout=15.0)
    r.raise_for_status()
    existing_sheets = [s["name"] for s in r.json().get("value", [])]

    if ONEDRIVE_SHEET_NAME not in existing_sheets:
        r2 = httpx.post(f"{base}/worksheets/add", headers=h,
                         json={"name": ONEDRIVE_SHEET_NAME}, timeout=15.0)
        r2.raise_for_status()
        log.info("created worksheet: %s", ONEDRIVE_SHEET_NAME)

    # ── Check table ───────────────────────────────────────────────────────────
    r3 = httpx.get(f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables", headers=h, timeout=15.0)
    r3.raise_for_status()
    tables = {t["name"]: t for t in r3.json().get("value", [])}

    if ONEDRIVE_TABLE_NAME in tables:
        # Verify column count — if wrong schema, delete and recreate
        r_cols = httpx.get(
            f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/columns",
            headers=h, timeout=15.0,
        )
        if r_cols.is_success:
            actual_cols = len(r_cols.json().get("value", []))
            if actual_cols != _COL_COUNT:
                log.info(
                    "schema mismatch: table has %d cols, expected %d — deleting and recreating",
                    actual_cols, _COL_COUNT,
                )
                httpx.delete(
                    f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}",
                    headers=h, timeout=15.0,
                ).raise_for_status()
                _create_table(base, h)
            elif not _cache.get("od_formatting_done"):
                # Table exists with correct schema — apply formatting if not done this session
                _setup_table_formatting()
                _cache["od_formatting_done"] = True
        return

    _create_table(base, h)
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


def _setup_table_formatting() -> None:
    """Set up dropdown validation and row conditional formatting on the Approvals sheet.

    Called once after table creation. Safe to re-call — data validation is idempotent;
    conditional formats are only added if none exist yet.
    """
    base  = _wb_base()
    h     = _session_headers()
    sheet = ONEDRIVE_SHEET_NAME
    # Action column letter (A=0 → J=9)
    action_col   = chr(ord("A") + _COL_ACTION)          # "J"
    action_range = f"{action_col}2:{action_col}10000"
    full_range   = f"A2:{_END_COL}10000"

    # ── 1. Dropdown validation on Action column ───────────────────────────────
    try:
        rv = httpx.patch(
            f"{base}/worksheets/{sheet}/range(address='{action_range}')/dataValidation",
            headers=h,
            json={
                "rule": {
                    "list": {
                        "source": "Approve,Reject,On-hold",
                        "showDropDown": False,   # False = SHOW dropdown (Excel API inverted)
                    }
                },
                "showErrorAlert": False,
                "showInputMessage": False,
            },
            timeout=15.0,
        )
        if rv.is_success:
            log.info("dropdown validation set: %s → Approve/Reject/On-hold", action_range)
        else:
            log.warning("dropdown validation failed %s: %s", rv.status_code, rv.text[:200])
    except Exception as exc:
        log.warning("dropdown validation setup error: %s", exc)

    # ── 2. Conditional formatting — row color per action ─────────────────────
    # Check how many custom conditional formats already exist
    try:
        rc = httpx.get(
            f"{base}/worksheets/{sheet}/range(address='{full_range}')/conditionalFormats",
            headers=h, timeout=15.0,
        )
        existing_cf = rc.json().get("value", []) if rc.is_success else []
    except Exception:
        existing_cf = []

    if len(existing_cf) >= len(_ACTION_COLORS):
        log.info("conditional formats already set (%d rules) — skipping", len(existing_cf))
        return

    for action_val, fill_hex in _ACTION_COLORS.items():
        try:
            # Add a Custom formula-based conditional format on the full row range
            r_add = httpx.post(
                f"{base}/worksheets/{sheet}/range(address='{full_range}')/conditionalFormats/add",
                headers=h,
                json={"type": "Custom"},
                timeout=15.0,
            )
            if not r_add.is_success:
                log.warning("CF add failed for %s: %s %s", action_val, r_add.status_code, r_add.text[:150])
                continue
            cf_id = r_add.json().get("id", "")

            # Set the formula rule
            formula = f'=${action_col}2="{action_val}"'
            r_rule = httpx.patch(
                f"{base}/worksheets/{sheet}/conditionalFormats/{cf_id}/customOrNullObject",
                headers=h,
                json={"rule": {"formula": formula}},
                timeout=15.0,
            )
            # Set the fill color
            r_fill = httpx.patch(
                f"{base}/worksheets/{sheet}/conditionalFormats/{cf_id}/format/fill",
                headers=h,
                json={"color": fill_hex},
                timeout=15.0,
            )
            if r_rule.is_success and r_fill.is_success:
                log.info("conditional format: %s → %s", action_val, fill_hex)
            else:
                log.warning("CF rule/fill failed for %s: rule=%s fill=%s",
                            action_val, r_rule.status_code, r_fill.status_code)
        except Exception as exc:
            log.warning("conditional format setup error for %s: %s", action_val, exc)


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
