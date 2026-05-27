"""Tests for agent_11_ar_escalation."""

from unittest.mock import MagicMock, call, patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _invoice(order_id, days_overdue, level=1):
    return {
        "order_id": order_id,
        "customer_email": f"{order_id.lower()}@client.com",
        "invoice_amount": 1200.0,
        "days_overdue": days_overdue,
        "reminder_level": level,
    }


# ── tests ─────────────────────────────────────────────────────────────────────

def test_run_sends_90day_alert_and_advances_level():
    inv = _invoice("ORD-090", 95)

    with patch("agents.agent_11_ar_escalation.get_invoices_due_for_escalation",
               side_effect=[[inv], []]), \
         patch("agents.agent_11_ar_escalation._send_teams_alert") as mock_alert, \
         patch("agents.agent_11_ar_escalation.update_ar_escalation_level") as mock_update, \
         patch("agents.agent_11_ar_escalation.log_decision"):

        from agents.agent_11_ar_escalation import run
        result = run()

    assert result["alerts_90"] == 1
    assert result["alerts_60"] == 0
    mock_alert.assert_called_once_with(
        order_id="ORD-090", customer_email="ord-090@client.com",
        days_overdue=95, invoice_amount=1200.0, tier=3,
    )
    mock_update.assert_called_once_with("ORD-090", new_level=3)


def test_run_sends_60day_alert_and_advances_level():
    inv = _invoice("ORD-060", 65)

    with patch("agents.agent_11_ar_escalation.get_invoices_due_for_escalation",
               side_effect=[[], [inv]]), \
         patch("agents.agent_11_ar_escalation._send_teams_alert") as mock_alert, \
         patch("agents.agent_11_ar_escalation.update_ar_escalation_level") as mock_update, \
         patch("agents.agent_11_ar_escalation.log_decision"):

        from agents.agent_11_ar_escalation import run
        result = run()

    assert result["alerts_60"] == 1
    assert result["alerts_90"] == 0
    mock_alert.assert_called_once_with(
        order_id="ORD-060", customer_email="ord-060@client.com",
        days_overdue=65, invoice_amount=1200.0, tier=2,
    )
    mock_update.assert_called_once_with("ORD-060", new_level=2)


def test_run_90day_processed_before_60day():
    """90d invoice must be processed first — it should NOT also appear in 60d list."""
    inv_90 = _invoice("ORD-090B", 92)

    calls = []

    def fake_get(min_days, max_level):
        calls.append((min_days, max_level))
        if min_days == 90:
            return [inv_90]
        return []

    with patch("agents.agent_11_ar_escalation.get_invoices_due_for_escalation",
               side_effect=fake_get), \
         patch("agents.agent_11_ar_escalation._send_teams_alert"), \
         patch("agents.agent_11_ar_escalation.update_ar_escalation_level"), \
         patch("agents.agent_11_ar_escalation.log_decision"):

        from agents.agent_11_ar_escalation import run
        run()

    assert calls[0][0] == 90, "90-day query must run first"
    assert calls[1][0] == 60, "60-day query must run second"


def test_run_no_alerts_when_no_overdue():
    with patch("agents.agent_11_ar_escalation.get_invoices_due_for_escalation",
               return_value=[]), \
         patch("agents.agent_11_ar_escalation._send_teams_alert") as mock_alert, \
         patch("agents.agent_11_ar_escalation.update_ar_escalation_level"), \
         patch("agents.agent_11_ar_escalation.log_decision"):

        from agents.agent_11_ar_escalation import run
        result = run()

    assert result == {"alerts_90": 0, "alerts_60": 0}
    mock_alert.assert_not_called()


def test_send_teams_alert_skipped_when_no_webhook():
    with patch("agents.agent_11_ar_escalation.TEAMS_WEBHOOK_URL", None), \
         patch("agents.agent_11_ar_escalation.httpx") as mock_httpx:
        from agents.agent_11_ar_escalation import _send_teams_alert
        _send_teams_alert("ORD-W", "x@y.com", 65, 500.0, tier=2)
    mock_httpx.post.assert_not_called()


def test_run_logs_decision_for_each_alert():
    inv = _invoice("ORD-LOG", 91)

    with patch("agents.agent_11_ar_escalation.get_invoices_due_for_escalation",
               side_effect=[[inv], []]), \
         patch("agents.agent_11_ar_escalation._send_teams_alert"), \
         patch("agents.agent_11_ar_escalation.update_ar_escalation_level"), \
         patch("agents.agent_11_ar_escalation.log_decision") as mock_log:

        from agents.agent_11_ar_escalation import run
        run()

    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args
    assert call_kwargs.kwargs.get("decision") == "day90_alert_sent" or \
           (len(call_kwargs.args) > 1 and call_kwargs.args[1] == "day90_alert_sent")
