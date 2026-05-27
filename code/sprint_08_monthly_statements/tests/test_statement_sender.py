"""Tests for agent_17_statement_sender."""

from datetime import date
from unittest.mock import MagicMock, call, patch

import pytest


def _stmt(client="billing@b2b.com", order_count=3, total=1500.0):
    return {
        "client_email": client,
        "statement_month": date(2026, 4, 1),
        "order_count": order_count,
        "total_amount": total,
        "excel_path": "/tmp/stmt.xlsx",
        "pdf_path": "/tmp/stmt.pdf",
    }


# ── _send_email ───────────────────────────────────────────────────────────────

def test_send_email_skipped_when_no_smtp_host():
    with patch("agents.agent_17_statement_sender.SMTP_HOST", None), \
         patch("agents.agent_17_statement_sender.smtplib") as mock_smtp:
        from agents.agent_17_statement_sender import _send_email
        _send_email("x@y.com", date(2026, 4, 1), "/tmp/a.xlsx", "/tmp/a.pdf")
    mock_smtp.SMTP.assert_not_called()


# ── _send_teams_notification ──────────────────────────────────────────────────

def test_send_teams_notification_skipped_when_no_webhook():
    with patch("agents.agent_17_statement_sender.TEAMS_WEBHOOK_URL", None), \
         patch("agents.agent_17_statement_sender.httpx") as mock_httpx:
        from agents.agent_17_statement_sender import _send_teams_notification
        _send_teams_notification("x@y.com", date(2026, 4, 1), 3, 1200.0)
    mock_httpx.post.assert_not_called()


# ── agent_17 run (mocked) ─────────────────────────────────────────────────────

def test_run_marks_statement_sent():
    month = date(2026, 4, 1)
    stmt  = _stmt()

    with patch("agents.agent_17_statement_sender._get_reviewed_statements",
               return_value=[stmt]), \
         patch("agents.agent_17_statement_sender._send_email") as mock_email, \
         patch("agents.agent_17_statement_sender._send_teams_notification") as mock_teams, \
         patch("agents.agent_17_statement_sender.update_statement_status") as mock_update, \
         patch("agents.agent_17_statement_sender.log_decision"):

        from agents.agent_17_statement_sender import run
        result = run(statement_month=month)

    assert result["sent"] == 1
    assert result["skipped"] == 0
    mock_email.assert_called_once()
    mock_teams.assert_called_once()
    call_kwargs = mock_update.call_args
    status_val = call_kwargs.kwargs.get("status") or call_kwargs.args[2]
    assert status_val == "sent"


def test_run_marks_failed_on_exception():
    month = date(2026, 4, 1)
    stmt  = _stmt()

    with patch("agents.agent_17_statement_sender._get_reviewed_statements",
               return_value=[stmt]), \
         patch("agents.agent_17_statement_sender._send_email",
               side_effect=Exception("SMTP error")), \
         patch("agents.agent_17_statement_sender.update_statement_status") as mock_update, \
         patch("agents.agent_17_statement_sender.log_decision"):

        from agents.agent_17_statement_sender import run
        result = run(statement_month=month)

    assert result["sent"] == 0
    assert result["skipped"] == 1
    call_args = mock_update.call_args
    assert call_args.args[2] == "failed"
