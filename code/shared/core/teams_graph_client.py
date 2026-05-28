"""
teams_graph_client.py — Microsoft Teams client (hybrid architecture).

SEND  -> Teams Workflows incoming webhook (TEAMS_INCOMING_WEBHOOK_URL)
         Adaptive Card POST. No app installation. No migration permissions needed.
         Setup: Teams channel -> Workflows -> "Post to a channel when a webhook
         request is received" -> copy the URL to TEAMS_INCOMING_WEBHOOK_URL in .env

READ  -> Microsoft Graph API ChannelMessage.Read.All (application permission)
         Polls channel for APPROVE / REJECT commands from Robert / Ryan.
         Application permission granted; admin consent confirmed 2026-05-28.

Why hybrid:
  ChannelMessage.Send as Application permission requires Teamwork.Migrate.All
  (Teams Migration API only). Workflows webhook is the official Microsoft path
  for app-to-channel posting without a Bot Framework registration.

Required env vars:
  TEAMS_INCOMING_WEBHOOK_URL  -- from Teams Workflows setup (for sending)
  TEAMS_TENANT_ID             -- Azure AD tenant ID (for reading)
  TEAMS_APP_ID                -- Azure AD app client ID (for reading)
  TEAMS_CLIENT_SECRET         -- Azure AD app secret (for reading)
  TEAMS_TEAM_ID               -- Teams group ID (for reading)
  TEAMS_CHANNEL_ID            -- Teams channel ID (for reading)
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
    TEAMS_INCOMING_WEBHOOK_URL,
    TEAMS_TEAM_ID,
    TEAMS_TENANT_ID,
)
from core.exceptions import AgentError
from core.logger import get_logger

log = get_logger("teams_graph_client")

_GRAPH_READ = "https://graph.microsoft.com/v1.0"
_TOKEN_URL  = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_SCOPE      = "https://graph.microsoft.com/.default"

_cache: dict[str, Any] = {}

_HTML_RE    = re.compile(r"<[^>]+>", re.IGNORECASE)
_MENTION_RE = re.compile(r"<at[^>]*>.*?</at>", re.IGNORECASE | re.DOTALL)


# ── Auth (for READ) ───────────────────────────────────────────────────────────

def _get_token() -> str:
    """Return a valid client_credentials Bearer token, refreshing when near expiry."""
    now = time.monotonic()
    if _cache.get("token") and _cache.get("exp", 0) > now + 60:
        return _cache["token"]

    if not all([TEAMS_TENANT_ID, TEAMS_APP_ID, TEAMS_CLIENT_SECRET]):
        raise AgentError(
            "Teams Graph API not configured -- set TEAMS_TENANT_ID, TEAMS_APP_ID, "
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
            f"Teams token request failed: HTTP {exc.response.status_code} -- "
            f"{exc.response.text[:200]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"Teams token request failed: {exc}") from exc

    data = r.json()
    _cache["token"] = data["access_token"]
    _cache["exp"]   = now + int(data.get("expires_in", 3600))
    log.debug("teams token refreshed expires_in=%s", data.get("expires_in"))
    return _cache["token"]


def _read_headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


# ── Send (via Workflows webhook) ──────────────────────────────────────────────

def send_channel_message(text_or_html: str, subject: str = "") -> dict:
    """Post a message to the FTF-Approvals channel via Workflows incoming webhook.

    Uses TEAMS_INCOMING_WEBHOOK_URL (set up via Teams channel -> Workflows).
    text_or_html -- message body; HTML tags are stripped for Adaptive Card rendering.
    subject      -- optional bold title shown above the message body.
    Returns {"ok": True, "method": "webhook"} on success.
    Raises AgentError if webhook URL not configured or POST fails.
    """
    if not TEAMS_INCOMING_WEBHOOK_URL:
        raise AgentError(
            "TEAMS_INCOMING_WEBHOOK_URL not set -- "
            "create a Workflows webhook in the FTF-Approvals channel and add the URL to .env"
        )

    # Strip HTML for Adaptive Card text rendering
    plain = _MENTION_RE.sub(" ", text_or_html)
    plain = _HTML_RE.sub(" ", plain)
    plain = " ".join(plain.split())

    # Build Adaptive Card payload (Teams Workflows webhook format)
    body_blocks: list[dict] = []
    if subject:
        body_blocks.append({
            "type": "TextBlock", "text": subject,
            "weight": "bolder", "size": "medium", "wrap": True,
        })
    body_blocks.append({"type": "TextBlock", "text": plain, "wrap": True})

    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "version": "1.4",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "body": body_blocks,
            },
        }],
    }

    try:
        r = httpx.post(TEAMS_INCOMING_WEBHOOK_URL, json=payload, timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"Teams webhook POST failed: HTTP {exc.response.status_code} -- "
            f"{exc.response.text[:200]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"Teams webhook POST failed: {exc}") from exc

    log.info("teams message sent via webhook subject=%r", subject or "(no subject)")
    return {"ok": True, "method": "webhook"}


def send_confirmation(text: str, color: str = "green") -> None:
    """Send a short confirmation reply to the approval channel."""
    prefix_map = {"green": "[APPROVED]", "red": "[REJECTED]", "orange": "[WARNING]"}
    prefix = prefix_map.get(color, "")
    full_text = f"{prefix} {text}" if prefix else text
    try:
        send_channel_message(full_text)
    except AgentError as exc:
        log.warning("confirmation send failed: %s", exc)


# ── Read / poll for approvals (via Graph API) ─────────────────────────────────

def get_recent_messages(limit: int = 50) -> list[dict]:
    """Fetch the most recent messages from the approval channel via Graph API.

    Returns list of dicts: {id, sender, sender_is_app, text, created_at_dt}
    Filters out our own bot/app messages.
    Requires ChannelMessage.Read.All application permission.
    """
    if not all([TEAMS_TEAM_ID, TEAMS_CHANNEL_ID]):
        raise AgentError("TEAMS_TEAM_ID and TEAMS_CHANNEL_ID must be set in .env")

    url = (
        f"{_GRAPH_READ}/teams/{TEAMS_TEAM_ID}/channels/{TEAMS_CHANNEL_ID}/messages"
        f"?$top={limit}"
    )
    try:
        r = httpx.get(url, headers=_read_headers(), timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"Teams message fetch failed: HTTP {exc.response.status_code} -- "
            f"{exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"Teams message fetch failed: {exc}") from exc

    results: list[dict] = []
    for msg in r.json().get("value", []):
        from_obj = msg.get("from") or {}
        app_ref  = from_obj.get("application") or {}
        user_ref = from_obj.get("user") or {}

        # Skip messages posted by this app (workflow-posted messages appear as app)
        if app_ref.get("id") == TEAMS_APP_ID:
            continue
        # Also skip system/bot messages with no meaningful text
        if msg.get("messageType") != "message":
            continue

        sender_name  = user_ref.get("displayName") or app_ref.get("displayName") or "Unknown"
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

    Each returned dict: {action, order_id, reason, sender, message_id, created_at_dt}
    action values: "approve" | "approve_all" | "reject"
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
    text = _MENTION_RE.sub(" ", html)
    text = _HTML_RE.sub(" ", text)
    return " ".join(text.split())


def _parse_command(text: str) -> tuple[str, str | None, str | None]:
    """Parse APPROVE / APPROVE ALL / REJECT from plain Teams message text.

    Searches for the keyword anywhere (handles @mention prefix Teams inserts).
    Returns (action, order_id, reason).
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


