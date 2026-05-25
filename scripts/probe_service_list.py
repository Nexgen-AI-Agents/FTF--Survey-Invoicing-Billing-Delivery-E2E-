"""
Service list probe — check every known service name against the FTF API.

Goals:
1. Find if a full service catalogue endpoint exists
2. Test all 24 services from our internal list — which ones does the API know?
3. Test all service_type values seen in real orders — which ones are priced?
4. Surface any price differences between API and our config

Run: python scripts/probe_service_list.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

import httpx
from config.settings import FTF_API_BASE_URL, FTF_API_KEY

HEADERS = {"Authorization": f"Bearer {FTF_API_KEY}", "Content-Type": "application/json"}
TIMEOUT = 30.0
SEP = "-" * 72

# Our internal 24-service list (from memory.md)
OUR_24_SERVICES = {
    "Acreage":                  250,
    "ALTA Table A Survey":     1500,
    "B-II Title Review":        450,
    "Boundary Survey":          350,
    "Building Stake Out":       225,
    "Elevation Certificate":    225,
    "Elevation Only":           250,
    "Final Survey":             300,
    "Form Board Survey":        225,
    "Foundation Tie-In":        225,
    "Legal Description":        300,
    "Lot Split":                450,
    "Other Services":           150,
    "Pad Stake Out":            225,
    "Property Flagging":        150,
    "Site Plan":                150,
    "Sketch and Description":   300,
    "Specific Purpose Survey":  600,
    "Survey Re-draw":           150,
    "Surveyor's Affidavit":     100,
    "Topography Survey":        225,
    "Tree Location":            225,
    "Update Survey":            250,
    "Wetland Delineation":      300,
}

# Service types seen in real API orders but NOT in our 24-service list
API_OBSERVED_EXTRAS = [
    "Land Survey Only",
    "Land Survey and Elevation",
    "Property Survey and Elevation",
    "Re-Survey",
    "Re-survey",
    "Special staking service",
    "Topographic builder survey",
    "Spot Survey (New client)",
    "Elevation Certificate, Spot Survey (New client)",
    "Update survey add 3 elevations on seawall",
    "Property Survey and Elevation",
    "Construction/Permitting",
]

# Possible full-catalogue endpoints to try
CATALOGUE_ENDPOINTS = [
    "/services",
    "/service-types",
    "/pricing/list",
    "/pricing/all",
    "/pricing/services",
    "/survey-types",
]


def get_price(service: str, tier: str = "individual"):
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/pricing",
            headers=HEADERS,
            params={"service": service, "tier": tier},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            body = r.json()
            price = (body.get("data", {}) or body).get("price") or body.get("price")
            return "OK", price, body
        elif r.status_code == 404:
            return "NOT FOUND", None, None
        else:
            return f"HTTP {r.status_code}", None, None
    except Exception as exc:
        return f"ERR: {exc}", None, None


def try_catalogue_endpoint(path: str):
    try:
        r = httpx.get(f"{FTF_API_BASE_URL}{path}", headers=HEADERS, timeout=TIMEOUT)
        return r.status_code, r.text[:300]
    except Exception as exc:
        return "ERR", str(exc)


if __name__ == "__main__":
    print("FTF Service List Probe")
    print(f"API: {FTF_API_BASE_URL}")

    # ── 1. Hunt for a full-catalogue endpoint ──────────────────────────────────
    print()
    print(SEP)
    print("1. Looking for a full service catalogue endpoint")
    for path in CATALOGUE_ENDPOINTS:
        code, body = try_catalogue_endpoint(path)
        print(f"  {path:<30} -> {code}  {body[:80]}")

    # ── 2. Test our 24 services ────────────────────────────────────────────────
    print()
    print(SEP)
    print("2. Our 24 internal services vs API /pricing")
    print(f"  {'Service':<35} {'Our $':>7}  {'Status':<12}  {'API $':>7}  {'Price match'}")
    print(f"  {'-'*35} {'-'*7}  {'-'*12}  {'-'*7}  {'-'*12}")

    found_in_api = []
    not_in_api = []

    for service, our_price in OUR_24_SERVICES.items():
        status, api_price, raw = get_price(service)
        if status == "OK":
            found_in_api.append(service)
            match = "MATCH" if api_price == our_price else f"DIFF (API={api_price})"
        else:
            not_in_api.append(service)
            match = ""
        api_price_str = f"${api_price}" if api_price is not None else "-"
        print(f"  {service:<35} ${our_price:>6}  {status:<12}  {api_price_str:>7}  {match}")

    # ── 3. Test API-observed extras ────────────────────────────────────────────
    print()
    print(SEP)
    print("3. Service types seen in real orders — are they priced in the API?")
    print(f"  {'Service':<45} {'Status':<12}  {'API $':>7}")
    print(f"  {'-'*45} {'-'*12}  {'-'*7}")

    extras_found = []
    for service in API_OBSERVED_EXTRAS:
        status, api_price, _ = get_price(service)
        api_price_str = f"${api_price}" if api_price is not None else "-"
        print(f"  {service:<45} {status:<12}  {api_price_str:>7}")
        if status == "OK":
            extras_found.append((service, api_price))

    # ── 4. Summary ─────────────────────────────────────────────────────────────
    print()
    print(SEP)
    print("SUMMARY")
    print(f"  Our list: {len(OUR_24_SERVICES)} services")
    print(f"  Found in API pricing: {len(found_in_api)}")
    print(f"  NOT in API pricing  : {len(not_in_api)}")
    if not_in_api:
        print(f"  Missing from API:")
        for s in not_in_api:
            print(f"    - {s}")
    if extras_found:
        print(f"  API extras that ARE priced:")
        for s, p in extras_found:
            print(f"    + {s} = ${p}")
    print()
    print(SEP)
    print("Probe complete.")
