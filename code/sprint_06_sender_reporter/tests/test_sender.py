"""Unit tests for Agent 8 — Sender (includes I-024: send window + retry logic)."""
import pytest
from unittest.mock import MagicMock, patch

from agents.agent_08_sender import run, send_estimate
from core.exceptions import AgentError

# ── fixtures ─────────────────────────────────────────────────────────────────

_DB_ROW_REVIEWED = {
    "order_id": "ORD-600",
    "status": "reviewed",
    "estimate_amount": 350.00,
    "service_type": "Boundary Survey",
}

_DB_ROW_PRICED = {
    "order_id": "ORD-601",
    "status": "priced",
    "estimate_amount": 450.00,
    "service_type": "Acreage",
}

_INVOICE_RESPONSE = {"invoice_id": "INV-999", "amount": 350.00}

# ── happy-path tests (all mock _in_send_window=True) ─────────────────────────


def test_send_estimate_creates_and_sends_invoice():
    with (
        patch("agents.agent_08_sender._in_send_window", return_value=True),
        patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_REVIEWED),
        patch("agents.agent_08_sender.create_invoice", return_value=_INVOICE_RESPONSE) as mock_create,
        patch("agents.agent_08_sender.send_invoice") as mock_send,
        patch("agents.agent_08_sender.mark_estimate_sent") as mock_mark,
        patch("agents.agent_08_sender.save_order_state"),
        patch("agents.agent_08_sender.log_decision"),
        patch("agents.agent_08_sender.time.sleep"),
    ):
        result = send_estimate("ORD-600")

    mock_create.assert_called_once_with(
        "ORD-600", 350.00, [{"name": "Boundary Survey", "amount": 350.00}]
    )
    mock_send.assert_called_once_with("INV-999")
    mock_mark.assert_called_once_with("ORD-600")
    assert result["status"] == "sent"
    assert result["invoice_id"] == "INV-999"


def test_send_estimate_updates_db_to_sent():
    with (
        patch("agents.agent_08_sender._in_send_window", return_value=True),
        patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_REVIEWED),
        patch("agents.agent_08_sender.create_invoice", return_value=_INVOICE_RESPONSE),
        patch("agents.agent_08_sender.send_invoice"),
        patch("agents.agent_08_sender.mark_estimate_sent"),
        patch("agents.agent_08_sender.save_order_state") as mock_save,
        patch("agents.agent_08_sender.log_decision"),
        patch("agents.agent_08_sender.time.sleep"),
    ):
        send_estimate("ORD-600")

    # First call is the success save — check it
    success_call = mock_save.call_args_list[-1]
    assert success_call[0][0] == "ORD-600"
    assert success_call[1].get("status") == "sent"
    assert "sent_at" in success_call[1]


def test_send_estimate_logs_decision():
    with (
        patch("agents.agent_08_sender._in_send_window", return_value=True),
        patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_REVIEWED),
        patch("agents.agent_08_sender.create_invoice", return_value=_INVOICE_RESPONSE),
        patch("agents.agent_08_sender.send_invoice"),
        patch("agents.agent_08_sender.mark_estimate_sent"),
        patch("agents.agent_08_sender.save_order_state"),
        patch("agents.agent_08_sender.log_decision") as mock_log,
        patch("agents.agent_08_sender.time.sleep"),
    ):
        send_estimate("ORD-600")

    mock_log.assert_called_once()
    args = mock_log.call_args[1]
    assert args["decision"] == "sent"
    assert args["order_id"] == "ORD-600"


def test_send_estimate_applies_delay():
    from config.settings import ESTIMATE_DELAY_MAX, ESTIMATE_DELAY_MIN

    with (
        patch("agents.agent_08_sender._in_send_window", return_value=True),
        patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_REVIEWED),
        patch("agents.agent_08_sender.create_invoice", return_value=_INVOICE_RESPONSE),
        patch("agents.agent_08_sender.send_invoice"),
        patch("agents.agent_08_sender.mark_estimate_sent"),
        patch("agents.agent_08_sender.save_order_state"),
        patch("agents.agent_08_sender.log_decision"),
        patch("agents.agent_08_sender.time.sleep") as mock_sleep,
        patch("agents.agent_08_sender.random.randint", return_value=500) as mock_rand,
    ):
        send_estimate("ORD-600")

    mock_rand.assert_called_once_with(ESTIMATE_DELAY_MIN, ESTIMATE_DELAY_MAX)
    mock_sleep.assert_called_once_with(500)


