"""teams_reader.py — READ-ONLY reader for the AI Invoicing Agent Teams chat.

The agent POSTS its report through a Power Automate HTTP flow (one-way). This module is
the missing return path: it READS the team's replies so the agent can learn from them.

Scope + privacy: it only ever reads the ONE chat named by TEAMS_CHAT_ID. It never lists
other users' chats, never posts, and never writes anything anywhere.

Auth reuses the existing app-only Graph token (core.onedrive_excel_client._get_token);
the app registration already holds Chat.Read.All / ChannelMessage.Read.All.

Chat id discovery: if TEAMS_CHAT_ID is not set, we look only through the chats the
service account (ONEDRIVE_FILE_USER) is a member of and match TEAMS_CHAT_TOPIC. If the
service account is not in the chat, set TEAMS_CHAT_ID explicitly — no tenant-wide scan.
"""
import re
from typing import Optional

import httpx

from config.settings import (
    ONEDRIVE_FILE_USER,
    TEAMS_CHAT_ID,
    TEAMS_CHAT_TOPIC,
)
from core.logger import get_logger
from core.onedrive_excel_client import _get_token

log = get_logger("teams_reader")

_GRAPH = "https://graph.microsoft.com/v1.0"
_TAG_RE = re.compile(r"<[^>]+>")


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}"}


def html_to_text(html: str) -> str:
    """Teams message bodies are HTML — flatten to readable text (keeps line breaks)."""
    if not html:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    s = re.sub(r"</(p|div|li|tr)>", "\n", s, flags=re.I)
    s = _TAG_RE.sub("", s)
    for ent, ch in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&quot;", '"'), ("&#39;", "'")):
        s = s.replace(ent, ch)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def resolve_chat_id() -> str:
    """Return the chat id to read. Explicit config wins; else match topic among the
    service account's own chats only. Returns "" when it cannot be resolved."""
    if TEAMS_CHAT_ID:
        return TEAMS_CHAT_ID
    if not TEAMS_CHAT_TOPIC:
        return ""
    want = TEAMS_CHAT_TOPIC.strip().lower()
    url = f"{_GRAPH}/users/{ONEDRIVE_FILE_USER}/chats?$top=50"
    pages = 0
    try:
        while url and pages < 6:
            r = httpx.get(url, headers=_headers(), timeout=30.0)
            if not r.is_success:
                log.warning("teams_reader: chat lookup HTTP %s %s", r.status_code, r.text[:160])
                return ""
            body = r.json()
            for c in body.get("value", []):
                if (c.get("topic") or "").strip().lower() == want:
                    return c.get("id") or ""
            url, pages = body.get("@odata.nextLink"), pages + 1
    except Exception as exc:
        log.warning("teams_reader: chat lookup failed: %s", exc)
    log.warning("teams_reader: no chat titled %r among %s's chats — set TEAMS_CHAT_ID",
                TEAMS_CHAT_TOPIC, ONEDRIVE_FILE_USER)
    return ""


def fetch_messages(limit: int = 25, chat_id: Optional[str] = None) -> list[dict]:
    """Newest-first messages from the configured chat.

    Returns [{id, created, edited, from, from_id, text, is_bot}]. Read-only; on any
    failure returns [] so callers (the report) can never break because Teams hiccuped.
    """
    cid = chat_id or resolve_chat_id()
    if not cid:
        return []
    try:
        r = httpx.get(f"{_GRAPH}/chats/{cid}/messages?$top={int(limit)}",
                      headers=_headers(), timeout=30.0)
        if not r.is_success:
            log.warning("teams_reader: messages HTTP %s %s", r.status_code, r.text[:160])
            return []
        out = []
        for m in r.json().get("value", []):
            if m.get("messageType") not in (None, "message"):
                continue          # skip system events (joins, renames, ...)
            frm = (m.get("from") or {})
            user = frm.get("user") or {}
            app = frm.get("application") or {}
            text = html_to_text((m.get("body") or {}).get("content", ""))
            if not text:
                continue
            out.append({
                "id":      m.get("id"),
                "created": m.get("createdDateTime"),
                "edited":  m.get("lastModifiedDateTime"),
                "from":    user.get("displayName") or app.get("displayName") or "unknown",
                "from_id": user.get("id") or app.get("id") or "",
                "text":    text,
                # Our own report posts arrive via the Power Automate flow (an application
                # identity, no user) — never learn from ourselves.
                "is_bot":  bool(app) and not user,
            })
        return out
    except Exception as exc:
        log.warning("teams_reader: fetch failed: %s", exc)
        return []
