"""
teams_graph_client.py — Microsoft Teams client (hybrid architecture).

SEND  -> TEAMS_INCOMING_WEBHOOK_URL (primary — Azure Logic App relay)
         Posts directly to FTF-Approvals Teams channel via Logic App HTTP trigger.
         Webhook type auto-detected from URL:
           logic.azure.com    -> Azure Logic App relay (plain JSON)
           webhook.office.com -> O365 connector MessageCard (deprecated — 403)
           other              -> Teams Workflows Adaptive Card
         Falls back to Graph API Mail.Send if webhook is not configured.

SEND fallback -> Graph API Mail.Send (application permission)
         Emails notification to NOTIFICATION_TO_EMAILS from NOTIFICATION_FROM_EMAIL.
         Requires Mail.Send application permission + admin consent on the Azure AD app.

READ  -> Microsoft Graph API ChannelMessage.Read.All (application permission)
         Polls FTF-Approvals channel for APPROVE / REJECT commands.
         Application permission granted; admin consent confirmed 2026-05-28.

Required env vars:
  TEAMS_INCOMING_WEBHOOK_URL -- Logic App webhook URL (primary send)
  NOTIFICATION_FROM_EMAIL   -- licensed M365 mailbox in tenant (email fallback)
  NOTIFICATION_TO_EMAILS    -- comma-separated recipient emails (email fallback)
  TEAMS_TENANT_ID            -- Azure AD tenant ID
  TEAMS_APP_ID               -- Azure AD app client ID
  TEAMS_CLIENT_SECRET        -- Azure AD app secret
  TEAMS_TEAM_ID              -- Teams group ID
  TEAMS_CHANNEL_ID           -- Teams channel ID
"""

