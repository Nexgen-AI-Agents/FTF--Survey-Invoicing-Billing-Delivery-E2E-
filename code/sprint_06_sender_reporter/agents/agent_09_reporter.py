import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

import httpx

from config.settings import TEAMS_WEBHOOK_URL
from core.db import get_daily_summary
from core.exceptions import AgentError
from core.logger import get_logger

AGENT_NAME = "agent_09_reporter"
log = get_logger(AGENT_NAME)

_TIMEOUT = 10.0


def _build_payload(summary: dict) -> dict:
    """Build a Teams MessageCard payload from daily summary stats."""
    sent = summary.get("sent_today", 0)
    flagged = summary.get("flagged_today", 0)
    awaiting = summary.get("awaiting_approval", 0)
    ready = summary.get("ready_to_send", 0)
    active = summary.get("active_pipeline", 0)

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0076D7",
        "summary": "FTF AI — Daily Estimate Report",
        "sections": [
            {
                "activityTitle": "FTF AI — Daily Estimate Report",
                "facts": [
                    {"name": "Estimates Sent Today", "value": str(sent)},
                    {"name": "Flagged (Needs Review)", "value": str(flagged)},
                    {"name": "Awaiting Human Approval", "value": str(awaiting)},
                    {"name": "Ready to Send", "value": str(ready)},
                    {"name": "Active Pipeline", "value": str(active)},
                ],
            }
        ],
    }


def send_daily_report() -> bool:
    """Query today's stats and POST a digest to the MS Teams webhook.

    Returns True on success.
    Raises AgentError if the webhook call fails.
    """
    if not TEAMS_WEBHOOK_URL:
        raise AgentError("send_daily_report: TEAMS_WEBHOOK_URL is not configured")

    summary = get_daily_summary()
    payload = _build_payload(summary)

    try:
        r = httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=_TIMEOUT)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"send_daily_report: Teams webhook returned HTTP {exc.response.status_code}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"send_daily_report: Teams webhook failed — {exc}") from exc

    log.info(
        "daily report sent sent_today=%s flagged_today=%s",
        summary.get("sent_today", 0),
        summary.get("flagged_today", 0),
    )
    return True


def run() -> bool:
    """Send the daily digest to MS Teams."""
    return send_daily_report()


if __name__ == "__main__":
    run()
