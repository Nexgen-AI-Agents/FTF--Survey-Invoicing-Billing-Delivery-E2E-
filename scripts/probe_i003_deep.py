"""
Deep probe — I-003: Find exact API name for Construction/Permitting surveys.

Strategy:
1. Test /pricing?service=... with candidate names Prateek mentioned
2. Sample Delivered orders at 3 different offset windows to find rare service types
3. Report all distinct service_type values seen
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

import httpx
from config.settings import FTF_API_BASE_URL, FTF_API_KEY

HEADERS = {
    "Authorization": f"Bearer {FTF_API_KEY}",
    "Content-Type": "application/json",
}
TIMEOUT = 30.0
SEP = "-" * 60


def test_pricing_service_name(name: str):
    """Hit GET /pricing?service=<name> — 200 means the API recognises this exact name."""
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/pricing",
            headers=HEADERS,
            params={"service": name, "tier": "individual"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return f"OK  — {r.json()}"
        else:
            return f"{r.status_code} — {r.text[:120]}"
    except Exception as exc:
        return f"ERR — {exc}"


def sample_service_types(status: str, offsets: list[int], per_page: int = 500) -> set[str]:
    """Collect service_type from the bulk endpoint across given offsets."""
    found = set()
    for offset in offsets:
        try:
            r = httpx.get(
                f"{FTF_API_BASE_URL}/orders",
                headers=HEADERS,
                params={"limit": per_page, "offset": offset, "status": status},
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            for o in r.json().get("data", []):
                st = o.get("service_type")
                if st:
                    found.add(st)
        except Exception as exc:
            print(f"  offset={offset} error: {exc}")
    return found


def sample_individual_orders(status: str, page_offset: int, sample_count: int = 100) -> set[str]:
    """Fetch real service_type by calling GET /orders/{id} on a sample."""
    r = httpx.get(
        f"{FTF_API_BASE_URL}/orders",
        headers=HEADERS,
        params={"limit": sample_count, "offset": page_offset, "status": status},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    orders = r.json().get("data", [])

    found = set()
    construction_perm = []
    for o in orders:
        order_id = o.get("order_id")
        try:
            detail = httpx.get(
                f"{FTF_API_BASE_URL}/orders/{order_id}",
                headers=HEADERS,
                timeout=TIMEOUT,
            ).json().get("data", {})
            st = detail.get("service_type", "")
            if st:
                found.add(st)
                if "construction" in st.lower() or "permitting" in st.lower():
                    construction_perm.append((order_id, st))
        except Exception:
            pass
    return found, construction_perm


if __name__ == "__main__":
    print("I-003 Deep Probe — Finding Construction/Permitting exact API name")
    print(f"Base URL: {FTF_API_BASE_URL}")

    # ── 1. Test candidate names directly on /pricing endpoint ──────────────────
    print()
    print(SEP)
    print("1. Testing candidate service names on GET /pricing?service=<name>")
    candidates = [
        "Construction/Permitting",
        "Construction Survey",
        "Permitting Survey",
        "Construction",
        "Permitting",
        "Construction Staking",
        "Construction Layout",
        "Permit Survey",
        "Building Permit Survey",
    ]
    for name in candidates:
        result = test_pricing_service_name(name)
        print(f"  '{name}' -> {result}")

    # ── 2. All distinct service_type from bulk Quote orders (wider sample) ──────
    print()
    print(SEP)
    print("2. service_type from bulk Quote orders — sampling offsets 0, 2000, 5000")
    quote_types = sample_service_types("Quote", offsets=[0, 2000, 5000])
    print("  Distinct values:")
    for st in sorted(quote_types):
        print(f"    {st}")

    # ── 3. service_type from bulk Delivered orders (wide offsets) ───────────────
    print()
    print(SEP)
    print("3. service_type from bulk Delivered orders — sampling offsets 0, 50000, 100000, 150000")
    delivered_bulk = sample_service_types("Delivered", offsets=[0, 50000, 100000, 150000])
    print("  Distinct values from bulk endpoint:")
    for st in sorted(delivered_bulk):
        print(f"    {st}")

    # ── 4. Deep sample: individual GET /orders/{id} at mid-range offset ─────────
    print()
    print(SEP)
    print("4. Individual order detail — 100 orders at Delivered offset=80000")
    try:
        deep_types, hits = sample_individual_orders("Delivered", page_offset=80000, sample_count=100)
        print("  Distinct service_type from individual endpoint:")
        for st in sorted(deep_types):
            print(f"    {st}")
        if hits:
            print(f"\n  FOUND Construction/Permitting:")
            for oid, st in hits:
                print(f"    order_id={oid}  service_type='{st}'")
        else:
            print("\n  Not found in this 100-order sample at offset 80000")
    except Exception as exc:
        print(f"  ERROR: {exc}")

    # ── 5. Note: Re-survey capitalisation inconsistency ─────────────────────────
    print()
    print(SEP)
    print("5. Capitalisation check — 'Re-survey' vs 'Re-Survey'")
    print("   Both values seen in previous probe. API returns inconsistent casing.")
    print("   Classifier must match case-insensitively for this service type.")

    print()
    print(SEP)
    print("Probe complete.")
