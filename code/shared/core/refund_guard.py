"""Refund Guard — I-063 hard rule enforcement.

Ryan (2026-05-26): "We don't want AI doing a refund."
Hard rule: if ANY text from a customer or order note contains refund intent,
immediately alert Jessica and stop all further AI action on that order.
AI never touches, processes, or approves a refund.
"""

import httpx

from config.flag_triggers import REFUND_KEYWORDS
from config.settings import TEAMS_WEBHOOK_URL
from core.logger import get_logger

logger = get_logger(__name__)

_JESSICA_CONTACT = "Jessica"


def detect_refund_intent(text: str) -> bool:
    """Return True if text contains any refund-related keyword."""
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in REFUND_KEYWORDS)


def alert_jessica_refund(order_id: str, source_text: str) -> None:
    """Send an immediate Teams alert to Jessica about a detected refund request.

    This is fire-and-forget — the caller is responsible for stopping further
    AI processing after calling this function.
    """
    if not TEAMS_WEBHOOK_URL:
        logger.error(
            "REFUND DETECTED order=%s but TEAMS_WEBHOOK_URL not set — Jessica NOT notified! Text: %.100s",
            order_id, source_text,
        )
        return

    title = f"REFUND REQUEST DETECTED — Order {order_id}"
    body = (
        f"**IMPORTANT: AI has stopped processing this order.**  \n\n"
        f"**Order:** {order_id}  \n"
        f"**Trigger:** Refund-related language detected in order data  \n"
        f"**Detected text (excerpt):** {source_text[:200]}  \n\n"
        f"**Action required:** {_JESSICA_CONTACT} — please handle this refund request manually. "
        f"AI will not take any further action on this order."
    )

    payload = {
        "@type":      "MessageCard",
        "@context":   "https://schema.org/extensions",
        "themeColor": "FF0000",
        "summary":    title,
        "title":      title,
        "text":       body,
    }

    try:
        resp = httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=15)
        resp.raise_for_status()
        logger.warning(
            "REFUND ALERT sent to Jessica order=%s — AI stopped processing", order_id
        )
    except Exception as exc:
        logger.error(
            "REFUND ALERT failed to send for order=%s: %s — Jessica must be notified manually!",
            order_id, exc,
        )
