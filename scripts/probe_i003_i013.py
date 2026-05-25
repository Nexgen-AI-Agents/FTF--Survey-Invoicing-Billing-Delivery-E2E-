"""
Probe script — I-003 + I-013 retest
Run from project root:  python scripts/probe_i003_i013.py

I-003: Does the API return "Construction/Permitting" as a service_type?
I-013: What is the current total order count (all statuses)?
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


def probe_total_all_statuses():
    """I-013: hit /orders with no status filter — compare total to last known 207,622."""
    print(SEP)
    print("I-013: GET /orders (no status filter) — checking current total")
    r = httpx.get(
        f"{FTF_API_BASE_URL}/orders",
        headers=HEADERS,
        params={"limit": 1, "offset": 0},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    body = r.json()
    total = body.get("total", "N/A")
    count = body.get("count", "N/A")
    print(f"  total (all statuses) : {total}")
    print(f"  count (this page)    : {count}")
    print(f"  Previous reading     : 207,622")
    print(f"  CRM shows            : 275,693")
    delta = None
    if isinstance(total, int):
        delta = 275693 - total
        print(f"  Gap vs CRM           : {delta:,} orders")
    return total


def probe_total_by_status(status: str):
    """Hit /orders?status=X — get total for one status bucket."""
    r = httpx.get(
        f"{FTF_API_BASE_URL}/orders",
        headers=HEADERS,
        params={"limit": 1, "offset": 0, "status": status},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    body = r.json()
    return body.get("total", 0)


def probe_all_status_buckets():
    """Sum across known FTF statuses — check if they add up to CRM total."""
    print(SEP)
    print("I-013: Summing totals per-status to find where the gap lives")
    statuses = [
        "Quote", "Assigned", "In-Field", "Crew Completed",
        "Checking", "Under Review", "Delivered", "Complete",
        "Canceled", "Go Back",
    ]
    grand_total = 0
    for s in statuses:
        try:
            n = probe_total_by_status(s)
            print(f"  status={s:<20} total={n:>8,}")
            grand_total += n
        except Exception as exc:
            print(f"  status={s:<20} ERROR: {exc}")
    print(f"  {'--- SUM ---':<20} total={grand_total:>8,}")
    print(f"  CRM total                       275,693")
    print(f"  Gap                             {275693 - grand_total:>8,}")
    return grand_total


def probe_service_type_sample():
    """I-003: Fetch a sample of individual orders and collect distinct service_type values.
    We look for anything containing 'Construction' or 'Permitting'.
    """
    print(SEP)
    print("I-003: Scanning service_type values across first 500 Quote orders")
    r = httpx.get(
        f"{FTF_API_BASE_URL}/orders",
        headers=HEADERS,
        params={"limit": 500, "offset": 0, "status": "Quote"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    orders = r.json().get("data", [])

    service_types = set()
    for o in orders:
        st = o.get("service_type")
        if st:
            service_types.add(st)

    print(f"  Distinct service_type values in first 500 Quote orders:")
    for st in sorted(service_types):
        print(f"    {st}")

    hits = [st for st in service_types if "construction" in st.lower() or "permitting" in st.lower()]
    print()
    if hits:
        print(f"  FOUND Construction/Permitting matches: {hits}")
    else:
        print("  No 'Construction' or 'Permitting' in service_type for Quote orders (expected — bulk endpoint always returns 'Quote')")
        print("  Will probe individual orders for actual service names next...")
    return service_types


def probe_individual_order_service_types():
    """I-003: Fetch Delivered/Complete orders to find real service_type values including Construction/Permitting."""
    print(SEP)
    print("I-003: Fetching first 500 Delivered orders — checking real service_type values")
    r = httpx.get(
        f"{FTF_API_BASE_URL}/orders",
        headers=HEADERS,
        params={"limit": 500, "offset": 0, "status": "Delivered"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    delivered = r.json().get("data", [])
    print(f"  Got {len(delivered)} Delivered orders")

    service_types = set()
    construction_permitting = []

    for o in delivered[:50]:
        order_id = o.get("order_id")
        try:
            detail = httpx.get(
                f"{FTF_API_BASE_URL}/orders/{order_id}",
                headers=HEADERS,
                timeout=TIMEOUT,
            ).json().get("data", {})
            st = detail.get("service_type", "")
            if st:
                service_types.add(st)
                if "construction" in st.lower() or "permitting" in st.lower():
                    construction_permitting.append((order_id, st))
        except Exception as exc:
            print(f"    order {order_id} error: {exc}")

    print(f"\n  Distinct service_type values found across 50 sampled Delivered orders:")
    for st in sorted(service_types):
        print(f"    {st}")

    print()
    if construction_permitting:
        print(f"  FOUND Construction/Permitting orders:")
        for oid, st in construction_permitting:
            print(f"    order_id={oid}  service_type='{st}'")
    else:
        print("  No 'Construction' or 'Permitting' service_type found in this 50-order sample")
        print("  Try increasing sample size or checking Checking/Under Review statuses")

    return service_types


def probe_pricing_endpoint():
    """I-003: Check if /pricing returns a full service catalogue (without params)."""
    print(SEP)
    print("I-003: GET /pricing (no params) — checking if API lists all available services")
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/pricing",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        body = r.json()
        print(f"  Response type: {type(body).__name__}")
        if isinstance(body, list):
            print(f"  Services returned: {len(body)}")
            for item in body:
                print(f"    {item}")
        elif isinstance(body, dict):
            print(f"  Keys: {list(body.keys())}")
            print(f"  Full response: {body}")
        else:
            print(f"  Raw: {body}")
    except Exception as exc:
        print(f"  ERROR: {exc}")


if __name__ == "__main__":
    print("FTF API Probe — I-003 (service types) + I-013 (order count)")
    print(f"Base URL: {FTF_API_BASE_URL}")
    print()

    try:
        probe_total_all_statuses()
        probe_all_status_buckets()
        probe_service_type_sample()
        probe_individual_order_service_types()
        probe_pricing_endpoint()
    except httpx.HTTPStatusError as exc:
        print(f"\nHTTP ERROR {exc.response.status_code}: {exc.response.text}")
    except Exception as exc:
        print(f"\nERROR: {exc}")

    print()
    print(SEP)
    print("Probe complete.")
