import pytest
import httpx
from unittest.mock import patch, MagicMock
from core.ftf_client import (
    health_check, get_orders, get_order, get_pricing,
    create_invoice, send_invoice, send_reminder, mark_estimate_sent,
    create_order,
)
from core.exceptions import AgentError, PricingError


def _mock_response(status_code=200, json_data=None):
    r = MagicMock(spec=httpx.Response)
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.raise_for_status = MagicMock()
    if status_code >= 400:
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=r
        )
    return r


@patch("core.ftf_client.httpx.get")
def test_health_check_true_on_200(mock_get):
    mock_get.return_value = _mock_response(200)
    assert health_check() is True


@patch("core.ftf_client.httpx.get")
def test_health_check_false_on_error(mock_get):
    mock_get.side_effect = Exception("connection refused")
    assert health_check() is False


@patch("core.ftf_client.httpx.get")
def test_get_orders_returns_list(mock_get):
    mock_get.return_value = _mock_response(200, [{"order_id": "ORD-001"}])
    result = get_orders(limit=1)
    assert result == [{"order_id": "ORD-001"}]


@patch("core.ftf_client.httpx.get")
def test_get_orders_raises_agent_error_on_http_error(mock_get):
    mock_get.return_value = _mock_response(500)
    with pytest.raises(AgentError):
        get_orders()


@patch("core.ftf_client.httpx.get")
def test_get_pricing_raises_pricing_error_on_failure(mock_get):
    mock_get.side_effect = Exception("timeout")
    with pytest.raises(PricingError):
        get_pricing("Boundary Survey")


@patch("core.ftf_client.httpx.post")
def test_create_invoice_returns_dict(mock_post):
    mock_post.return_value = _mock_response(201, {"invoice_id": "INV-001"})
    result = create_invoice("ORD-001", 350.0, [{"name": "Boundary Survey", "price": 350}])
    assert result["invoice_id"] == "INV-001"


@patch("core.ftf_client.httpx.post")
def test_send_invoice_returns_true(mock_post):
    mock_post.return_value = _mock_response(200)
    assert send_invoice("INV-001") is True


@patch("core.ftf_client.httpx.patch")
def test_mark_estimate_sent_returns_true(mock_patch):
    mock_patch.return_value = _mock_response(200)
    assert mark_estimate_sent("ORD-001") is True


@patch("core.ftf_client.httpx.post")
def test_create_order_returns_dict_on_success(mock_post):
    mock_post.return_value = _mock_response(201, {"order_id": "12345"})
    result = create_order({"service_type": "Boundary Survey"})
    assert result["order_id"] == "12345"


@patch("core.ftf_client.httpx.post")
def test_create_order_raises_agent_error_on_404(mock_post):
    mock_post.return_value = _mock_response(404)
    with pytest.raises(AgentError, match="does not support order creation"):
        create_order({"service_type": "Boundary Survey"})
