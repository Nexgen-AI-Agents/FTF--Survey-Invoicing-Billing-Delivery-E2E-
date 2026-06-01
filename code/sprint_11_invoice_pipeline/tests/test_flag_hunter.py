"""Tests for A1 Flag Hunter."""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))


def test_run_no_orders():
    with patch("agents.agent_a1_flag_hunter.get_invoice_needed_orders", return_value=[]), \
         patch("agents.agent_a1_flag_hunter.order_exists", return_value=False):
        import importlib
        import agents.agent_a1_flag_hunter as m
        importlib.reload(m)
        result = m.run()
        assert result == []


def test_run_skips_existing_orders():
    orders = [{"order_id": "TEST-001", "service_type": "Land Survey Only"}]
    with patch("agents.agent_a1_flag_hunter.get_invoice_needed_orders", return_value=orders), \
         patch("agents.agent_a1_flag_hunter.order_exists", return_value=True), \
         patch("agents.agent_a1_flag_hunter.save_order_state") as mock_save:
        import importlib
        import agents.agent_a1_flag_hunter as m
        importlib.reload(m)
        result = m.run()
        assert result == []
        mock_save.assert_not_called()


def test_run_queues_new_order():
    orders = [{
        "order_id": "TEST-002",
        "service_type": "Land Survey Only",
        "customer_email": "client@example.com",
        "customer_name": "John Smith",
        "property_address": "123 Main St",
        "status": "Assigned",
    }]
    with patch("agents.agent_a1_flag_hunter.get_invoice_needed_orders", return_value=orders), \
         patch("agents.agent_a1_flag_hunter.order_exists", return_value=False), \
         patch("agents.agent_a1_flag_hunter.save_order_state") as mock_save, \
         patch("agents.agent_a1_flag_hunter.log_decision"):
        import importlib
        import agents.agent_a1_flag_hunter as m
        importlib.reload(m)
        result = m.run()
        assert "TEST-002" in result
        mock_save.assert_called_once()
