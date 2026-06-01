"""Tests for A3 Invoice Compiler — specifically pricing logic and Teams post building."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))


def test_base_rate_land_survey():
    """Land Survey Only should return the base rate."""
    from agents.agent_a3_invoice_compiler import _lookup_price
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "agents.agent_a3_invoice_compiler.get_pricing_examples",
            lambda **kw: [],
        )
        mp.setattr(
            "agents.agent_a3_invoice_compiler.get_invoice_learnings",
            lambda **kw: [],
        )
        price, source = _lookup_price("Land Survey Only", "Miami-Dade", "residential")
        assert price == 450.0
        assert source == "base_rate"


def test_base_rate_elevation_cert():
    from agents.agent_a3_invoice_compiler import _lookup_price
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("agents.agent_a3_invoice_compiler.get_pricing_examples", lambda **kw: [])
        mp.setattr("agents.agent_a3_invoice_compiler.get_invoice_learnings", lambda **kw: [])
        price, source = _lookup_price("Elevation Certificate", "", "residential")
        assert price == 225.0


def test_b2b_multiplier():
    from agents.agent_a3_invoice_compiler import _lookup_price
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("agents.agent_a3_invoice_compiler.get_pricing_examples", lambda **kw: [])
        mp.setattr("agents.agent_a3_invoice_compiler.get_invoice_learnings", lambda **kw: [])
        price_res, _  = _lookup_price("Land Survey Only", "", "residential")
        price_b2b, _  = _lookup_price("Land Survey Only", "", "b2b")
        assert abs(price_b2b - price_res * 1.3) < 0.01


def test_pricing_examples_take_priority():
    from agents.agent_a3_invoice_compiler import _lookup_price
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "agents.agent_a3_invoice_compiler.get_pricing_examples",
            lambda **kw: [{"final_price": 600.0}],
        )
        mp.setattr("agents.agent_a3_invoice_compiler.get_invoice_learnings", lambda **kw: [])
        price, source = _lookup_price("Land Survey Only", "Broward", "residential")
        assert price == 600.0
        assert source == "pricing_examples"


def test_build_teams_post_contains_order_id(sample_invoice_draft, sample_order_packet):
    from agents.agent_a3_invoice_compiler import _build_teams_post
    html = _build_teams_post("TEST-001", sample_order_packet, sample_invoice_draft, "https://example.com/TEST-001")
    assert "TEST-001" in html
    assert "450" in html
    assert "APPROVE" in html
