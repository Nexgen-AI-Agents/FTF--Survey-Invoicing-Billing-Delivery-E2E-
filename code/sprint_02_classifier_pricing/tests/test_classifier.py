import pytest
from unittest.mock import patch, call

from agents.agent_03_classifier import classify_order, AGENT_NAME
from core.exceptions import FEMAUnavailableError


# ── shared base order (clean, no flags) ──────────────────────────────────────

_BASE = {
    "service_type": "Boundary Survey",
    "customer_type": "individual",
    "special_pricing": False,
    "property_lat": 26.1224,
    "property_lng": -80.1373,
    "property_state": "FL",
    "property_county": "Broward",
    "customer_email": "client@example.com",
}


def _classify(order_override=None, fema_zone="X"):
    """Helper: run classify_order with DB/API mocked out."""
    order = {**_BASE, **(order_override or {})}
    with patch("agents.agent_03_classifier.get_order", return_value=order), \
         patch("agents.agent_03_classifier.check_flood_zone", return_value=fema_zone), \
         patch("agents.agent_03_classifier.save_order_state"), \
         patch("agents.agent_03_classifier.log_decision"):
        return classify_order("ORD-001")


# ── UT-02-01  customer type: individual ──────────────────────────────────────

def test_individual_customer_tier():
    result = _classify({"customer_type": "individual"})
    assert result["pricing_tier"] == "individual"
    assert result["flag_for_human"] is False


# ── UT-02-02  customer type: b2b ─────────────────────────────────────────────

def test_b2b_customer_tier():
    result = _classify({"customer_type": "b2b"})
    assert result["pricing_tier"] == "b2b"


def test_company_customer_maps_to_b2b():
    result = _classify({"customer_type": "company"})
    assert result["pricing_tier"] == "b2b"


# ── UT-02-03  ALWAYS_FLAG_SERVICES triggers flag ──────────────────────────────

def test_alta_survey_always_flags():
    result = _classify({"service_type": "ALTA Table A Survey"})
    assert result["flag_for_human"] is True
    assert "ALTA Table A Survey" in result["flag_reason"]


def test_other_services_always_flags():
    result = _classify({"service_type": "Other Services"})
    assert result["flag_for_human"] is True


# ── UT-02-04  NEVER_AUTO_QUOTE triggers flag ──────────────────────────────────

def test_specific_purpose_survey_flags():
    result = _classify({"service_type": "Specific Purpose Survey"})
    assert result["flag_for_human"] is True
    assert "never-auto-quote" in result["flag_reason"]


def test_lot_split_flags():
    result = _classify({"service_type": "Lot Split"})
    assert result["flag_for_human"] is True


def test_wetland_delineation_flags():
    result = _classify({"service_type": "Wetland Delineation"})
    assert result["flag_for_human"] is True


# ── UT-02-05  unresolved service_type flags ───────────────────────────────────

def test_quote_service_type_flags():
    # I-033: service_type="Quote" is FTF placeholder — flag for human
    result = _classify({"service_type": "Quote"})
    assert result["flag_for_human"] is True
    assert "Quote" in result["flag_reason"]


def test_empty_service_type_flags():
    result = _classify({"service_type": ""})
    assert result["flag_for_human"] is True


def test_none_service_type_flags():
    result = _classify({"service_type": None})
    assert result["flag_for_human"] is True


# ── UT-02-06  missing county flags (I-036) ────────────────────────────────────

def test_missing_county_flags():
    result = _classify({"property_county": ""})
    assert result["flag_for_human"] is True
    assert "county" in result["flag_reason"].lower()


def test_none_county_flags():
    result = _classify({"property_county": None})
    assert result["flag_for_human"] is True


# ── UT-02-07  false Florida coordinate flags (I-037) ─────────────────────────

def test_fl_state_lat_outside_florida_flags():
    # Florida northernmost point ≈ 31.0°N; 32.5 is Georgia
    result = _classify({"property_state": "FL", "property_lat": 32.5})
    assert result["flag_for_human"] is True
    assert "FL" in result["flag_reason"]


def test_fl_state_valid_lat_no_false_flag():
    # 25.77 = Miami — valid Florida lat, must NOT trigger I-037
    result = _classify({"property_state": "FL", "property_lat": 25.77})
    assert result["flag_for_human"] is False


def test_non_fl_state_high_lat_no_flag():
    # Georgia address — property_state != FL, so I-037 guard must not fire
    result = _classify({"property_state": "GA", "property_lat": 33.5})
    assert result["flag_for_human"] is False


# ── UT-02-08  flood zone — elevation cert required ────────────────────────────

