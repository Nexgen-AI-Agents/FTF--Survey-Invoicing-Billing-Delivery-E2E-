import pytest
from unittest.mock import patch, call

from agents.agent_05_pricing_engine import price_order, AGENT_NAME
from core.exceptions import PricingError


# ── base classification dicts ─────────────────────────────────────────────────

_BASE_CLASS = {
    "order_id": "ORD-001",
    "service_type": "Boundary Survey",
    "pricing_tier": "individual",
    "elevation_cert_required": False,
    "special_pricing": False,
}

_FEMA_CLASS = {
    **_BASE_CLASS,
    "elevation_cert_required": True,
}

_B2B_CLASS = {
    **_BASE_CLASS,
    "pricing_tier": "b2b",
}

_OVERRIDE_CLASS = {
    **_BASE_CLASS,
    "special_pricing": True,
}


def _price(classification=None, api_response=None, overrides=None):
    """Helper: run price_order with external calls mocked."""
    cls = classification or _BASE_CLASS
    api_resp = api_response or {"price": 350.0}
    with patch("agents.agent_05_pricing_engine.get_pricing", return_value=api_resp), \
         patch("agents.agent_05_pricing_engine.get_pricing_overrides", return_value=overrides or {}), \
         patch("agents.agent_05_pricing_engine.save_order_state"), \
         patch("agents.agent_05_pricing_engine.log_decision"):
        return price_order(cls)


# ── UT-02-15  base price from FTF API ────────────────────────────────────────

def test_base_price_from_api():
    result = _price(api_response={"price": 350.0})
    assert result["base_amount"] == 350.0
    assert result["total_amount"] == 350.0
    assert result["pricing_source"] == "ftf_api"
    assert result["override_applied"] is False


def test_api_response_amount_key_fallback():
    # Some FTF endpoints return "amount" instead of "price"
    result = _price(api_response={"amount": 450.0})
    assert result["base_amount"] == 450.0


# ── UT-02-16  correct tier passed to pricing API ─────────────────────────────

def test_b2b_tier_passed_to_api():
    with patch("agents.agent_05_pricing_engine.get_pricing") as mock_get, \
         patch("agents.agent_05_pricing_engine.get_pricing_overrides", return_value={}), \
         patch("agents.agent_05_pricing_engine.save_order_state"), \
         patch("agents.agent_05_pricing_engine.log_decision"):
        mock_get.return_value = {"price": 300.0}
        price_order(_B2B_CLASS)

    mock_get.assert_called_once_with("Boundary Survey", tier="b2b")


def test_individual_tier_passed_to_api():
    with patch("agents.agent_05_pricing_engine.get_pricing") as mock_get, \
         patch("agents.agent_05_pricing_engine.get_pricing_overrides", return_value={}), \
         patch("agents.agent_05_pricing_engine.save_order_state"), \
         patch("agents.agent_05_pricing_engine.log_decision"):
        mock_get.return_value = {"price": 350.0}
        price_order(_BASE_CLASS)

    mock_get.assert_called_once_with("Boundary Survey", tier="individual")


# ── UT-02-17  elevation cert adds 225 ────────────────────────────────────────

def test_elevation_cert_adds_225():
    result = _price(classification=_FEMA_CLASS, api_response={"price": 350.0})
    assert result["base_amount"] == 350.0
    assert result["elevation_cert_amount"] == 225
    assert result["total_amount"] == 575.0


def test_no_elevation_cert_zero_added():
    result = _price(classification=_BASE_CLASS, api_response={"price": 350.0})
    assert result["elevation_cert_amount"] == 0
    assert result["total_amount"] == 350.0


# ── UT-02-18  special pricing override applied ────────────────────────────────

def test_override_applied_when_service_in_overrides():
    overrides = {"Boundary Survey": 200.0}
    result = _price(classification=_OVERRIDE_CLASS, overrides=overrides)
    assert result["base_amount"] == 200.0
    assert result["override_applied"] is True
    assert result["pricing_source"] == "override"


def test_override_dict_tier_lookup():
    # Override value is a dict with per-tier pricing
    overrides = {"Boundary Survey": {"individual": 200.0, "b2b": 175.0}}
    result = _price(classification=_OVERRIDE_CLASS, overrides=overrides)
    assert result["base_amount"] == 200.0
    assert result["override_applied"] is True


