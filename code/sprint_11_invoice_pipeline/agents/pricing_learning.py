"""pricing_learning.py — pure helpers for the AI pricing-learning loop.

When an order already carries a human-set amount in FTF (the "Amount ($) by User"),
the pipeline compares that to what the AI would have priced ("Amount ($) by AI"),
records a structured learning note ("AI Learning"), and feeds the observation into
data/learned_rules.json so future pricing improves — eventually including condo
Elevation Certificates.

Everything here is PURE (no network/DB/file I/O except the explicitly-named
learned_rules persistence) so it is fully unit-testable. Bounds and graduation
criteria come from the Florida-PLS design brief.
"""
from __future__ import annotations

import json
import os
from typing import Optional

# ── Price guardrails (South Florida market, from the PLS brief) ───────────────
# Per normalized service: (floor, ceiling). A learned/observed price outside the
# band is never trusted silently — it is flagged for human review.
PRICE_BOUNDS = {
    "boundary":      (350.0, 1200.0),   # Land Survey Only / boundary (residential)
    "elevation":     (275.0, 475.0),    # Elevation Certificate
    "boundary_ec":   (650.0, 900.0),    # bundled boundary + EC
    "topographic":   (700.0, 1500.0),
    "final":         (400.0, 700.0),    # final / as-built (CO)
    "condo_ec":      (300.0, 550.0),    # condo Elevation Certificate
    "alta":          (1500.0, 6000.0),  # commercial — always human, never auto
}
ABS_MIN_FIELD = 275.0   # never price any field service below cost

# Learning movement limiter: one observation may nudge a learned rate by at most
# this fraction per cycle, and never more than MAX_OFF_BASE off the published base.
MAX_MOVE_PER_CYCLE = 0.05
MAX_OFF_BASE       = 0.15
TOLERANCE          = 0.10   # |delta| <= 10% counts as a "match"

# Condo-EC graduation: only condo Elevation Certificates may ever auto-graduate,
# and only after enough close human-matched examples.
CONDO_GRAD_MIN_EXAMPLES = 15
CONDO_GRAD_MIN_HITS     = 12   # of the last 15, within TOLERANCE


def normalize_service(service: str) -> str:
    """Map a free-text FTF service string to a PRICE_BOUNDS key."""
    s = (service or "").lower()
    is_condo = "condo" in s
    has_ec = any(k in s for k in ("elevation", "ec", "elev cert", "elevation cert"))
    has_boundary = any(k in s for k in ("boundary", "land survey", "lot survey"))
    if "alta" in s:
        return "alta"
    if "topo" in s:
        return "topographic"
    if "final" in s or "as-built" in s or "as built" in s:
        return "final"
    if is_condo and has_ec:
        return "condo_ec"
    if has_boundary and has_ec:
        return "boundary_ec"
    if has_ec:
        return "elevation"
    if has_boundary:
        return "boundary"
    return "boundary"   # safe default for unmatched survey work


def price_within_bounds(service: str, price: float) -> bool:
    """True if price is inside the service's published band (and above abs floor)."""
    key = normalize_service(service)
    lo, hi = PRICE_BOUNDS.get(key, (ABS_MIN_FIELD, 1e9))
    return price >= max(lo, ABS_MIN_FIELD) and price <= hi


def clamp_or_flag(service: str, price: float) -> tuple[float, str]:
    """Return (price, flag). Never silently move price out of band; flag instead.

    flag is "" when in-band, else a short reason a human/PLS can read.
    """
    key = normalize_service(service)
    lo, hi = PRICE_BOUNDS.get(key, (ABS_MIN_FIELD, 1e9))
    lo = max(lo, ABS_MIN_FIELD)
    if price < lo:
        return price, f"below floor for {key} (${lo:,.0f})"
    if price > hi:
        return price, f"above ceiling for {key} (${hi:,.0f})"
    return price, ""


def classify_delta(ai_price: float, human_price: float) -> dict:
    """Compare AI vs human price. Returns delta_abs, delta_pct, within_tolerance, verdict."""
    delta_abs = round(human_price - ai_price, 2)
    delta_pct = round((delta_abs / human_price) * 100, 1) if human_price else 0.0
    within = abs(delta_pct) <= TOLERANCE * 100
    if within:
        verdict = "match"
    elif ai_price > human_price:
        verdict = "ai_high"
    else:
        verdict = "ai_low"
    return {"delta_abs": delta_abs, "delta_pct": delta_pct,
            "within_tolerance": within, "verdict": verdict}


def looks_like_negotiated_discount(tier: str, verdict: str) -> bool:
    """Heuristic: a title-company (old/new_title) coming in UNDER the AI price is most
    likely a negotiated relationship rate, NOT an AI error — tag it so it does not drag
    the learned base down. Individuals are full-retail, so their deltas ARE signal.
    """
    return verdict == "ai_high" and str(tier).lower() in ("old_title", "new_title")