def test_flood_zone_ae_sets_elevation_cert():
    result = _classify(fema_zone="AE")
    assert result["is_flood_zone"] is True
    assert result["elevation_cert_required"] is True
    assert result["flood_zone"] == "AE"


def test_flood_zone_a_sets_elevation_cert():
    result = _classify(fema_zone="A")
    assert result["is_flood_zone"] is True
    assert result["elevation_cert_required"] is True


def test_flood_zone_x_no_elevation_cert():
    result = _classify(fema_zone="X")
    assert result["is_flood_zone"] is False
    assert result["elevation_cert_required"] is False
    assert result["flag_for_human"] is False


# ── UT-02-09  VE zone triggers coastal flag (I-035) ──────────────────────────

def test_ve_zone_triggers_coastal_flag():
    result = _classify(fema_zone="VE")
    assert result["flag_for_human"] is True
    assert "VE" in result["flag_reason"]
    assert result["is_flood_zone"] is True
    assert result["elevation_cert_required"] is True


def test_v_zone_triggers_coastal_flag():
    result = _classify(fema_zone="V")
    assert result["flag_for_human"] is True


# ── UT-02-10  FEMA unavailable flags ─────────────────────────────────────────

def test_fema_unavailable_flags():
    order = {**_BASE}
    with patch("agents.agent_03_classifier.get_order", return_value=order), \
         patch("agents.agent_03_classifier.check_flood_zone",
               side_effect=FEMAUnavailableError("timeout")), \
         patch("agents.agent_03_classifier.save_order_state"), \
         patch("agents.agent_03_classifier.log_decision"):
        result = classify_order("ORD-001")

    assert result["flag_for_human"] is True
    assert "FEMA" in result["flag_reason"]
    assert result["flood_zone"] == "UNAVAILABLE"


# ── UT-02-11  DB persistence: status values ───────────────────────────────────

def test_clean_order_saves_classified_status():
    order = {**_BASE}
    with patch("agents.agent_03_classifier.get_order", return_value=order), \
         patch("agents.agent_03_classifier.check_flood_zone", return_value="X"), \
         patch("agents.agent_03_classifier.save_order_state") as mock_save, \
         patch("agents.agent_03_classifier.log_decision"):
        classify_order("ORD-001")

    kwargs = mock_save.call_args[1]
    assert kwargs["status"] == "classified"


def test_flagged_order_saves_flagged_status():
    order = {**_BASE, "service_type": "ALTA Table A Survey"}
    with patch("agents.agent_03_classifier.get_order", return_value=order), \
         patch("agents.agent_03_classifier.check_flood_zone", return_value="X"), \
         patch("agents.agent_03_classifier.save_order_state") as mock_save, \
         patch("agents.agent_03_classifier.log_decision"):
        classify_order("ORD-001")

    kwargs = mock_save.call_args[1]
    assert kwargs["status"] == "flagged"
    assert "flag_reason" in kwargs


# ── UT-02-12  log_decision called once per order ─────────────────────────────

def test_log_decision_called_once():
    order = {**_BASE}
    with patch("agents.agent_03_classifier.get_order", return_value=order), \
         patch("agents.agent_03_classifier.check_flood_zone", return_value="X"), \
         patch("agents.agent_03_classifier.save_order_state"), \
         patch("agents.agent_03_classifier.log_decision") as mock_log:
        classify_order("ORD-001")

    mock_log.assert_called_once()
    assert mock_log.call_args[1]["agent_name"] == AGENT_NAME


# ── UT-02-13  no FEMA call when coordinates absent ───────────────────────────

def test_no_fema_call_when_coords_missing():
    order = {**_BASE, "property_lat": None, "property_lng": None}
    with patch("agents.agent_03_classifier.get_order", return_value=order), \
         patch("agents.agent_03_classifier.check_flood_zone") as mock_fema, \
         patch("agents.agent_03_classifier.save_order_state"), \
         patch("agents.agent_03_classifier.log_decision"):
        result = classify_order("ORD-001")

    mock_fema.assert_not_called()
    assert result["flood_zone"] == "UNKNOWN"


# ── UT-02-14  multiple flag reasons accumulate ───────────────────────────────

def test_multiple_flags_accumulate_in_reason():
    # Missing county + VE zone should both appear in flag_reason
    order = {**_BASE, "property_county": ""}
    with patch("agents.agent_03_classifier.get_order", return_value=order), \
         patch("agents.agent_03_classifier.check_flood_zone", return_value="VE"), \
         patch("agents.agent_03_classifier.save_order_state"), \
         patch("agents.agent_03_classifier.log_decision"):
        result = classify_order("ORD-001")

    assert result["flag_for_human"] is True
    assert "county" in result["flag_reason"].lower()
    assert "VE" in result["flag_reason"]
