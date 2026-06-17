"""Tests for A3 Invoice Compiler — current behaviour (AI pricing + Excel approval).

The pre-AI pricing-table helpers (_lookup_price, _build_teams_post) were removed in the
AI-pricing/Excel rewrite. These tests cover the pure helpers that exist today, including the
poison-data guard and the Pricing Rules tab injection.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from agents import agent_a3_invoice_compiler as a3


# ── Service breakdown string ──────────────────────────────────────────────────

def test_build_breakdown_str_multi_service():
    out = a3._build_breakdown_str([
        {"name": "Boundary Survey", "amount": 475.0},
        {"name": "Elevation Cert", "amount": 150.0},
    ])
    assert out == "Boundary Survey: $475.00 | Elevation Cert: $150.00"


def test_build_breakdown_str_no_amount_falls_back_to_name():
    out = a3._build_breakdown_str([{"name": "Land Survey Only", "amount": 0}])
    assert out == "Land Survey Only"


def test_build_breakdown_str_empty():
    assert a3._build_breakdown_str([]) == ""


# ── Client tier classification (incl. poison-data guard) ───────────────────────

def test_classify_tier_no_company_is_individual():
    assert a3._classify_client_tier({}) == "individual"


def test_classify_tier_company_type_1_is_individual():
    assert a3._classify_client_tier({"company_type": 1}) == "individual"


def test_classify_tier_established_company_is_old_title():
    # Old registration year → old_title regardless of order count
    assert a3._classify_client_tier({"company_type": 0, "ng_dtentered": "2005-01-01",
                                     "ng_order_count": 500}) == "old_title"


def test_classify_tier_poison_dtentered_does_not_crash():
    # Empty / garbage ng_dtentered must not raise (int("") would) — falls back gracefully.
    for bad in ("", "   ", None, "not-a-date"):
        assert a3._classify_client_tier({"company_type": 0, "ng_dtentered": bad,
                                         "ng_order_count": 1}) in ("old_title", "new_title", "individual")


# ── Fallback survey rate ───────────────────────────────────────────────────────

def test_fallback_rate_individual_vs_old_title():
    from config.settings import PRICE_SURVEY_FALLBACK_INDIVIDUAL, PRICE_SURVEY_FALLBACK_OLD_TITLE
    assert a3._get_fallback_survey_rate("individual") == PRICE_SURVEY_FALLBACK_INDIVIDUAL
    assert a3._get_fallback_survey_rate("new_title") == PRICE_SURVEY_FALLBACK_INDIVIDUAL
    assert a3._get_fallback_survey_rate("old_title") == PRICE_SURVEY_FALLBACK_OLD_TITLE


# ── Pricing Rules tab → AI prompt injection ────────────────────────────────────

def test_user_pricing_rules_block_formats_active_rules(monkeypatch):
    monkeypatch.setattr(a3, "get_pricing_rules", lambda: [
        {"service": "Boundary", "county": "Miami-Dade", "client": "*", "price": 550.0, "notes": "std"},
        {"service": "*", "county": "*", "client": "*", "price": 0.0, "notes": "keep AI"},  # price 0 → skipped
    ])
    block = a3._load_user_pricing_rules_block()
    assert "$550.00" in block
    assert "Boundary" in block and "Miami-Dade" in block
    assert "keep AI" not in block          # price<=0 rule must be excluded


def test_user_pricing_rules_block_empty_when_no_rules(monkeypatch):
    monkeypatch.setattr(a3, "get_pricing_rules", lambda: [])
    assert a3._load_user_pricing_rules_block() == ""
