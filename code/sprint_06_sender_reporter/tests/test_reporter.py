"""Unit tests for Agent 9 — Reporter."""
import pytest
from unittest.mock import MagicMock, patch

import httpx

from agents.agent_09_reporter import _build_payload, send_daily_report
from core.exceptions import AgentError

# ── fixtures ─────────────────────────────────────────────────────────────────

_SUMMARY = {
    "sent_today": 4,
    "flagged_today": 1,
    "awaiting_approval": 2,
    "ready_to_send": 3,
    "active_pipeline": 12,
}

# ── tests ─────────────────────────────────────────────────────────────────────


def test_report_posts_to_teams():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with (
        patch("agents.agent_09_reporter.get_daily_summary", return_value=_SUMMARY),
        patch("agents.agent_09_reporter.httpx.post", return_value=mock_response) as mock_post,
        patch("agents.agent_09_reporter.TEAMS_WEBHOOK_URL", "https://teams.example.com/webhook"),
    ):
        send_daily_report()

    mock_post.assert_called_once()
    call_url = mock_post.call_args[0][0]
    assert call_url == "https://teams.example.com/webhook"


def test_report_contains_sent_today_count():
    payload = _build_payload(_SUMMARY)
    facts = payload["sections"][0]["facts"]
    sent_fact = next(f for f in facts if f["name"] == "Estimates Sent Today")
    assert sent_fact["value"] == "4"


def test_report_contains_flagged_count():
    payload = _build_payload(_SUMMARY)
    facts = payload["sections"][0]["facts"]
    flagged_fact = next(f for f in facts if f["name"] == "Flagged (Needs Review)")
    assert flagged_fact["value"] == "1"


def test_report_returns_true_on_success():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with (
        patch("agents.agent_09_reporter.get_daily_summary", return_value=_SUMMARY),
        patch("agents.agent_09_reporter.httpx.post", return_value=mock_response),
        patch("agents.agent_09_reporter.TEAMS_WEBHOOK_URL", "https://teams.example.com/webhook"),
    ):
        result = send_daily_report()

    assert result is True


def test_report_raises_on_webhook_failure():
    with (
        patch("agents.agent_09_reporter.get_daily_summary", return_value=_SUMMARY),
        patch(
            "agents.agent_09_reporter.httpx.post",
            side_effect=Exception("connection refused"),
        ),
        patch("agents.agent_09_reporter.TEAMS_WEBHOOK_URL", "https://teams.example.com/webhook"),
    ):
        with pytest.raises(AgentError, match="Teams webhook failed"):
            send_daily_report()
