"""
teams_graph_client.py — Microsoft Graph API client for Teams messaging.

Uses Azure AD app credentials (client_credentials / app-only flow) to:
  - Send rich messages to the FTF-Approvals channel
  - Poll the channel for APPROVE / REJECT commands from Robert / Ryan

No public URL. No webhook. No Flask server. No ngrok.
Token is cached in memory and auto-refreshed.

Azure AD app: FTF Estimate Bot
  App ID:    TEAMS_APP_ID  (7369cb84-...)
  Tenant ID: TEAMS_TENANT_ID
  Secret:    TEAMS_CLIENT_SECRET

Required application permissions (admin consent in portal.azure.com):
  - ChannelMessage.Send
  - ChannelMessage.Read.All

Required env vars:
  TEAMS_TENANT_ID, TEAMS_APP_ID, TEAMS_CLIENT_SECRET,
  TEAMS_TEAM_ID, TEAMS_CHANNEL_ID
"""

import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from config.settings import (
    TEAMS_APP_ID,
    TEAMS_CHANNEL_ID,
    TEAMS_CLIENT_SECRET,
    TEAMS_TEAM_ID,
    TEAMS_TENANT_ID,
)
from core.exceptions import AgentError
from core.logger import get_logger

log = get_logger("teams_graph_client")

# Microsoft Graph uses the beta endpoint for ChannelMessage.Send (app-only)
_GRAPH_SEND = "https://graph.microsoft.com/beta"
_GRAPH_READ = "https://graph.microsoft.com/v1.0"
_TOKEN_URL  = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_SCOPE      = "https://graph.microsoft.com/.default"

# Simple in-memory token cache (process lifetime)
_cache: dict[str, Any] = {}

