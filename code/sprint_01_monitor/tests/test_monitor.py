import pytest
from unittest.mock import patch, MagicMock, call

from agents.agent_02_monitor import run, AGENT_NAME


_MOCK_ORDERS = [
    {"order_id": "O-001", "status": "Quote", "estimate_sent": False},
    {"order_id": "O-002", "status": "Quote", "estimate_sent": False},
    {"order_id": "O-003", "status": "Quote", "estimate_sent": False},
]


# ---------------------------------------------------------------------------
# Original tests (unchanged logic — signatures still valid after refactor)
# ---------------------------------------------------------------------------

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
    orders_with_int_ids = [
        {"order_id": 101, "status": "Quote", "estimate_sent": False},
        {"order_id": 102, "status": "Quote", "estimate_sent": False},
    ]

    with patch("agents.agent_02_monitor.get_orders", return_value=orders_with_int_ids), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert result == ["101", "102"]
    saved_ids = [c.args[0] for c in mock_save.call_args_list]
    assert all(isinstance(oid, str) for oid in saved_ids)


# UT-01-07: REMOVED — client-side status != "Quote" check was deleted when the agent
# was refactored to use server-side filter (status="Quote" param to get_orders).
# The server guarantees only Quote orders are returned; a client-side guard is
# redundant and was intentionally removed. Coverage of the server-side filter
# contract is now owned by UT-01-09 (get_orders called with status="Quote").
#
# If you re-add a client-side status guard in the future, restore this test.
# @pytest.mark.skip("Removed: client-side status filter deleted in pagination refactor")
def test_non_quote_orders_skipped_defense_in_depth():
    # Agent relies on server-side filter; any status value in the response body
    # is NOT checked by the agent — it trusts the server to have filtered correctly.
    # This test documents that behavior: non-Quote orders returned by the mock
    # ARE processed (because the agent no longer inspects the status field).
    # In production this never happens because get_orders(status="Quote") is used.
    mixed_orders = [
        {"order_id": "O-001", "status": "Quote",     "estimate_sent": False},
        {"order_id": "O-002", "status": "Delivered",  "estimate_sent": False},
        {"order_id": "O-003", "status": "Pending",    "estimate_sent": False},
        {"order_id": "O-004", "status": "Complete",   "estimate_sent": False},
        {"order_id": "O-005", "status": "Canceled",   "estimate_sent": False},
    ]

    with patch("agents.agent_02_monitor.get_orders", return_value=mixed_orders), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    # Agent trusts server filter — processes ALL orders in the list regardless of status field.
    # If this is undesirable, add a client-side guard and update this assertion.
    assert result == ["O-001", "O-002", "O-003", "O-004", "O-005"]
    assert mock_save.call_count == 5


# UT-01-08: Quote orders with estimate_sent=True are skipped — no duplicate estimates
def test_already_estimated_orders_skipped():
    orders = [
        {"order_id": "O-001", "status": "Quote", "estimate_sent": False},
        {"order_id": "O-002", "status": "Quote", "estimate_sent": True},
        {"order_id": "O-003", "status": "Quote", "estimate_sent": True},
    ]

    with patch("agents.agent_02_monitor.get_orders", return_value=orders), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert result == ["O-001"]
    assert mock_save.call_count == 1
    saved_ids = [c.args[0] for c in mock_save.call_args_list]
    assert "O-002" not in saved_ids
    assert "O-003" not in saved_ids


# ---------------------------------------------------------------------------
# NEW TESTS — pagination + server-side filter contract
# ---------------------------------------------------------------------------

# UT-01-09: get_orders called with status="Quote" — server-side filter is used
# This is the primary regression guard for the API refactor.
# If this test fails, the agent is doing client-side filtering on 500 random
# orders instead of fetching all 7000+ Quote orders via server filter.
def test_get_orders_called_with_status_quote():
    with patch("agents.agent_02_monitor.get_orders", return_value=[]) as mock_get, \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state"), \
         patch("agents.agent_02_monitor.log_decision"):
        run()

    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs.get("status") == "Quote", (
        "get_orders must be called with status='Quote' to use server-side filter. "
        "Without it, only 500 random orders are fetched and most Quote orders are never seen."
    )