import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from config.settings import (
    NOTIFICATION_FROM_EMAIL,
    NOTIFICATION_TO_EMAILS,
    TEAMS_APP_ID,
    TEAMS_CHANNEL_ID,
    TEAMS_CHAT_ID,
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


# ── Send (webhook — auto-detects format from URL) ────────────────────────────
#
# Three webhook types supported, detected from the URL:
#
#   1. Azure Logic App (logic.azure.com)           -- plain JSON relay
#      Setup: portal.azure.com -> Logic App Consumption -> HTTP trigger
#             -> Teams "Post message in a chat or channel" action
#      Payload: {"subject": "...", "text": "..."}
#      The Logic App composes + posts the Teams message itself.
#
#   2. Teams Workflows (powerautomate.com flows)   -- Adaptive Card
#      Setup: Teams channel -> Workflows -> "Post to channel when webhook received"
#      Payload: Adaptive Card attachments format
#
#   3. O365 Incoming Webhook (webhook.office.com)  -- MessageCard (DEPRECATED)
#      Retired by Microsoft Aug 2024; returns 403 in most tenants.
#      Kept for reference only.

def _build_logic_app_payload(
    text: str,
    subject: str,
    parent_message_id: str | None = None,
) -> dict:
    """HTML payload for Azure Logic App HTTP trigger relay.

    Teams renders messageBody as HTML. We:
    - Prepend bold subject header
    - Replace newlines with <br> (existing HTML tags like <strong> pass through)
    - Include parent_message_id when posting a thread reply
    """
    header = f"<strong>{subject}</strong><br><br>" if subject else ""
    body   = text.replace("\n", "<br>")
    result: dict = {"subject": subject, "text": header + body}
    if parent_message_id:
        result["parent_message_id"] = parent_message_id
    return result


def _build_adaptive_card_payload(plain: str, subject: str) -> dict:
    """Adaptive Card for Teams Workflows incoming webhook."""
    body_blocks: list[dict] = []
    if subject:
        body_blocks.append({
            "type": "TextBlock", "text": subject,
            "weight": "bolder", "size": "medium", "wrap": True,
        })
    body_blocks.append({"type": "TextBlock", "text": plain, "wrap": True})
    return {
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


def _build_o365_payload(plain: str, subject: str) -> dict:
    """MessageCard for deprecated O365 connector (likely 403 in most tenants)."""
    payload: dict = {
        "@type":    "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0076D7",
        "summary":  subject or plain[:80],
    }
    if subject:
        payload["title"] = subject
    payload["text"] = plain
    return payload


def _detect_webhook_type(url: str) -> str:
    if "logic.azure.com" in url:
        return "logic_app"
    if "webhook.office.com" in url:
        return "o365_connector"
    return "workflows"   # power automate / teams workflows


# ── Send via Graph API email (Mail.Send application permission) ───────────────

def send_email_notification(text_or_html: str, subject: str = "") -> dict:
    """Send an HTML email to NOTIFICATION_TO_EMAILS via Graph API Mail.Send.

    Requires Mail.Send application permission on the Azure AD app + admin consent.
    NOTIFICATION_FROM_EMAIL must be a licensed M365 mailbox in the same tenant.

    Returns {"ok": True, "method": "graph_email"} on success.
    Raises AgentError if not configured or send fails.
    """
    if not NOTIFICATION_FROM_EMAIL:
        raise AgentError(
            "NOTIFICATION_FROM_EMAIL not set in .env -- "
            "set to a licensed M365 mailbox in your tenant (e.g. pchandra@nexgensurveying.com)"
        )
    recipients_raw = [e.strip() for e in NOTIFICATION_TO_EMAILS.split(",") if e.strip()]
    if not recipients_raw:
        raise AgentError(
            "NOTIFICATION_TO_EMAILS not set in .env -- "
            "comma-separated list of recipient emails"
        )

    subj = subject or "FTF Estimates — Action Required"

    # Keep HTML body if provided; Graph API supports HTML content
    html_body = text_or_html if "<" in text_or_html else text_or_html.replace("\n", "<br>")

    payload = {
        "message": {
            "subject": subj,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [
                {"emailAddress": {"address": addr}} for addr in recipients_raw
            ],
        },
        "saveToSentItems": True,
    }

    url = f"{_GRAPH_READ}/users/{NOTIFICATION_FROM_EMAIL}/sendMail"
    try:
        r = httpx.post(url, headers=_read_headers(), json=payload, timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"Graph API email send failed: HTTP {exc.response.status_code} -- "
            f"{exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"Graph API email send failed: {exc}") from exc

    log.info("email notification sent from=%s to=%s subject=%r",
             NOTIFICATION_FROM_EMAIL, recipients_raw, subj)
    return {"ok": True, "method": "graph_email"}


def send_channel_message(
    text_or_html: str,
    subject: str = "",
    parent_message_id: str | None = None,
) -> dict:
    """Send a Teams notification — webhook primary, email fallback.

    parent_message_id — when set, the Logic App will post as a thread reply
    (requires Logic App to have a Reply action configured; see docs/teams_setup.md).

    Primary: Logic App webhook (if TEAMS_INCOMING_WEBHOOK_URL set) -> posts to Teams channel
    Fallback: Graph API Mail.Send (if NOTIFICATION_FROM_EMAIL + NOTIFICATION_TO_EMAILS set)

    Raises AgentError if neither is configured.
    """
    # Primary: Teams channel via Logic App webhook
    if TEAMS_INCOMING_WEBHOOK_URL:
        return _send_via_webhook(text_or_html, subject, parent_message_id=parent_message_id)

    # Fallback: email via Graph API (thread replies not applicable for email)
    if NOTIFICATION_FROM_EMAIL and NOTIFICATION_TO_EMAILS:
        return send_email_notification(text_or_html, subject)

    raise AgentError(
        "No notification method configured.\n"
        "Option A (recommended): set TEAMS_INCOMING_WEBHOOK_URL (Logic App webhook) in .env\n"
        "Option B: set NOTIFICATION_FROM_EMAIL and NOTIFICATION_TO_EMAILS for email fallback.\n"
        "See docs/teams_setup.md for instructions."
    )


def _send_via_webhook(
    text_or_html: str,
    subject: str = "",
    parent_message_id: str | None = None,
) -> dict:
    """Internal: post via configured incoming webhook."""
    wtype = _detect_webhook_type(TEAMS_INCOMING_WEBHOOK_URL)

    if wtype == "logic_app":
        # Preserve HTML (bold etc.) and newlines — only strip @mention tags
        text = _MENTION_RE.sub("", text_or_html)
        payload = _build_logic_app_payload(text, subject, parent_message_id=parent_message_id)
    else:
        # Adaptive Card / O365 connector: collapse to plain text
        plain = _MENTION_RE.sub(" ", text_or_html)
        plain = _HTML_RE.sub(" ", plain)
        plain = " ".join(plain.split())
        if wtype == "o365_connector":
            payload = _build_o365_payload(plain, subject)
        else:
            payload = _build_adaptive_card_payload(plain, subject)

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

    log.info("teams message sent via %s subject=%r", wtype, subject or "(no subject)")
    return {"ok": True, "method": wtype}


def send_confirmation(
    text: str,
    color: str = "green",
    parent_message_id: str | None = None,
) -> None:
    """Send a short confirmation reply to the approval channel.

    color:
      "green"  → [APPROVED] prefix
      "red"    → [REJECTED] prefix
      "orange" → [WARNING]  prefix
      "blue"   → [INFO]     prefix
      ""       → no prefix
    parent_message_id — when set, posted as a thread reply (Logic App must support Reply action).
    """
    prefix_map = {
        "green":  "[APPROVED]",
        "red":    "[REJECTED]",
        "orange": "[WARNING]",
        "blue":   "[INFO]",
    }
    prefix    = prefix_map.get(color, "")
    full_text = f"{prefix} {text}" if prefix else text
    try:
        send_channel_message(full_text, parent_message_id=parent_message_id)
    except AgentError as exc:
        log.warning("confirmation send failed: %s", exc)


# ── Read / poll for approvals (via Graph API) ─────────────────────────────────

def get_recent_messages(limit: int = 50) -> list[dict]:
    """Fetch the most recent top-level messages from the approval channel.

    Returns list of dicts: {id, sender, text, created_at_dt, reply_count}
    Skips all app/bot messages — only returns human user messages.
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

        if msg.get("messageType") != "message":
            continue

        created_raw = msg.get("createdDateTime", "")
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            created_dt = datetime.now(timezone.utc)

        # Include ALL messages (app + human) at top level — we need app messages
        # so we can fetch their thread replies (user approvals come in as replies).
        # App/bot messages are filtered later so they don't trigger commands themselves.
        is_app = bool(app_ref) or not bool(user_ref.get("id"))
        sender_name = user_ref.get("displayName") or app_ref.get("displayName") or "Unknown"
        raw_body    = (msg.get("body") or {}).get("content", "")
        plain       = _clean_message_body(raw_body)
        reply_count = int(msg.get("replyCount") or 0)

        results.append({
            "id":            msg.get("id", ""),
            "sender":        sender_name,
            "is_app":        is_app,
            "text":          plain,
            "created_at_dt": created_dt,
            "reply_count":   reply_count,
        })

    return results


def _get_thread_replies(message_id: str) -> list[dict]:
    """Fetch human replies to a specific channel message (thread replies).

    Returns list of dicts: {id, sender, text, created_at_dt}
    Only returns replies from real users (skips bot/app replies).
    """
    url = (
        f"{_GRAPH_READ}/teams/{TEAMS_TEAM_ID}/channels/{TEAMS_CHANNEL_ID}"
        f"/messages/{message_id}/replies?$top=20"
    )
    try:
        r = httpx.get(url, headers=_read_headers(), timeout=20.0)
        r.raise_for_status()
    except Exception as exc:
        log.warning("could not fetch replies for message=%s: %s", message_id, exc)
        return []

    results: list[dict] = []
    for reply in r.json().get("value", []):
        from_obj = reply.get("from") or {}
        app_ref  = from_obj.get("application") or {}
        user_ref = from_obj.get("user") or {}

        # Only human replies — skip bot/app replies
        if app_ref or not user_ref.get("id"):
            continue
        if reply.get("messageType") != "message":
            continue

        sender_name  = user_ref.get("displayName") or "Unknown"
        sender_email = (user_ref.get("userPrincipalName") or "").lower()
        raw_body     = (reply.get("body") or {}).get("content", "")
        plain        = _clean_message_body(raw_body)

        created_raw = reply.get("createdDateTime", "")
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            created_dt = datetime.now(timezone.utc)

        results.append({
            "id":            reply.get("id", ""),
            "sender":        sender_name,
            "sender_email":  sender_email,
            "text":          plain,
            "created_at_dt": created_dt,
        })

    return results


def check_for_approvals(since: datetime | None = None) -> list[dict]:
    """Return parsed APPROVE / REJECT commands posted since `since` (UTC).

    Scans both top-level channel messages AND thread replies — approvals will
    typically come as replies to the bot's order notification message.

    Each returned dict: {action, order_ids, reason, sender, message_id, created_at_dt}
    action values: "approve" | "approve_all" | "reject"
    order_ids: list[str] for approve/reject; None for approve_all
    """
    messages  = get_recent_messages(limit=50)
    commands: list[dict] = []

    def _parse_and_append(
        text: str,
        sender: str,
        msg_id: str,
        created_dt,
        parent_message_id: str | None = None,
    ) -> None:
        parsed = _parse_all_commands(text)
        for action, order_ids, reason in parsed:
            if action == "unknown":
                continue
            commands.append({
                "action":            action,
                "order_ids":         order_ids,
                "reason":            reason,
                "sender":            sender,
                "message_id":        msg_id,
                "parent_message_id": parent_message_id,
                "created_at_dt":     created_dt,
            })
            log.info("approval command found action=%s order_ids=%s sender=%s",
                     action, order_ids, sender)

    for msg in messages:
        # ── Check top-level human messages ────────────────────────────────────
        if not msg["is_app"]:
            if not (since and msg["created_at_dt"] <= since):
                _parse_and_append(msg["text"], msg["sender"], msg["id"], msg["created_at_dt"])

        # ── Check thread replies (where approvals typically arrive) ──────────
        # Graph API does NOT return replyCount in the messages list response,
        # so we always fetch replies for messages within our time window.
        # Only check messages that could have recent replies (not too old).
        cutoff = since or (datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=48))
        if msg["created_at_dt"] >= cutoff:
            for reply in _get_thread_replies(msg["id"]):
                if since and reply["created_at_dt"] <= since:
                    continue
                # Pass the top-level message ID so confirmations can be posted as replies
                _parse_and_append(
                    reply["text"], reply["sender"], reply["id"], reply["created_at_dt"],
                    parent_message_id=msg["id"],
                )

    return commands


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_message_body(html: str) -> str:
    text = _MENTION_RE.sub(" ", html)
    text = _HTML_RE.sub(" ", text)
    return " ".join(text.split())


def _looks_like_order_id(token: str) -> bool:
    """True if token resembles an order ID rather than a conversational English word.

    Order IDs are numeric (1000276115), contain hyphens (QA-001), or are
    long uppercase strings. Short lowercase common words (of, this, the) return False
    so "I approve of this" doesn't trigger the bot.
    """
    if any(c.isdigit() for c in token):
        return True
    if "-" in token:
        return True
    if len(token) >= 5 and token[0].isupper():
        return True
    return False


def _parse_all_commands(text: str) -> list[tuple[str, list[str] | None, str | None]]:
    """Parse ALL APPROVE/REJECT commands from a single Teams message.

    Handles:
    - Multiple commands in one message  (approve A, B  reject C reason)
    - Comma-separated order IDs         (APPROVE QA-001, QA-002)
    - Space-separated order IDs         (APPROVE QA-001 QA-002)
    - Mixed separators                  (APPROVE QA-001, QA-002 QA-003)
    - Multi-line input (collapsed to single line after HTML strip)
    - For REJECT: last non-comma segment's trailing words become the reason

    Returns list of (action, order_ids, reason) tuples.

    action values:
      "approve"      — APPROVE <id> [<id2> ...]   — approve specific orders
      "approve_all"  — APPROVE ALL                 — approve all pending
      "approve_bare" — APPROVE (alone)             — approve the one pending order
      "reject"       — REJECT <id[s]> [reason]     — reject one or more orders
      "reject_all"   — REJECT ALL [reason]         — reject all pending
      "reject_bare"  — REJECT (alone)              — reject the one pending order
      "unknown"      — unrecognised

    Examples:
      "APPROVE QA-001, QA-002 REJECT QA-003 bad scope"
        → [("approve", ["QA-001","QA-002"], None),
           ("reject",  ["QA-003"], "bad scope")]

      "REJECT QA-001, QA-002 pricing issue"
        → [("reject", ["QA-001","QA-002"], "pricing issue")]

      "APPROVE ALL"  → [("approve_all", None, None)]
      "APPROVE"      → [("approve_bare", None, None)]
    """
    upper = text.upper()
    results: list[tuple[str, list[str] | None, str | None]] = []

    keyword_matches = list(re.finditer(r"\bAPPROVE\b|\bREJECT\b|\bDEFER\b", upper))
    if not keyword_matches:
        return [("unknown", None, None)]

    for i, match in enumerate(keyword_matches):
        keyword = match.group()
        kw_end  = match.end()

        # Grab text from after keyword to next keyword (or end of string)
        if i + 1 < len(keyword_matches):
            after = text[kw_end : keyword_matches[i + 1].start()].strip().rstrip(",")
        else:
            after = text[kw_end:].strip().rstrip(",")

        if keyword == "APPROVE":
            tokens = [t for t in re.split(r"[\s,]+", after) if t]
            if not tokens:
                results.append(("approve_bare", None, None))
            elif tokens[0].upper() == "ALL":
                results.append(("approve_all", None, None))
            elif any(_looks_like_order_id(t) for t in tokens):
                results.append(("approve", tokens, None))
            else:
                results.append(("unknown", None, None))  # conversational text, not order IDs

        elif keyword == "REJECT":
            if not after:
                results.append(("reject_bare", None, None))
                continue

            first = after.split()[0].upper()
            if first == "ALL":
                reason = after[3:].strip() or None
                results.append(("reject_all", None, reason))
                continue

            # Comma-separated IDs; trailing words after last comma = reason
            comma_parts = [p.strip() for p in after.split(",") if p.strip()]
            order_ids: list[str] = []
            reason_str: str | None = None
            for j, part in enumerate(comma_parts):
                words = part.split()
                if words:
                    order_ids.append(words[0])
                    if j == len(comma_parts) - 1 and len(words) > 1:
                        reason_str = " ".join(words[1:])
            if order_ids and any(_looks_like_order_id(oid) for oid in order_ids):
                results.append(("reject", order_ids, reason_str))
            elif not order_ids:
                results.append(("reject_bare", None, None))
            else:
                results.append(("unknown", None, None))  # conversational text, not order IDs

        elif keyword == "DEFER":
            if not after:
                results.append(("unknown", None, None))
                continue
            tokens = after.split()
            if tokens and _looks_like_order_id(tokens[0]):
                defer_id = tokens[0]
                defer_reason = " ".join(tokens[1:]) or None
                results.append(("defer", [defer_id], defer_reason))
            else:
                results.append(("unknown", None, None))

    return results if results else [("unknown", None, None)]


def _parse_command(text: str) -> tuple[str, list[str] | None, str | None]:
    """Backward-compatible wrapper — returns first command from _parse_all_commands."""
    return _parse_all_commands(text)[0]


# ── Teams Group Chat API (invoice approval flow) ──────────────────────────────
#
# The invoice pipeline uses a Teams GROUP CHAT (19:xxx@thread.v2) for:
#   - A3 posts invoice drafts: POST /chats/{chatId}/messages
#   - A4 polls for replies:    GET  /chats/{chatId}/messages/{id}/replies
#
# Required Azure AD app permissions (application, admin consent required):
#   Chat.Read.All        — read all chat messages
#   Chat.ReadWrite.All   — send messages to the chat as the app


def post_chat_message(text_or_html: str, subject: str = "") -> dict:
    """Post a new message to the invoice approval group chat.

    Returns {"id": message_id, "ok": True} on success.
    Requires Chat.ReadWrite.All application permission.
    """
    if not TEAMS_CHAT_ID:
        raise AgentError("TEAMS_CHAT_ID not set in .env")

    header = f"<strong>{subject}</strong><br><br>" if subject else ""
    body   = (header + text_or_html).replace("\n", "<br>")

    payload = {"body": {"contentType": "html", "content": body}}
    url     = f"{_GRAPH_READ}/chats/{TEAMS_CHAT_ID}/messages"

    try:
        r = httpx.post(url, headers=_read_headers(), json=payload, timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"post_chat_message failed: HTTP {exc.response.status_code} -- {exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"post_chat_message failed: {exc}") from exc

    data = r.json()
    msg_id = data.get("id", "")
    log.info("chat message posted id=%s subject=%r", msg_id, subject)
    return {"id": msg_id, "ok": True}


def post_chat_reply(message_id: str, text_or_html: str) -> dict:
    """Post a reply in a chat message thread.

    Returns {"id": reply_id, "ok": True} on success.
    Requires Chat.ReadWrite.All application permission.
    """
    if not TEAMS_CHAT_ID:
        raise AgentError("TEAMS_CHAT_ID not set in .env")

    body_html = text_or_html.replace("\n", "<br>")
    payload   = {"body": {"contentType": "html", "content": body_html}}
    url       = f"{_GRAPH_READ}/chats/{TEAMS_CHAT_ID}/messages/{message_id}/replies"

    try:
        r = httpx.post(url, headers=_read_headers(), json=payload, timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"post_chat_reply failed: HTTP {exc.response.status_code} -- {exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"post_chat_reply failed: {exc}") from exc

    data = r.json()
    log.info("chat reply posted to message=%s", message_id)
    return {"id": data.get("id", ""), "ok": True}


def get_chat_messages(limit: int = 50) -> list[dict]:
    """Fetch recent messages from the invoice approval group chat.

    Returns list of dicts: {id, sender, is_app, text, created_at_dt}
    Requires Chat.Read.All application permission.
    """
    if not TEAMS_CHAT_ID:
        raise AgentError("TEAMS_CHAT_ID not set in .env")

    url = f"{_GRAPH_READ}/chats/{TEAMS_CHAT_ID}/messages?$top={limit}"
    try:
        r = httpx.get(url, headers=_read_headers(), timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"get_chat_messages failed: HTTP {exc.response.status_code} -- {exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"get_chat_messages failed: {exc}") from exc

    results: list[dict] = []
    for msg in r.json().get("value", []):
        if msg.get("messageType") != "message":
            continue

        from_obj    = msg.get("from") or {}
        app_ref     = from_obj.get("application") or {}
        user_ref    = from_obj.get("user") or {}
        is_app      = bool(app_ref) or not bool(user_ref.get("id"))
        sender_name = user_ref.get("displayName") or app_ref.get("displayName") or "Unknown"
        raw_body    = (msg.get("body") or {}).get("content", "")
        plain       = _clean_message_body(raw_body)

        created_raw = msg.get("createdDateTime", "")
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            created_dt = datetime.now(timezone.utc)

        results.append({
            "id":            msg.get("id", ""),
            "sender":        sender_name,
            "is_app":        is_app,
            "text":          plain,
            "raw_html":      raw_body,
            "created_at_dt": created_dt,
        })

    return results


def get_chat_thread_replies(message_id: str) -> list[dict]:
    """Fetch human replies to a specific chat message thread.

    Returns list of dicts: {id, sender, text, created_at_dt}
    Only returns messages from real users (skips bot/app replies).
    """
    if not TEAMS_CHAT_ID:
        raise AgentError("TEAMS_CHAT_ID not set in .env")

    url = f"{_GRAPH_READ}/chats/{TEAMS_CHAT_ID}/messages/{message_id}/replies?$top=50"
    try:
        r = httpx.get(url, headers=_read_headers(), timeout=20.0)
        r.raise_for_status()
    except Exception as exc:
        log.warning("could not fetch chat replies for message=%s: %s", message_id, exc)
        return []

    results: list[dict] = []
    for reply in r.json().get("value", []):
        if reply.get("messageType") != "message":
            continue

        from_obj = reply.get("from") or {}
        app_ref  = from_obj.get("application") or {}
        user_ref = from_obj.get("user") or {}
        if app_ref or not user_ref.get("id"):
            continue

        sender_name  = user_ref.get("displayName") or "Unknown"
        sender_email = (user_ref.get("userPrincipalName") or "").lower()
        raw_body     = (reply.get("body") or {}).get("content", "")
        plain        = _clean_message_body(raw_body)

        created_raw = reply.get("createdDateTime", "")
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            created_dt = datetime.now(timezone.utc)

        results.append({
            "id":            reply.get("id", ""),
            "sender":        sender_name,
            "sender_email":  sender_email,
            "text":          plain,
            "created_at_dt": created_dt,
        })

    return results


# ── Teams Channel API (invoice pipeline v5 — tacv2 channel) ──────────────────
#
# The invoice pipeline posts to a Teams CHANNEL (thread.tacv2), not a group chat.
# Channel ID: 19:50IGnbm0MQft2C4eUkl8RXLk6wa2IRpEEE-ySnUeaV81@thread.tacv2
# Required Azure AD app permissions (application, admin consent required):
#   ChannelMessage.Send          — post messages to the channel
#   ChannelMessage.Read.All      — read channel messages and thread replies


def post_channel_message(text_or_html: str, subject: str = "") -> dict:
    """Post a new top-level message to the invoice approval Teams channel.

    Returns {"id": message_id, "ok": True} on success.
    Requires ChannelMessage.Send application permission.
    """
    if not TEAMS_TEAM_ID or not TEAMS_CHANNEL_ID:
        raise AgentError("TEAMS_TEAM_ID and TEAMS_CHANNEL_ID must be set in .env")

    header = f"<strong>{subject}</strong><br><br>" if subject else ""
    body   = (header + text_or_html).replace("\n", "<br>")

    payload = {"body": {"contentType": "html", "content": body}}
    url     = f"{_GRAPH_READ}/teams/{TEAMS_TEAM_ID}/channels/{TEAMS_CHANNEL_ID}/messages"

    try:
        r = httpx.post(url, headers=_read_headers(), json=payload, timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"post_channel_message failed: HTTP {exc.response.status_code} -- {exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"post_channel_message failed: {exc}") from exc

    data   = r.json()
    msg_id = data.get("id", "")
    log.info("channel message posted id=%s subject=%r", msg_id, subject)
    return {"id": msg_id, "ok": True}


def post_channel_reply(message_id: str, text_or_html: str) -> dict:
    """Post a thread reply to a channel message.

    Returns {"id": reply_id, "ok": True} on success.
    Requires ChannelMessage.Send application permission.
    """
    if not TEAMS_TEAM_ID or not TEAMS_CHANNEL_ID:
        raise AgentError("TEAMS_TEAM_ID and TEAMS_CHANNEL_ID must be set in .env")

    body_html = text_or_html.replace("\n", "<br>")
    payload   = {"body": {"contentType": "html", "content": body_html}}
    url       = (
        f"{_GRAPH_READ}/teams/{TEAMS_TEAM_ID}/channels/{TEAMS_CHANNEL_ID}"
        f"/messages/{message_id}/replies"
    )

    try:
        r = httpx.post(url, headers=_read_headers(), json=payload, timeout=20.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"post_channel_reply failed: HTTP {exc.response.status_code} -- {exc.response.text[:300]}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"post_channel_reply failed: {exc}") from exc

    data = r.json()
    log.info("channel reply posted to message=%s", message_id)
    return {"id": data.get("id", ""), "ok": True}


def get_channel_thread_replies(message_id: str) -> list[dict]:
    """Fetch human replies to a specific channel message thread.

    Returns list of dicts: {id, sender, text, created_at_dt}
    Only returns messages from real users (skips bot/app replies).
    Requires ChannelMessage.Read.All application permission.
    """
    if not TEAMS_TEAM_ID or not TEAMS_CHANNEL_ID:
        raise AgentError("TEAMS_TEAM_ID and TEAMS_CHANNEL_ID must be set in .env")

    url = (
        f"{_GRAPH_READ}/teams/{TEAMS_TEAM_ID}/channels/{TEAMS_CHANNEL_ID}"
        f"/messages/{message_id}/replies?$top=50"
    )
    try:
        r = httpx.get(url, headers=_read_headers(), timeout=20.0)
        r.raise_for_status()
    except Exception as exc:
        log.warning("could not fetch channel replies for message=%s: %s", message_id, exc)
        return []

    results: list[dict] = []
    for reply in r.json().get("value", []):
        if reply.get("messageType") != "message":
            continue

        from_obj = reply.get("from") or {}
        app_ref  = from_obj.get("application") or {}
        user_ref = from_obj.get("user") or {}

        if app_ref or not user_ref.get("id"):
            continue

        sender_name  = user_ref.get("displayName") or "Unknown"
        sender_email = (user_ref.get("userPrincipalName") or "").lower()
        raw_body     = (reply.get("body") or {}).get("content", "")
        plain        = _clean_message_body(raw_body)

        created_raw = reply.get("createdDateTime", "")
        try:
            created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            created_dt = datetime.now(timezone.utc)

        results.append({
            "id":            reply.get("id", ""),
            "sender":        sender_name,
            "sender_email":  sender_email,
            "text":          plain,
            "created_at_dt": created_dt,
        })

    return results


def parse_confirmation_reply(text: str) -> str | None:
    """Parse a yes/no confirmation reply from a Teams message.

    Returns "yes", "no", or None if the message is not a clear yes/no.

    Handles natural language synonyms:
      yes → yes, yeah, yep, yup, sure, ok, okay, confirm, do it, go ahead, proceed, absolutely
      no  → no, nope, nah, cancel, stop, keep it, don't, negative, abort, never mind
    """
    cleaned = re.sub(r"<[^>]+>", " ", text)   # strip HTML
    word = cleaned.strip().lower().split()[0] if cleaned.strip() else ""
    phrase = " ".join(cleaned.strip().lower().split()[:2])

    YES = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "confirm", "confirmed",
           "absolutely", "definitely", "proceed", "affirmative", "correct"}
    NO  = {"no", "nope", "nah", "cancel", "stop", "negative", "abort", "skip",
           "dont", "don't", "keep"}
    YES_PHRASES = {"do it", "go ahead", "go for it", "yes please", "change it"}
    NO_PHRASES  = {"keep it", "never mind", "no change", "leave it", "no thanks", "don't change"}

    if phrase in YES_PHRASES:
        return "yes"
    if phrase in NO_PHRASES:
        return "no"
    if word in YES:
        return "yes"
    if word in NO:
        return "no"
    return None


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
        # ⚠ visual indicator for orders stuck >= 4 hours
        age_hours = 0
        if rec.get("flagged_at"):
            try:
                fa = datetime.fromisoformat(str(rec["flagged_at"]))
                if fa.tzinfo is None:
                    fa = fa.replace(tzinfo=timezone.utc)
                age_hours = int((now - fa).total_seconds() / 3600)
            except Exception:
                pass
        overdue_flag = " *** OVERDUE ***" if age_hours >= 4 else ""
        age_str_val  = f" | {age_hours}h in queue{overdue_flag}" if age_hours else age_str
        lines.append(
            f"  Order {oid} ({link}) | {service} | {amount_str} | {flag_reason}{age_str_val}"
        )

    lines += [
        "",
        "Commands -- type in this channel (only Robert, Ryan, or Prateek):",
        "  APPROVE <id> [<id2> ...]    -- approve one or more estimates",
        "  APPROVE ALL                 -- approve everything in this list",
        "  REJECT <order_id> <reason>  -- reject and hold",
        "  DEFER <order_id> [reason]   -- hold for tomorrow without rejecting",
        "",
        "Examples:",
        "  APPROVE 1000276115",
        "  APPROVE 1000276115 1000276116 1000276117",
        "  REJECT 1000276115 client requested scope change",
        "  DEFER 1000276115 waiting on client callback",
    ]

    return "\n".join(lines)
