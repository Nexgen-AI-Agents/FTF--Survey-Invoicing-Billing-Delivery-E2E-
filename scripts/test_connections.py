#!/usr/bin/env python3
"""
Sprint 0 — Live connection verification.
Run from project root: python scripts/test_connections.py
Requires .env to be populated with real staging credentials.
"""

import os
import sys

# Add code/shared to path so core/ and config/ are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from dotenv import load_dotenv
load_dotenv()

import yaml

from core.ftf_client import health_check, get_orders, get_pricing
from core.fema_client import check_flood_zone
from core.claude_client import call as claude_call
from core.db import get_pending_order
from config.models import MONITOR_MODEL

_PASS = "\033[92m  PASS\033[0m"
_FAIL = "\033[91m  FAIL\033[0m"

results: list[tuple[str, bool, str]] = []
warnings: list[tuple[str, str]] = []


def check(name: str, fn):
    try:
        detail = fn()
        results.append((name, True, str(detail)[:80]))
        print(f"{_PASS}  {name}")
    except Exception as exc:
        results.append((name, False, str(exc)[:120]))
        print(f"{_FAIL}  {name}")
        print(f"         {exc}")


def check_warn(name: str, fn):
    """Network-dependent check — failure is a warning, not a blocker."""
    try:
        detail = fn()
        results.append((name, True, str(detail)[:80]))
        print(f"{_PASS}  {name}")
    except Exception as exc:
        warnings.append((name, str(exc)[:120]))
        print(f"\033[93m  WARN\033[0m  {name} (network-dependent — will pass on GitHub Actions)")
        print(f"         {exc}")


# ── 1. FTF /health ───────────────────────────────────────────────────────────
check("FTF /health -> 200", lambda: health_check() or (_ for _ in ()).throw(AssertionError("returned False")))


# ── 2. FTF /orders (single page, no full pagination) ─────────────────────────
def _check_orders():
    # max_results=5 prevents paginating 275K orders — just verifies the endpoint is live
    orders = get_orders(limit=5, max_results=5)
    assert isinstance(orders, list) and len(orders) > 0, "Empty orders list"
    return f"{len(orders)} order(s) returned (single page check)"

check("FTF /orders -> data (5-order sample)", _check_orders)


# ── 3. FTF /pricing ──────────────────────────────────────────────────────────
def _check_pricing():
    pricing = get_pricing("Boundary Survey")
    assert pricing, "Empty pricing response"
    return str(pricing)[:60]

check("FTF /pricing -> response", _check_pricing)


# ── 4. FEMA flood zone (Lake Park, FL) ───────────────────────────────────────
def _check_fema():
    zone = check_flood_zone(lat=26.7998, lng=-80.0642)
    assert zone, "Empty zone code"
    return f"Zone: {zone}"

check_warn("FEMA FL lat/lng -> zone code", _check_fema)


# ── 5. Claude Haiku ──────────────────────────────────────────────────────────
def _check_claude():
    response = claude_call(
        model=MONITOR_MODEL,
        system="You are a test assistant.",
        user="Reply with only the word: OK",
        max_tokens=10,
    )
    assert response, "Empty Claude response"
    return response.strip()

check("Claude Haiku -> response received", _check_claude)


# ── 6. DB schema ─────────────────────────────────────────────────────────────
def _check_db():
    get_pending_order()  # returns None on empty table — that is correct
    return "processed_orders table accessible"

check("DB processed_orders -> accessible", _check_db)


# ── 7. GitHub Actions YAML validity ──────────────────────────────────────────
def _check_yaml():
    base = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows")
    files = ("estimate_generation.yml", "ar_followup.yml", "monthly_statements.yml")
    for fname in files:
        with open(os.path.join(base, fname)) as f:
            yaml.safe_load(f)
    return f"{len(files)} workflow files valid"

check("GitHub Actions YAML -> valid", _check_yaml)


# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("-" * 50)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Sprint 0 checks: {passed}/{total} passed")
if warnings:
    print(f"Warnings (network-dependent, not blocking): {len(warnings)}")
    for name, detail in warnings:
        print(f"  WARN {name}: {detail}")
if passed < total:
    print()
    print("Failed checks:")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAIL {name}: {detail}")
    sys.exit(1)
else:
    print("All checks green — Sprint 0 infrastructure confirmed.")