# Strip HTML tags from raw Teams message body
_HTML_RE    = re.compile(r"<[^>]+>", re.IGNORECASE)
_MENTION_RE = re.compile(r"<at[^>]*>.*?</at>", re.IGNORECASE | re.DOTALL)


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_token() -> str:
    """Return a valid Bearer token, refreshing if within 60 s of expiry."""
    now = time.monotonic()
    if _cache.get("token") and _cache.get("exp", 0) > now + 60:
        return _cache["token"]

    if not all([TEAMS_TENANT_ID, TEAMS_APP_ID, TEAMS_CLIENT_SECRET]):
        raise AgentError(
            "Teams Graph API not configured — set TEAMS_TENANT_ID, TEAMS_APP_ID, "
            "TEAMS_CLIENT_SECRET in .env"
        )

    try:
        r = httpx.post(
            _TOKEN_URL.format(tenant=TEAMS_TENANT_ID),
            data={
                "grant_type":    "client_credentials",
                "client_id":     TEAMS_APP_ID,
                "client_secret": TEAMS_CLIENT_SECRET,
                "scope":         _SCOPE,
            },
            timeout=15.0,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"Teams token request failed: HTTP {exc.response.status_code} — "
            f"{exc.response.text[:200]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"Teams token request failed: {exc}") from exc

    data = r.json()
    _cache["token"] = data["access_token"]
    _cache["exp"]   = now + int(data.get("expires_in", 3600))
    log.debug("teams token refreshed expires_in=%s", data.get("expires_in"))
    return _cache["token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


# ── Send ──────────────────────────────────────────────────────────────────────

def send_channel_message(html_content: str, subject: str = "") -> dict:
    """Post an HTML message to the FTF-Approvals Teams channel.

    html_content — HTML body (Teams renders: <b>, <i>, <a>, <ul>, <li>, <br>, <pre>)
    subject      — optional card title displayed above the message
    Returns the created message dict from Graph API.
    Raises AgentError on auth or send failure.
    """
    if not all([TEAMS_TEAM_ID, TEAMS_CHANNEL_ID]):
        raise AgentError("TEAMS_TEAM_ID and TEAMS_CHANNEL_ID must be set in .env")

    url     = f"{_GRAPH_SEND}/teams/{TEAMS_TEAM_ID}/channels/{TEAMS_CHANNEL_ID}/messages"
    payload: dict[str, Any] = {"body": {"contentType": "html", "content": html_content}}
    if subject:
        payload["subject"] = subject

    try:
        r = httpx.post(url, json=payload, headers=_headers(), timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"Teams message send failed: HTTP {exc.response.status_code} — "
            f"{exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"Teams message send failed: {exc}") from exc

    msg_id = r.json().get("id", "?")
    log.info("teams message sent id=%s channel=%s", msg_id, TEAMS_CHANNEL_ID)
    return r.json()


def send_confirmation(text: str, color: str = "green") -> None:
    """Send a short confirmation or error reply to the approval channel.

    color: "green" (approval OK), "red" (error/reject), "orange" (warning)
    """
    color_map = {"green": "#00CC00", "red": "#CC0000", "orange": "#FF6600"}
    hex_color = color_map.get(color, "#0078D7")
    html = f'<p style="color:{hex_color}"><b>{text}</b></p>'
    try:
        send_channel_message(html)
    except AgentError as exc:
        log.warning("confirmation send failed: %s", exc)


# ── Poll for approvals ────────────────────────────────────────────────────────

def get_recent_messages(limit: int = 50) -> list[dict]:
    """Fetch the most recent messages from the approval channel.

    Returns list of dicts:
      {id, sender, sender_is_app, text, created_at_dt}

    Filters out messages sent BY this bot app to avoid processing our own messages.
    """
    if not all([TEAMS_TEAM_ID, TEAMS_CHANNEL_ID]):
        raise AgentError("TEAMS_TEAM_ID and TEAMS_CHANNEL_ID must be set in .env")

    url = (
        f"{_GRAPH_READ}/teams/{TEAMS_TEAM_ID}/channels/{TEAMS_CHANNEL_ID}/messages"
        f"?$top={limit}"
    )
    try:
        r = httpx.get(url, headers=_headers(), timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"Teams message fetch failed: HTTP {exc.response.status_code} — "
            f"{exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"Teams message fetch failed: {exc}") from exc

    results: list[dict] = []
    for msg in r.json().get("value", []):
        from_obj  = msg.get("from") or {}
        app_ref   = from_obj.get("application") or {}
        user_ref  = from_obj.get("user") or {}

        # Skip our own bot messages
        if app_ref.get("id") == TEAMS_APP_ID:
            continue

        sender_name  = (
            user_ref.get("displayName")
            or app_ref.get("displayName")
            or "Unknown"
        )
        sender_is_app = bool(app_ref)

        raw_body = (msg.get("body") or {}).get("content", "")
        plain    = _clean_message_body(raw_body)

        created_raw = msg.get("createdDateTime", "")
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            created_dt = datetime.now(timezone.utc)

        results.append({
            "id":            msg.get("id", ""),
            "sender":        sender_name,
            "sender_is_app": sender_is_app,
            "text":          plain,
            "created_at_dt": created_dt,
        })

    return results


def check_for_approvals(since: datetime | None = None) -> list[dict]:
    """Return parsed APPROVE / REJECT commands posted since `since` (UTC).

    Each returned dict:
      {action, order_id, reason, sender, message_id, created_at_dt}

    action values:
      "approve"     — approve one specific order
      "approve_all" — approve everything pending
      "reject"      — reject one specific order
    """
    messages = get_recent_messages(limit=50)
    commands: list[dict] = []

    for msg in messages:
        if since and msg["created_at_dt"] <= since:
            continue

        action, order_id, reason = _parse_command(msg["text"])
        if action == "unknown":
            continue

        commands.append({
            "action":        action,
            "order_id":      order_id,
            "reason":        reason,
            "sender":        msg["sender"],
            "message_id":    msg["id"],
            "created_at_dt": msg["created_at_dt"],
        })
        log.info(
            "approval command found action=%s order_id=%s sender=%s",
            action, order_id, msg["sender"],
        )

    return commands


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_message_body(html: str) -> str:
    """Strip @mention tags and all HTML to get plain command text."""
    text = _MENTION_RE.sub(" ", html)   # remove <at>...</at> blocks entirely
    text = _HTML_RE.sub(" ", text)       # strip remaining HTML tags
    return " ".join(text.split())        # collapse whitespace


def _parse_command(text: str) -> tuple[str, str | None, str | None]:
    """Parse APPROVE / APPROVE ALL / REJECT from plain Teams message text.

    Searches for the keyword anywhere in the text (handles @mention prefix).

    Returns (action, order_id, reason):
      action   — "approve" | "approve_all" | "reject" | "unknown"
      order_id — order ID string or None
      reason   — rejection reason string or None
    """
    upper = text.upper()

    approve_m = re.search(r"\bAPPROVE\b", upper)
    reject_m  = re.search(r"\bREJECT\b",  upper)

    if approve_m:
        after  = text[approve_m.end():].strip()
        tokens = after.split(None, 1)
        if not tokens:
            return "unknown", None, None
        if tokens[0].upper() == "ALL":
            return "approve_all", None, None
        return "approve", tokens[0], None

    if reject_m:
        after  = text[reject_m.end():].strip()
        tokens = after.split(None, 1)
        if not tokens:
            return "unknown", None, None
        reason = tokens[1] if len(tokens) == 2 else None
        return "reject", tokens[0], reason

    return "unknown", None, None


# ── Convenience builders ──────────────────────────────────────────────────────

def build_digest_html(orders: list[dict], ftf_order_url: str) -> str:
    """Build the hourly approval digest HTML for Teams.

    orders — list of order dicts with keys:
      order_id, service_type, estimate_amount, flag_reason, status, flagged_at
    ftf_order_url — base URL for clickable order links
    """
    from datetime import datetime as _dt
    now = datetime.now(timezone.utc)

    rows_html = ""
    for rec in orders:
        oid        = rec["order_id"]
        amount     = rec.get("estimate_amount")
        amount_str = f"${float(amount):,.2f}" if amount else "TBD"
        age_str    = ""
        if rec.get("flagged_at"):
            try:
                fa = _dt.fromisoformat(str(rec["flagged_at"]))
                if fa.tzinfo is None:
                    fa = fa.replace(tzinfo=timezone.utc)
                age_h   = int((now - fa).total_seconds() / 3600)
                age_str = f"{age_h}h ago"
            except Exception:
                pass
        link        = f"{ftf_order_url}/{oid}"
        flag_reason = (rec.get("flag_reason") or "see order")[:60]
        service     = rec.get("service_type") or "Unknown"
        status      = rec.get("status") or ""
        rows_html += (
            f"<tr>"
            f"<td><a href='{link}'>{oid}</a></td>"
            f"<td>{service}</td>"
            f"<td>{amount_str}</td>"
            f"<td>{flag_reason}</td>"
            f"<td>{status}</td>"
            f"<td>{age_str}</td>"
            f"</tr>"
        )

    count   = len(orders)
    plural  = "s" if count != 1 else ""
    return f"""
<h2>FTF Estimates Pending Review — {count} order{plural}</h2>
<p><b>@Robert @Ryan — please review and approve/deny the following estimates:</b></p>
<table>
  <tr>
    <th>Order</th><th>Service</th><th>Amount</th>
    <th>Flag Reason</th><th>Status</th><th>Age</th>
  </tr>
  {rows_html}
</table>
<br>
<p><b>Reply in this channel to take action:</b></p>
<ul>
  <li><code>APPROVE 1000276115</code> — approve one estimate for sending</li>
  <li><code>APPROVE ALL</code> — approve everything in this list</li>
  <li><code>REJECT 1000276115 wrong county</code> — reject and hold</li>
</ul>
<p><i>The bot reads this channel every hour and processes your replies automatically.</i></p>
""".strip()
