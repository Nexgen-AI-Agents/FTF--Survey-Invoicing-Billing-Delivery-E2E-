"""
teams_approval_receiver.py — Teams Outgoing Webhook receiver for estimate approvals.

How it works:
  1. Teams admin registers an Outgoing Webhook in the approval channel.
  2. Robert or Ryan types  APPROVE ORD-001  or  APPROVE ALL  or  REJECT ORD-001
     (or with the @mention prefix Teams adds automatically).
  3. Teams POSTs a JSON payload to this server's /teams/webhook endpoint.
  4. This server verifies the HMAC-SHA256 signature, parses the command,
     and calls process_approval_reply() from agent_04_human_gate.
  5. A confirmation is sent back to the Teams channel.

Environment variables required:
  TEAMS_OUTGOING_WEBHOOK_SECRET   — copied from Teams Outgoing Webhook registration
  APPROVAL_RECEIVER_HOST          — bind host (default 0.0.0.0)
  APPROVAL_RECEIVER_PORT          — bind port (default 5001)
  TEAMS_APPROVAL_WEBHOOK_URL      — outbound webhook URL for confirmation messages
  DB_*                            — PostgreSQL connection (same as rest of pipeline)

Run:  python scripts/run_approval_receiver.py
"""

import base64
import hashlib
import hmac
import json
import os
import re
import sys

from flask import Flask, Response, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import (
    APPROVAL_RECEIVER_HOST,
    APPROVAL_RECEIVER_PORT,
    TEAMS_APPROVAL_WEBHOOK_URL,
    TEAMS_OUTGOING_WEBHOOK_SECRET,
)
from core.db import get_all_awaiting_orders, get_all_flagged_orders
from core.exceptions import AgentError
from core.logger import get_logger

log = get_logger("teams_approval_receiver")

app = Flask(__name__)

# ── HMAC verification ─────────────────────────────────────────────────────────

def _verify_teams_hmac(secret: str, body: bytes, auth_header: str) -> bool:
    """Verify Teams Outgoing Webhook HMAC-SHA256 signature.

    Teams sends:  Authorization: HMAC <base64(hmac-sha256(secret, body))>
    """
    if not auth_header or not auth_header.startswith("HMAC "):
        return False
    try:
        received_b64 = auth_header[5:].strip()
        received = base64.b64decode(received_b64)
        expected = hmac.new(
            base64.b64decode(secret), body, hashlib.sha256
        ).digest()
        return hmac.compare_digest(received, expected)
    except Exception:
        return False


# ── Command parser ────────────────────────────────────────────────────────────

# Strip @mention prefix Teams inserts: "<at>EstimateBot</at> APPROVE ORD-001"
_MENTION_RE = re.compile(r"<at>[^<]*</at>", re.IGNORECASE)

def _parse_command(text: str) -> tuple[str, str | None, str | None]:
    """Parse Teams message text into (action, order_id, reason).

    Supported commands (case-insensitive, @mention prefix stripped):
      APPROVE ALL
      APPROVE <order_id>
      REJECT  <order_id>
      REJECT  <order_id> <reason text>

    Returns:
      action   — "approve" | "approve_all" | "reject" | "unknown"
      order_id — order ID string or None
      reason   — rejection reason or None
    """
    clean = _MENTION_RE.sub("", text).strip()
    tokens = clean.split(None, 2)  # max 3 parts: action, order_id, reason

    if not tokens:
        return "unknown", None, None

    action_word = tokens[0].upper()

    if action_word == "APPROVE":
        if len(tokens) == 1:
            return "unknown", None, None
        if tokens[1].upper() == "ALL":
            return "approve_all", None, None
        return "approve", tokens[1], None

    if action_word == "REJECT":
        if len(tokens) < 2:
            return "unknown", None, None
        reason = tokens[2] if len(tokens) == 3 else None
        return "reject", tokens[1], reason

    return "unknown", None, None


# ── Confirmation sender ───────────────────────────────────────────────────────

