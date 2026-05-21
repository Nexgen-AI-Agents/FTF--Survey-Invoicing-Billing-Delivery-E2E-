import pytest
from unittest.mock import patch, MagicMock, call

from agents.agent_02_monitor import run, AGENT_NAME


_MOCK_ORDERS = [{"id": "O-001"}, {"id": "O-002"}, {"id": "O-003"}]


def _patch_all(orders, exists_fn):
    return (
        patch("agents.agent_02_monitor.get_orders", return_value=orders),
        patch("agents.agent_02_monitor.order_exists", side_effect=exists_fn),
        patch("agents.agent_02_monitor.save_order_state"),
        patch("agents.agent_02_monitor.log_decision"),
    )


# UT-01-01: 3 new orders — all written
def test_three_new_orders_all_written():
    with patch("agents.agent_02_monitor.get_orders", return_value=_MOCK_ORDERS), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert result == ["O-001", "O-002", "O-003"]
    assert mock_save.call_count == 3


# UT-01-02: 1 already in DB — skipped; existing order NOT reset
def test_existing_order_skipped_and_not_reset():
    def exists(order_id):
        return order_id == "O-001"

    with patch("agents.agent_02_monitor.get_orders", return_value=_MOCK_ORDERS), \
         patch("agents.agent_02_monitor.order_exists", side_effect=exists), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert result == ["O-002", "O-003"]
    assert mock_save.call_count == 2
    saved_ids = [c.args[0] for c in mock_save.call_args_list]
    assert "O-001" not in saved_ids


# UT-01-03: Empty API response — no errors, empty list returned
def test_empty_api_response_no_errors():
    with patch("agents.agent_02_monitor.get_orders", return_value=[]), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert result == []
    mock_save.assert_not_called()


# UT-01-04: All orders already in DB — nothing written
def test_all_existing_nothing_written():
    with patch("agents.agent_02_monitor.get_orders", return_value=_MOCK_ORDERS), \
         patch("agents.agent_02_monitor.order_exists", return_value=True), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert result == []
    mock_save.assert_not_called()


# UT-01-05: log_decision called once per new order with correct agent name
def test_log_decision_called_per_new_order():
    with patch("agents.agent_02_monitor.get_orders", return_value=_MOCK_ORDERS), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state"), \
         patch("agents.agent_02_monitor.log_decision") as mock_log:
        run()

    assert mock_log.call_count == 3
    for c in mock_log.call_args_list:
        assert c.args[0] == AGENT_NAME


# UT-01-06: No LLM call is ever made
def test_no_llm_call():
    with patch("agents.agent_02_monitor.get_orders", return_value=_MOCK_ORDERS), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state"), \
         patch("agents.agent_02_monitor.log_decision"), \
         patch("core.claude_client.call") as mock_llm:
        run()

    mock_llm.assert_not_called()


# EC-01-03: Numeric order IDs from FTF cast to string correctly
def test_numeric_order_id_cast_to_string():
    orders_with_int_ids = [{"id": 101}, {"id": 102}]

    with patch("agents.agent_02_monitor.get_orders", return_value=orders_with_int_ids), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert result == ["101", "102"]
    saved_ids = [c.args[0] for c in mock_save.call_args_list]
    assert all(isinstance(oid, str) for oid in saved_ids)