def build_ai_learn_record(
    order_id: str,
    service: str,
    tier: str,
    county: str,
    ai_price: float,
    human_price: float,
    observed_at: str,
    flood: Optional[str] = None,
    acreage=None,
    legal: str = "",
    extra_driver: str = "",
) -> str:
    """Build the compact, PLS-auditable AI_LEARN record (v1) for the AI Learning cell."""
    d = classify_delta(ai_price, human_price)
    negotiated = looks_like_negotiated_discount(tier, d["verdict"])
    _, bound_flag = clamp_or_flag(service, human_price)
    if extra_driver:
        driver = extra_driver
    elif negotiated:
        driver = "negotiated_rate (title-company relationship discount -- excluded from scoring)"
    elif bound_flag:
        driver = f"human price {bound_flag}"
    elif d["verdict"] == "match":
        driver = "AI price matched the human amount"
    elif d["verdict"] == "ai_low":
        driver = "AI under-priced — check size/flood/legal-description signals"
    else:
        driver = "AI over-priced — check tier/negotiated rate"
    svc_key = normalize_service(service)
    lines = [
        "AI_LEARN | v1",
        f"order={order_id} svc={svc_key} tier={tier or 'unknown'} county={county or 'unknown'}",
        f"flood={flood or 'na'} legal={legal or 'na'} acreage={acreage if acreage is not None else 'na'}",
        f"ai_price={ai_price:.0f} human_price={human_price:.0f} "
        f"delta_abs={d['delta_abs']:.0f} delta_pct={d['delta_pct']}",
        f"within_tolerance={'Y' if d['within_tolerance'] else 'N'} verdict={d['verdict']}",
        f"scored={'N' if negotiated else 'Y'} likely_driver=\"{driver}\"",
        f"observed_at={observed_at} source=human_invoice",
    ]
    # One line (pipe-separated) so the AI Learning cell never makes the row tall/distorted
    # in the Approvals sheet.
    return " | ".join(lines)


def condo_ec_graduated(recent_examples: list[dict]) -> bool:
    """True only if condo-EC pricing has earned auto-pricing: >= MIN_EXAMPLES observations
    and >= MIN_HITS of the most recent 15 within tolerance (trimmed: drop 2 worst outliers).
    `recent_examples` items: {"within_tolerance": bool, "delta_pct": float}.
    """
    ex = [e for e in recent_examples if e.get("delta_pct") is not None]
    if len(ex) < CONDO_GRAD_MIN_EXAMPLES:
        return False
    last = sorted(ex, key=lambda e: abs(e.get("delta_pct", 999)))[:-2] if len(ex) > 15 else ex
    last = last[-15:]
    hits = sum(1 for e in last if e.get("within_tolerance"))
    return hits >= CONDO_GRAD_MIN_HITS


def limited_move(current: float, target: float, base: float) -> float:
    """Move `current` toward `target` by at most MAX_MOVE_PER_CYCLE, clamped to within
    MAX_OFF_BASE of the published `base`. Prevents one odd invoice yanking the model.
    """
    if current <= 0:
        current = base
    step = current * MAX_MOVE_PER_CYCLE
    if target > current:
        nxt = min(target, current + step)
    else:
        nxt = max(target, current - step)
    lo = base * (1 - MAX_OFF_BASE)
    hi = base * (1 + MAX_OFF_BASE)
    return round(min(max(nxt, lo), hi), 2)


# ── learned_rules.json persistence (the one I/O function) ─────────────────────

_RULES_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "learned_rules.json")
)


def condo_ec_pricing_enabled(rules_path: str = _RULES_FILE) -> bool:
    """True if condo Elevation Certificate pricing has GRADUATED to auto-pricing.

    Reads learned_rules.json and returns True only if at least one condo_ec observation
    bucket has reached status 'active'. Read-only; never raises — returns False on error
    so condos stay safely escalated by default.
    """
    try:
        if not os.path.exists(rules_path):
            return False
        with open(rules_path, encoding="utf-8") as f:
            data = json.load(f)
        for b in data.get("observations", {}).values():
            if b.get("service") == "condo_ec" and b.get("status") == "active":
                return True
        return False
    except Exception:
        return False


def record_observation(order_id: str, service: str, county: str, tier: str,
                       ai_price: float, human_price: float, observed_at: str,
                       rules_path: str = _RULES_FILE) -> dict:
    """Append a price observation to learned_rules.json under its (service,county,tier)
    bucket. Negotiated discounts are stored but flagged scored=False so they don't move
    the learned rate. Returns the updated bucket. Never raises — returns {} on error.
    """
    try:
        d = classify_delta(ai_price, human_price)
        negotiated = looks_like_negotiated_discount(tier, d["verdict"])
        svc_key = normalize_service(service)
        bucket_key = f"{svc_key}|{(county or 'any').lower()}|{tier or 'unknown'}"

        data = {}
        if os.path.exists(rules_path):
            with open(rules_path, encoding="utf-8") as f:
                data = json.load(f)
        buckets = data.setdefault("observations", {})
        b = buckets.setdefault(bucket_key, {"service": svc_key, "county": county or "any",
                                            "tier": tier, "samples": [], "learned_price": 0.0,
                                            "status": "observing"})
        b["samples"].append({
            "order_id": str(order_id), "ai": round(ai_price, 2), "human": round(human_price, 2),
            "delta_pct": d["delta_pct"], "within_tolerance": d["within_tolerance"],
            "scored": not negotiated, "observed_at": observed_at,
        })
        # Update learned price only from SCORED samples, via the movement limiter.
        scored = [s for s in b["samples"] if s.get("scored")]
        if len(scored) >= 10:
            base = b["learned_price"] or (sum(s["human"] for s in scored[-10:]) / 10)
            target = sum(s["human"] for s in scored[-10:]) / 10
            b["learned_price"] = limited_move(b["learned_price"], target, base)
            if svc_key == "condo_ec":
                b["status"] = "active" if condo_ec_graduated(scored) else "observing"
            else:
                b["status"] = "active"
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return b
    except Exception:
        return {}