# ── Message builders ──────────────────────────────────────────────────────────

def build_digest_html(orders: list[dict], ftf_order_url: str) -> str:
    """Build the hourly approval digest as plain text (used by send_channel_message).

    The Adaptive Card TextBlock renders this as readable text in Teams.
    orders -- list of dicts with: order_id, service_type, estimate_amount,
              flag_reason, status, flagged_at
    """
    now = datetime.now(timezone.utc)

    lines = [
        "FTF Estimates Pending Review -- @Robert @Ryan please approve or reject:",
        "",
    ]

    for rec in orders:
        oid        = rec["order_id"]
        amount     = rec.get("estimate_amount")
        amount_str = f"${float(amount):,.2f}" if amount else "TBD"
        age_str    = ""
        if rec.get("flagged_at"):
            try:
                fa = datetime.fromisoformat(str(rec["flagged_at"]))
                if fa.tzinfo is None:
                    fa = fa.replace(tzinfo=timezone.utc)
                age_h   = int((now - fa).total_seconds() / 3600)
                age_str = f" | {age_h}h ago"
            except Exception:
                pass

        flag_reason = (rec.get("flag_reason") or "see order")[:60]
        service     = rec.get("service_type") or "Unknown"
        link        = f"{ftf_order_url}/{oid}"
        lines.append(
            f"  Order {oid} ({link}) | {service} | {amount_str} | {flag_reason}{age_str}"
        )

    lines += [
        "",
        "Commands -- type in this channel:",
        "  APPROVE <order_id>          -- approve one estimate",
        "  APPROVE ALL                 -- approve everything in this list",
        "  REJECT <order_id> <reason>  -- reject and hold",
        "",
        "Example: APPROVE 1000276115",
    ]

    return "\n".join(lines)