def _send_confirmation(message: str, theme_color: str = "00CC00") -> None:
    """POST a confirmation card back to the approval Teams channel."""
    if not TEAMS_APPROVAL_WEBHOOK_URL:
        return
    import httpx
    try:
        httpx.post(
            TEAMS_APPROVAL_WEBHOOK_URL,
            json={
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": theme_color,
                "summary": "Approval Update",
                "text": message,
            },
            timeout=10.0,
        )
    except Exception as exc:
        log.warning("confirmation send failed: %s", exc)


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@app.route("/teams/webhook", methods=["POST"])
def teams_webhook() -> Response:
    """Receive and process Teams Outgoing Webhook POST."""
    body = request.get_data()

    # Verify HMAC when secret is configured (skip in dev if not set)
    if TEAMS_OUTGOING_WEBHOOK_SECRET:
        auth = request.headers.get("Authorization", "")
        if not _verify_teams_hmac(TEAMS_OUTGOING_WEBHOOK_SECRET, body, auth):
            log.warning("teams_webhook HMAC verification failed — rejected")
            return jsonify({"type": "message", "text": "Unauthorized."}), 401

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return jsonify({"type": "message", "text": "Bad request — invalid JSON."}), 400

    # Teams sends text in "text" field; HTML entities may be present
    raw_text = data.get("text", "")
    sender_name = (data.get("from") or {}).get("name", "Unknown")

    log.info("teams_webhook received from=%s text=%r", sender_name, raw_text[:120])

    action, order_id, reason = _parse_command(raw_text)

    # Import here to keep startup fast and allow mocking in tests
    from sprint_03_human_gate.agents.agent_04_human_gate import (  # type: ignore[import]
        process_approval_reply,
    )

    if action == "approve_all":
        flagged  = get_all_flagged_orders()
        awaiting = get_all_awaiting_orders()
        targets  = [r["order_id"] for r in flagged + awaiting]

        if not targets:
            msg = f"✅ {sender_name}: No orders pending approval right now."
            _send_confirmation(msg, "0078D7")
            return jsonify({"type": "message", "text": msg})

        approved, failed = [], []
        for oid in targets:
            try:
                process_approval_reply(oid, "approve")
                approved.append(oid)
            except AgentError as exc:
                failed.append(f"{oid} ({exc})")

        msg = (
            f"✅ **{sender_name}** approved ALL {len(approved)} order(s): "
            f"{', '.join(approved)}"
        )
        if failed:
            msg += f"\n⚠️ Could not approve: {', '.join(failed)}"
        _send_confirmation(msg)
        return jsonify({"type": "message", "text": msg})

    if action == "approve":
        try:
            process_approval_reply(order_id, "approve")
            msg = f"✅ **{sender_name}** approved order **{order_id}**. Estimate will be sent."
            _send_confirmation(msg)
            return jsonify({"type": "message", "text": msg})
        except AgentError as exc:
            msg = f"⚠️ Could not approve {order_id}: {exc}"
            _send_confirmation(msg, "FF6600")
            return jsonify({"type": "message", "text": msg}), 400

    if action == "reject":
        try:
            process_approval_reply(order_id, "reject")
            msg = (
                f"🚫 **{sender_name}** rejected order **{order_id}**."
                + (f" Reason: {reason}" if reason else "")
            )
            _send_confirmation(msg, "CC0000")
            return jsonify({"type": "message", "text": msg})
        except AgentError as exc:
            msg = f"⚠️ Could not reject {order_id}: {exc}"
            _send_confirmation(msg, "FF6600")
            return jsonify({"type": "message", "text": msg}), 400

    # Unknown / help
    help_text = (
        "**FTF Estimate Bot — commands:**\n"
        "- `APPROVE <order_id>` — approve one estimate\n"
        "- `APPROVE ALL` — approve everything pending\n"
        "- `REJECT <order_id> [reason]` — reject one estimate\n\n"
        "Example: `APPROVE 1000276115`"
    )
    return jsonify({"type": "message", "text": help_text})


@app.route("/health", methods=["GET"])
def health() -> Response:
    return jsonify({"status": "ok", "service": "teams_approval_receiver"})


# ── Entry point ───────────────────────────────────────────────────────────────

def create_app() -> Flask:
    """Return the Flask app for WSGI deployment or testing."""
    return app


def run_server() -> None:
    log.info(
        "Teams approval receiver starting on %s:%s",
        APPROVAL_RECEIVER_HOST, APPROVAL_RECEIVER_PORT,
    )
    app.run(host=APPROVAL_RECEIVER_HOST, port=APPROVAL_RECEIVER_PORT)


if __name__ == "__main__":
    run_server()