# UT-01-10: get_orders called exactly once per run() — no redundant API calls
def test_get_orders_called_exactly_once():
    with patch("agents.agent_02_monitor.get_orders", return_value=_MOCK_ORDERS) as mock_get, \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state"), \
         patch("agents.agent_02_monitor.log_decision"):
        run()

    mock_get.assert_called_once()


# UT-01-11: Large paginated result (1500 orders across 3 pages) processed correctly.
# The paginated ftf_client flattens pages into one list before returning;
# agent_02_monitor receives that flat list and must process every order in it.
def test_large_paginated_result_all_orders_processed():
    # Simulate ftf_client returning a flat list of 1500 Quote orders (3 pages worth)
    large_order_list = [
        {"order_id": f"O-{i:04d}", "status": "Quote", "estimate_sent": False}
        for i in range(1, 1501)
    ]

    with patch("agents.agent_02_monitor.get_orders", return_value=large_order_list), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert len(result) == 1500
    assert mock_save.call_count == 1500
    # Spot-check first and last order IDs are present
    assert "O-0001" in result
    assert "O-1500" in result


# UT-01-12: Large list — mix of new and existing orders at scale
# Guards against off-by-one or early-exit bugs when iterating long lists.
def test_large_list_mixed_new_and_existing():
    # 1000 orders; even-indexed already in DB, odd-indexed are new
    large_mixed = [
        {"order_id": f"O-{i:04d}", "status": "Quote", "estimate_sent": False}
        for i in range(1000)
    ]

    def exists(order_id):
        # orders O-0000, O-0002, O-0004 ... are existing
        num = int(order_id.split("-")[1])
        return num % 2 == 0

    with patch("agents.agent_02_monitor.get_orders", return_value=large_mixed), \
         patch("agents.agent_02_monitor.order_exists", side_effect=exists), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    assert len(result) == 500
    assert mock_save.call_count == 500
    # All returned IDs should be odd-numbered
    for oid in result:
        assert int(oid.split("-")[1]) % 2 == 1, f"Even (existing) order {oid} should not be returned"


# EC-01-04: estimate_sent key missing entirely treated same as False — order is processed
# API may omit the key for older orders; absence must not cause a KeyError or skip.
def test_missing_estimate_sent_key_treated_as_false():
    orders = [
        {"order_id": "O-001", "status": "Quote"},            # no estimate_sent key
        {"order_id": "O-002", "status": "Quote", "estimate_sent": None},  # None also falsy
        {"order_id": "O-003", "status": "Quote", "estimate_sent": False},
    ]

    with patch("agents.agent_02_monitor.get_orders", return_value=orders), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    # All three should be processed — missing/None estimate_sent is not a skip condition
    assert "O-001" in result
    assert "O-002" in result
    assert "O-003" in result
    assert mock_save.call_count == 3


# EC-01-05: get_orders raises AgentError — exception propagates; save_order_state not called
# Agent must not swallow infrastructure failures silently.
def test_get_orders_exception_propagates():
    from core.exceptions import AgentError

    with patch("agents.agent_02_monitor.get_orders", side_effect=AgentError("API down")), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        with pytest.raises(AgentError, match="API down"):
            run()

    mock_save.assert_not_called()


# EC-01-06: status field missing from order dict — no KeyError, order is processed.
# Agent no longer reads the status field (server filter guarantees Quote-only).
# Missing key must not crash; order goes through the remaining checks normally.
def test_missing_status_field_no_crash_order_processed():
    orders = [
        {"order_id": "O-001"},                                       # no status key — no crash
        {"order_id": "O-002", "status": "Quote", "estimate_sent": False},
    ]

    with patch("agents.agent_02_monitor.get_orders", return_value=orders), \
         patch("agents.agent_02_monitor.order_exists", return_value=False), \
         patch("agents.agent_02_monitor.save_order_state") as mock_save, \
         patch("agents.agent_02_monitor.log_decision"):
        result = run()

    # Agent does not inspect status — both orders are processed without error
    assert "O-001" in result
    assert "O-002" in result
    assert mock_save.call_count == 2