def test_override_dict_b2b_tier_lookup():
    overrides = {"Boundary Survey": {"individual": 200.0, "b2b": 175.0}}
    cls = {**_OVERRIDE_CLASS, "pricing_tier": "b2b"}
    result = _price(classification=cls, overrides=overrides)
    assert result["base_amount"] == 175.0


def test_special_pricing_no_override_falls_through_to_api():
    # Customer has special_pricing=True but no override entry for this service
    result = _price(
        classification=_OVERRIDE_CLASS,
        api_response={"price": 350.0},
        overrides={},  # empty — no override for this service
    )
    assert result["base_amount"] == 350.0
    assert result["override_applied"] is False
    assert result["pricing_source"] == "ftf_api"


# ── UT-02-19  DB persistence ─────────────────────────────────────────────────

def test_estimate_saved_to_db():
    with patch("agents.agent_05_pricing_engine.get_pricing", return_value={"price": 350.0}), \
         patch("agents.agent_05_pricing_engine.get_pricing_overrides", return_value={}), \
         patch("agents.agent_05_pricing_engine.save_order_state") as mock_save, \
         patch("agents.agent_05_pricing_engine.log_decision"):
        price_order(_BASE_CLASS)

    mock_save.assert_called_once()
    args, kwargs = mock_save.call_args
    assert args[0] == "ORD-001"
    assert kwargs["estimate_amount"] == 350.0
    assert kwargs["status"] == "priced"


def test_log_decision_called_once():
    with patch("agents.agent_05_pricing_engine.get_pricing", return_value={"price": 350.0}), \
         patch("agents.agent_05_pricing_engine.get_pricing_overrides", return_value={}), \
         patch("agents.agent_05_pricing_engine.save_order_state"), \
         patch("agents.agent_05_pricing_engine.log_decision") as mock_log:
        price_order(_BASE_CLASS)

    mock_log.assert_called_once()
    assert mock_log.call_args[1]["agent_name"] == AGENT_NAME
    assert mock_log.call_args[1]["decision"] == "priced"


# ── UT-02-20  PricingError propagates ────────────────────────────────────────

def test_pricing_api_error_propagates():
    with patch("agents.agent_05_pricing_engine.get_pricing",
               side_effect=PricingError("API down")), \
         patch("agents.agent_05_pricing_engine.get_pricing_overrides", return_value={}), \
         patch("agents.agent_05_pricing_engine.save_order_state"), \
         patch("agents.agent_05_pricing_engine.log_decision"):
        with pytest.raises(PricingError, match="API down"):
            price_order(_BASE_CLASS)


def test_override_error_flags_order_and_raises_agent_error():
    # I-057: overrides API unavailable → flag for human (not crash) — AgentError raised
    from core.exceptions import AgentError
    with patch("agents.agent_05_pricing_engine.get_pricing_overrides",
               side_effect=PricingError("overrides down")), \
         patch("agents.agent_05_pricing_engine.save_order_state") as mock_save, \
         patch("agents.agent_05_pricing_engine.log_decision"):
        with pytest.raises(AgentError, match="overrides API unavailable"):
            price_order(_OVERRIDE_CLASS)

    # DB must be updated to flagged status
    flag_save = mock_save.call_args
    assert flag_save[1].get("status") == "flagged"
    assert "overrides API unavailable" in flag_save[1].get("flag_reason", "")


# ── I-057: overrides fallback ─────────────────────────────────────────────────

def test_override_unavailable_does_not_use_standard_rate():
    # When overrides API fails, order must NOT be priced at standard rate
    from core.exceptions import AgentError
    with patch("agents.agent_05_pricing_engine.get_pricing_overrides",
               side_effect=PricingError("endpoint 404")), \
         patch("agents.agent_05_pricing_engine.get_pricing") as mock_get_pricing, \
         patch("agents.agent_05_pricing_engine.save_order_state"), \
         patch("agents.agent_05_pricing_engine.log_decision"):
        with pytest.raises(AgentError):
            price_order(_OVERRIDE_CLASS)

    mock_get_pricing.assert_not_called()


# ── UT-02-21  return dict structure ──────────────────────────────────────────

def test_return_dict_has_all_keys():
    result = _price()
    expected_keys = {
        "order_id", "base_amount", "elevation_cert_amount",
        "total_amount", "pricing_tier", "override_applied", "pricing_source",
    }
    assert expected_keys == set(result.keys())


def test_order_id_preserved_in_result():
    result = _price()
    assert result["order_id"] == "ORD-001"
