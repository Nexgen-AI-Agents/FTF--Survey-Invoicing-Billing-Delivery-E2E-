"""
Status count verification — API vs CRM screenshot
Run: python scripts/probe_status_match.py

CRM screenshot counts (2026-05-25):
  Pending: 55, Needs FP: 138, Assigned: 50, In-Field: 14,
  Drafting Queue: 125, Drafting: 56, Checking: 27, Complete: 12,
  On Hold: 760, Quote: 7456, In Progress: 1, Go Back: 10,
  Set Corners: 1, Set Up: 0, Canceled: 60615, Delivered: 206333
  Search (total): 275705
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

import httpx
from config.settings import FTF_API_BASE_URL, FTF_API_KEY

HEADERS = {"Authorization": f"Bearer {FTF_API_KEY}", "Content-Type": "application/json"}
TIMEOUT = 30.0

CRM_COUNTS = {
    "Pending":        55,
    "Needs FP":      138,
    "Assigned":       50,
    "In-Field":       14,
    "Drafting Queue": 125,
    "Drafting":       56,
    "Checking":       27,
    "Complete":       12,
    "On Hold":       760,
    "Quote":        7456,
    "In Progress":     1,
    "Go Back":        10,
    "Set Corners":     1,
    "Set Up":          0,
    "Canceled":    60615,
    "Delivered":  206333,
}
CRM_TOTAL = 275705


def get_total(status: str = None) -> tuple[int | None, str]:
    """Return (total, note). total=None on error."""
    params = {"limit": 1, "offset": 0}
    if status:
        params["status"] = status
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/orders",
            headers=HEADERS,
            params=params,
            timeout=TIMEOUT,
        )
        if r.status_code == 400:
            return None, f"400 BAD REQUEST — status not filterable via API"
        r.raise_for_status()
        body = r.json()
        return body.get("total", 0), "OK"
    except httpx.HTTPStatusError as exc:
        return None, f"HTTP {exc.response.status_code}"
    except Exception as exc:
        return None, f"ERR: {exc}"


SEP = "-" * 72

if __name__ == "__main__":
    print("FTF API vs CRM Status Count Verification")
    print(f"API: {FTF_API_BASE_URL}")
    print()

    # ── 1. No-filter total ──────────────────────────────────────────────────────
    api_total, note = get_total()
    match_sym = "PASS" if api_total == CRM_TOTAL else "FAIL"
    print(f"TOTAL (no filter)")
    print(f"  CRM: {CRM_TOTAL:>8,}  |  API: {str(api_total):>8}  |  {match_sym} {note}")
    print()

    # ── 2. Per-status breakdown ─────────────────────────────────────────────────
    print(SEP)
    print(f"{'Status':<20} {'CRM':>8}  {'API':>8}  {'Match':>6}  Note")
    print(SEP)

    api_sum = 0
    accessible = []
    not_filterable = []

    for status, crm_count in CRM_COUNTS.items():
        api_count, note = get_total(status)

        if api_count is None:
            sym = "N/A "
            not_filterable.append((status, crm_count))
            api_display = "N/A"
        else:
            api_sum += api_count
            accessible.append((status, crm_count, api_count))
            diff = api_count - crm_count
            if diff == 0:
                sym = "PASS   "
            elif abs(diff) <= 5:
                sym = f"~{diff:+d} "
            else:
                sym = f"FAIL{diff:+d}"
            api_display = f"{api_count:,}"

        print(f"  {status:<18} {crm_count:>8,}  {api_display:>8}  {sym}  {note}")

    print(SEP)
    print()

    # ── 3. Summary ──────────────────────────────────────────────────────────────
    print("SUMMARY")
    print(f"  CRM total (screenshot) : {CRM_TOTAL:>8,}")
    print(f"  API total (no filter)  : {str(api_total):>8}")
    print(f"  API sum (filterable)   : {api_sum:>8,}")
    print()

    crm_filterable_sum = sum(c for _, c, _ in accessible)
    crm_not_filterable_sum = sum(c for _, c in not_filterable)
    print(f"  Statuses accessible via API filter : {len(accessible)}")
    print(f"  Statuses NOT filterable (400)      : {len(not_filterable)}")
    if not_filterable:
        print(f"  Not-filterable statuses + their CRM counts:")
        for s, c in not_filterable:
            print(f"    {s:<20} CRM={c:,}")
        print(f"  Sum of not-filterable             : {crm_not_filterable_sum:,}")
    print()
    print(f"  Filterable sum check: {api_sum:,} (API) vs {crm_filterable_sum:,} (CRM filterable only)")
    gap = CRM_TOTAL - (api_sum + crm_not_filterable_sum)
    print(f"  Unaccounted gap                    : {gap:,}")
