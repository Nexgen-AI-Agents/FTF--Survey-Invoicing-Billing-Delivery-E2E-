"""Tests for pricing_learning — the AI pricing-learning loop helpers."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from agents import pricing_learning as p


# ── service normalization ───────────────────────────────────────────────────
def test_normalize_service():
    assert p.normalize_service("Condo Elevation Certificate") == "condo_ec"
    assert p.normalize_service("Land Survey and Elevation") == "boundary_ec"
    assert p.normalize_service("Elevation Certificate") == "elevation"
    assert p.normalize_service("Land Survey Only") == "boundary"
    assert p.normalize_service("ALTA/NSPS Survey") == "alta"
    assert p.normalize_service("") == "boundary"          # safe default


# ── bounds / guardrails ───────────────────────────────────────────────────────
def test_price_within_bounds():
    assert p.price_within_bounds("Land Survey Only", 450) is True
    assert p.price_within_bounds("Land Survey Only", 200) is False   # below floor
    assert p.price_within_bounds("Land Survey Only", 5000) is False  # above ceiling
    assert p.price_within_bounds("Elevation Certificate", 300) is True


def test_clamp_or_flag_never_silently_moves():
    # below abs field floor → flagged, price unchanged (never silently clamped to bill low)
    price, flag = p.clamp_or_flag("Land Survey Only", 100)
    assert price == 100 and "below floor" in flag
    price, flag = p.clamp_or_flag("Elevation Certificate", 9999)
    assert price == 9999 and "above ceiling" in flag
    price, flag = p.clamp_or_flag("Land Survey Only", 450)
    assert flag == ""


# ── delta + negotiated-discount tagging ───────────────────────────────────────
def test_classify_delta():
    d = p.classify_delta(475, 400)
    assert d["verdict"] == "ai_high" and d["within_tolerance"] is False
    d = p.classify_delta(400, 420)
    assert d["verdict"] == "match" and d["within_tolerance"] is True   # 4.8% <= 10%
    d = p.classify_delta(300, 500)
    assert d["verdict"] == "ai_low"


def test_negotiated_discount_only_for_title_under():
    assert p.looks_like_negotiated_discount("old_title", "ai_high") is True
    assert p.looks_like_negotiated_discount("new_title", "ai_high") is True
    assert p.looks_like_negotiated_discount("individual", "ai_high") is False  # full retail = signal
    assert p.looks_like_negotiated_discount("old_title", "ai_low") is False


# ── movement limiter ──────────────────────────────────────────────────────────
def test_limited_move_caps_step_and_band():
    # from 500 toward 600, base 500: step capped at 5% (=25) → 525
    assert p.limited_move(500, 600, 500) == 525.0
    # never more than 15% off base regardless of target
    assert p.limited_move(560, 5000, 500) == 575.0   # hi band = 575
    assert p.limited_move(440, 100, 500) == 425.0    # lo band = 425


# ── AI_LEARN record ───────────────────────────────────────────────────────────
def test_build_ai_learn_record_tags_negotiated():
    rec = p.build_ai_learn_record("48217", "Land Survey Only", "old_title", "Broward",
                                  475, 400, "2026-06-18 10:00 EDT", flood="AE")
    assert "AI_LEARN | v1" in rec
    assert "order=48217" in rec and "svc=boundary" in rec
    assert "verdict=ai_high" in rec
    assert "scored=N" in rec                 # negotiated discount excluded from scoring
    assert "negotiated_rate" in rec


def test_build_ai_learn_record_individual_is_scored():
    rec = p.build_ai_learn_record("9", "Land Survey Only", "individual", "Palm Beach",
                                  475, 400, "2026-06-18 10:00 EDT")
    assert "scored=Y" in rec                 # individual delta IS signal


# ── condo-EC graduation ───────────────────────────────────────────────────────
def test_condo_graduation_needs_enough_close_examples():
    few = [{"within_tolerance": True, "delta_pct": 1.0}] * 5
    assert p.condo_ec_graduated(few) is False                     # < 15 examples
    good = [{"within_tolerance": True, "delta_pct": 2.0}] * 15
    assert p.condo_ec_graduated(good) is True
    mostly_off = [{"within_tolerance": False, "delta_pct": 30.0}] * 15
    assert p.condo_ec_graduated(mostly_off) is False


# ── persistence ───────────────────────────────────────────────────────────────
def test_condo_ec_pricing_enabled(tmp_path):
    import json
    f = tmp_path / "lr.json"
    # no file → not enabled (safe default)
    assert p.condo_ec_pricing_enabled(str(f)) is False
    # condo_ec bucket but still observing → not enabled
    f.write_text(json.dumps({"observations": {
        "condo_ec|broward|individual": {"service": "condo_ec", "status": "observing"}}}))
    assert p.condo_ec_pricing_enabled(str(f)) is False
    # condo_ec bucket active → enabled
    f.write_text(json.dumps({"observations": {
        "condo_ec|broward|individual": {"service": "condo_ec", "status": "active"}}}))
    assert p.condo_ec_pricing_enabled(str(f)) is True


def test_record_observation_writes_bucket(tmp_path):
    f = tmp_path / "learned_rules.json"
    b = p.record_observation("1001", "Land Survey Only", "Broward", "individual",
                             475, 460, "2026-06-18 10:00 EDT", rules_path=str(f))
    assert b["service"] == "boundary"
    assert len(b["samples"]) == 1
    assert b["samples"][0]["scored"] is True
    # negotiated (title under) is stored but not scored
    b2 = p.record_observation("1002", "Land Survey Only", "Broward", "old_title",
                              475, 400, "2026-06-18 10:00 EDT", rules_path=str(f))
    assert b2["samples"][-1]["scored"] is False