# ── error-path tests ──────────────────────────────────────────────────────────


def test_send_estimate_raises_on_missing_order():
    with patch("agents.agent_08_sender.get_order_by_id", return_value=None):
        with pytest.raises(AgentError, match="not found"):
            send_estimate("ORD-GONE")


def test_send_estimate_raises_on_wrong_status():
    with patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_PRICED):
        with pytest.raises(AgentError, match="expected 'reviewed'"):
            send_estimate("ORD-601")


def test_send_estimate_raises_on_zero_amount():
    zero_row = {**_DB_ROW_REVIEWED, "estimate_amount": 0.0}
    with patch("agents.agent_08_sender.get_order_by_id", return_value=zero_row):
        with pytest.raises(AgentError, match="no estimate amount"):
            send_estimate("ORD-600")


# ── I-024: send window tests ──────────────────────────────────────────────────


def test_send_estimate_returns_none_outside_send_window():
    with (
        patch("agents.agent_08_sender._in_send_window", return_value=False),
        patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_REVIEWED),
        patch("agents.agent_08_sender.create_invoice") as mock_create,
        patch("agents.agent_08_sender.time.sleep"),
    ):
        result = send_estimate("ORD-600")

    assert result is None
    mock_create.assert_not_called()


def test_send_estimate_retries_on_transient_failure():
    """First create_invoice call raises; second succeeds — result is 'sent'."""
    with (
        patch("agents.agent_08_sender._in_send_window", return_value=True),
        patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_REVIEWED),
        patch(
            "agents.agent_08_sender.create_invoice",
            side_effect=[Exception("network error"), _INVOICE_RESPONSE],
        ) as mock_create,
        patch("agents.agent_08_sender.send_invoice"),
        patch("agents.agent_08_sender.mark_estimate_sent"),
        patch("agents.agent_08_sender.save_order_state"),
        patch("agents.agent_08_sender.log_decision"),
        patch("agents.agent_08_sender.time.sleep"),
    ):
        result = send_estimate("ORD-600")

    assert mock_create.call_count == 2
    assert result["status"] == "sent"


def test_send_estimate_marks_error_after_max_retries():
    """All MAX_SENDER_RETRIES attempts fail — status saved as 'error', AgentError raised."""
    from config.settings import MAX_SENDER_RETRIES

    with (
        patch("agents.agent_08_sender._in_send_window", return_value=True),
        patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_REVIEWED),
        patch(
            "agents.agent_08_sender.create_invoice",
            side_effect=Exception("FTF API down"),
        ) as mock_create,
        patch("agents.agent_08_sender.save_order_state") as mock_save,
        patch("agents.agent_08_sender.log_decision"),
        patch("agents.agent_08_sender.time.sleep"),
    ):
        with pytest.raises(AgentError, match=f"failed after {MAX_SENDER_RETRIES} attempts"):
            send_estimate("ORD-600")

    assert mock_create.call_count == MAX_SENDER_RETRIES
    error_save = mock_save.call_args
    assert error_save[1].get("status") == "error"


# ── run() tests ───────────────────────────────────────────────────────────────


def test_run_picks_reviewed_order():
    with (
        patch("agents.agent_08_sender.get_reviewed_order", return_value=_DB_ROW_REVIEWED) as mock_get,
        patch("agents.agent_08_sender._in_send_window", return_value=True),
        patch("agents.agent_08_sender.get_order_by_id", return_value=_DB_ROW_REVIEWED),
        patch("agents.agent_08_sender.create_invoice", return_value=_INVOICE_RESPONSE),
        patch("agents.agent_08_sender.send_invoice"),
        patch("agents.agent_08_sender.mark_estimate_sent"),
        patch("agents.agent_08_sender.save_order_state"),
        patch("agents.agent_08_sender.log_decision"),
        patch("agents.agent_08_sender.time.sleep"),
    ):
        result = run()

    mock_get.assert_called_once()
    assert result is not None
    assert result["status"] == "sent"
