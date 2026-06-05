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
    "Order ID", "Client Name", "Property Address", "Service",
    "Amount", "Confidence", "Escalate", "FTF Link",
    "Status", "Notes", "Posted At", "Processed At",
]
_COL_COUNT = len(APPROVAL_HEADERS)
_END_COL   = chr(ord("A") + _COL_COUNT - 1)   # "L"


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

def ensure_approval_sheet() -> None:
    """Create the Approvals sheet and ApprovalTable if they don't already exist."""
    base = _wb_base()
    h    = _session_headers()

    # Check sheets
    r = httpx.get(f"{base}/worksheets", headers=h, timeout=15.0)
    r.raise_for_status()
    existing_sheets = [s["name"] for s in r.json().get("value", [])]

    if ONEDRIVE_SHEET_NAME not in existing_sheets:
        r2 = httpx.post(f"{base}/worksheets/add", headers=h,
                         json={"name": ONEDRIVE_SHEET_NAME}, timeout=15.0)
        r2.raise_for_status()
        log.info("created worksheet: %s", ONEDRIVE_SHEET_NAME)

    # Check tables
    r3 = httpx.get(f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables", headers=h, timeout=15.0)
    r3.raise_for_status()
    existing_tables = [t["name"] for t in r3.json().get("value", [])]

    if ONEDRIVE_TABLE_NAME not in existing_tables:
        # Write headers to A1:L1
        range_addr = f"A1:{_END_COL}1"
        httpx.patch(
            f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/range(address='{range_addr}')",
            headers=h,
            json={"values": [APPROVAL_HEADERS]},
            timeout=15.0,
        ).raise_for_status()

        # Convert range to table
        r5 = httpx.post(
            f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/add",
            headers=h,
            json={"address": f"{ONEDRIVE_SHEET_NAME}!{range_addr}", "hasHeaders": True},
            timeout=15.0,
        )
        r5.raise_for_status()
        table_id = r5.json()["id"]

        # Rename to known name
        httpx.patch(
            f"{base}/tables/{table_id}",
            headers=h,
            json={"name": ONEDRIVE_TABLE_NAME},
            timeout=15.0,
        ).raise_for_status()
        log.info("created table: %s", ONEDRIVE_TABLE_NAME)


# ── Public write API ──────────────────────────────────────────────────────────

def append_approval_row(
    order_id:    str,
    client_name: str,
    address:     str,
    service:     str,
    amount:      float,
    confidence:  str,
    escalate:    bool,
    ftf_link:    str,
    posted_at:   Optional[str] = None,
) -> None:
    """Append a new Pending row to the approval table."""
    ensure_approval_sheet()

    if not posted_at:
        posted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    values = [[
        str(order_id),
        str(client_name),
        str(address)[:120],
        str(service),
        float(amount),
        str(confidence),
        "Yes" if escalate else "No",
        str(ftf_link),
        "Pending",      # Status — user changes this to Approve/Reject/Hold
        "",             # Notes — user fills in if rejecting
        posted_at,
        "",             # Processed At — filled after pipeline runs
    ]]

    r = httpx.post(
        f"{_wb_base()}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows/add",
        headers=_session_headers(),
        json={"values": values},
        timeout=15.0,
    )
    r.raise_for_status()
    log.info("excel row appended order_id=%s amount=%.2f", order_id, amount)


def mark_row_processed(order_id: str) -> None:
    """Set Processed At timestamp on the row matching order_id."""
    base = _wb_base()
    h    = _session_headers()

    r = httpx.get(
        f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows",
        headers=h, timeout=15.0,
    )
    r.raise_for_status()
    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for row in r.json().get("value", []):
        vals = row.get("values", [[]])[0]
        if len(vals) >= 1 and str(vals[0]) == str(order_id):
            idx = row["index"]
            # Patch only Processed At (column 12, index 11)
            new_vals = list(vals) + [""] * (_COL_COUNT - len(vals))
            new_vals[11] = processed_at
            httpx.patch(
                f"{base}/worksheets/{ONEDRIVE_SHEET_NAME}/tables/{ONEDRIVE_TABLE_NAME}/rows/itemAt(index={idx})",
                headers=h,
                json={"values": [new_vals[:_COL_COUNT]]},
                timeout=15.0,
            ).raise_for_status()
            log.info("marked processed order_id=%s at=%s", order_id, processed_at)
            return

    log.warning("mark_row_processed: order_id=%s not found in Excel", order_id)
