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


# ── UT-02-05b  informal survey type flags (I-003) ────────────────────────────

def test_construction_permitting_flags():
    # I-003: "Construction/Permitting" is an informal CRM bundle label — not a priced service.
    # Must flag for human review regardless of case.
    result = _classify({"service_type": "Construction/Permitting"})
    assert result["flag_for_human"] is True
    assert "informal survey type" in result["flag_reason"]
    assert "Construction/Permitting" in result["flag_reason"]


def test_construction_permitting_case_insensitive():
    result = _classify({"service_type": "construction/permitting"})
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


def test_non_fl_state_high_lat_i037_does_not_fire():
    # I-037 guard only fires when property_state=FL. A GA address must NOT
    # trigger "outside Florida bounds" — it triggers out-of-state (Trigger 9) instead.
    result = _classify({"property_state": "GA", "property_lat": 33.5})
    assert result["flag_for_human"] is True  # out-of-state Trigger 9 fires
    assert "FL-only" in result["flag_reason"]
    assert "outside Florida bounds" not in result["flag_reason"]  # I-037 must NOT fire


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


# ── UT-02-15  Trigger 3: competitor company name match ───────────────────────

def test_competitor_company_name_flags():
    order = {**_BASE, "company_name": "Apex Surveying & Mapping"}
    result = _classify(order)
    assert result["flag_for_human"] is True
    assert "competitor company name" in result["flag_reason"].lower()


def test_competitor_name_substring_match_flags():
    # "Apex Surveying" is a substring of "Apex Surveying Florida LLC"
    order = {**_BASE, "company_name": "Apex Surveying Florida LLC"}
    result = _classify(order)
    assert result["flag_for_human"] is True


def test_non_competitor_company_no_flag():
    order = {**_BASE, "company_name": "Smith Family Properties"}
    result = _classify(order)
    assert result["flag_for_human"] is False


# ── UT-02-16  Trigger 4: competitor email domain match ───────────────────────

def test_competitor_email_domain_flags():
    order = {**_BASE, "customer_email": "info@apexsurvey.us"}
    result = _classify(order)
    assert result["flag_for_human"] is True
    assert "apexsurvey.us" in result["flag_reason"]


def test_non_competitor_email_no_flag():
    order = {**_BASE, "customer_email": "client@gmail.com"}
    result = _classify(order)
    assert result["flag_for_human"] is False


def test_email_without_at_no_crash():
    # Malformed email must not crash the classifier
    order = {**_BASE, "customer_email": "not-an-email"}
    result = _classify(order)
    assert result["flag_for_human"] is False


# ── UT-02-17  Trigger 9: out-of-state property ───────────────────────────────

def test_georgia_property_flags():
    result = _classify({"property_state": "GA", "property_lat": 33.5, "property_lng": -84.4})
    assert result["flag_for_human"] is True
    assert "FL-only" in result["flag_reason"]


def test_fl_property_does_not_trigger_out_of_state():
    result = _classify({"property_state": "FL"})
    # Out-of-state trigger must NOT fire for FL orders
    assert not any("FL-only" in r for r in (result["flag_reason"] or "").split("; "))


def test_empty_state_does_not_trigger_out_of_state():
    # Missing state field — no out-of-state flag (separate data quality check)
    result = _classify({"property_state": ""})
    assert not any("FL-only" in r for r in (result["flag_reason"] or "").split("; "))


# ── UT-02-18  I-034: Monroe County (Florida Keys) ────────────────────────────

def test_monroe_county_flags():
    result = _classify({"property_county": "Monroe"})
    assert result["flag_for_human"] is True
    assert "Monroe" in result["flag_reason"]


def test_monroe_county_case_insensitive():
    result = _classify({"property_county": "monroe county"})
    assert result["flag_for_human"] is True


def test_broward_county_no_monroe_flag():
    result = _classify({"property_county": "Broward"})
    assert result["flag_for_human"] is False


# ── I-050: property_state normalization (FTF API returns "FLORIDA" not "FL") ─

def test_florida_full_name_not_flagged_as_out_of_state():
    result = _classify({"property_state": "FLORIDA"})
    assert "FL-only" not in (result["flag_reason"] or "")


def test_florida_mixed_case_not_flagged():
    result = _classify({"property_state": "Florida"})
    assert "FL-only" not in (result["flag_reason"] or "")


def test_florida_lat_check_works_after_state_normalization():
    # After "FLORIDA" normalizes to "FL", the I-037 lat-bounds check must still fire
    result = _classify({"property_state": "FLORIDA", "property_lat": 35.0})
    assert result["flag_for_human"] is True
    assert "outside Florida bounds" in result["flag_reason"]
    assert "FL-only" not in result["flag_reason"]


# ── I-053: service type alias normalization + LLM fallback ───────────────────

def test_alias_land_survey_only_maps_to_boundary_survey():
    result = _classify({"service_type": "Land Survey Only"})
    assert result["flag_for_human"] is False
    assert result["service_type"] == "Boundary Survey"


def test_alias_special_purpose_maps_to_specific_purpose_and_flags():
    # "Special Purpose Survey" -> "Specific Purpose Survey" which is NEVER_AUTO_QUOTE
    result = _classify({"service_type": "Special Purpose Survey"})
    assert result["flag_for_human"] is True
    assert "never-auto-quote" in result["flag_reason"]


def test_alias_construction_survey_maps_to_topography():
    # "Construction Survey" -> "Topography Survey" (Robert confirmed).
    # "Topography Survey" is currently in NEVER_AUTO_QUOTE (I-054 — unresolved).
    # So mapping is correct; order is flagged until I-054 removes it from NEVER_AUTO_QUOTE.
    result = _classify({"service_type": "Construction Survey"})
    assert result["service_type"] == "Topography Survey"
    assert result["flag_for_human"] is True
    assert "never-auto-quote" in result["flag_reason"]


def test_unrecognized_service_type_calls_llm_and_uses_result():
    with patch("agents.agent_03_classifier._llm_normalize_service_type", return_value="Boundary Survey") as mock_llm:
        result = _classify({"service_type": "Re-plot Survey"})
    mock_llm.assert_called_once_with("Re-plot Survey")
    assert result["service_type"] == "Boundary Survey"
    assert result["flag_for_human"] is False


def test_llm_returns_unrecognized_sentinel_flags_order():
    from agents.agent_03_classifier import _UNRECOGNIZED
    with patch("agents.agent_03_classifier._llm_normalize_service_type", return_value=_UNRECOGNIZED):
        result = _classify({"service_type": "Drone Mapping Service"})
    assert result["flag_for_human"] is True
    assert "unrecognized" in result["flag_reason"].lower()
    assert "Drone Mapping Service" in result["flag_reason"]


def test_canonical_service_type_skips_llm():
    with patch("agents.agent_03_classifier._llm_normalize_service_type") as mock_llm:
        result = _classify({"service_type": "Boundary Survey"})
    mock_llm.assert_not_called()
    assert result["flag_for_human"] is False
