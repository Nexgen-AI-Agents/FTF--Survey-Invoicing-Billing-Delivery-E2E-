# A2 "Unknown" Sentinel Bug — Root Cause & Fix

**Date:** 2026-06-05  
**Affected orders:** 1000283728, 1000283564, 1000283486 (and potentially others)  
**Status:** Fixed in `agent_a2_data_collector.py`

---

## What Happened

Orders were showing `client_name = "Unknown"` and `property_address = "Unknown"` in the
pipeline state, even though MySQL (`ng_orders`) had correct data for all three orders:

| Order | DB client_name | DB property_address |
|-------|---------------|---------------------|
| 1000283486 | Garrett Bender | 610 SE 3RD AVE |
| 1000283564 | Law Offices of Cary P. Sabol | 5301 S DIXIE HWY |
| 1000283728 | DITI GLAZER | 7800 LAKE WORTH RD |

---

## Root Cause 1: Python `or` doesn't guard against truthy sentinel strings

**File:** `agent_a2_data_collector.py` — `collect_for_order()` → `save_order_state()` call

```python
# BROKEN — "Unknown" is truthy so `or db_value` never fires
client_name = str(packet.get("client_name", {}).get("value") or client_name)
```

The A2 AI prompt instructs Claude to return the literal string `"Unknown"` when a field
can't be found. Python's `or` only falls back when the left side is **falsy**.
`"Unknown"` is a non-empty string → truthy → the fallback never fires.

The local `client_name` variable WAS correctly populated from MySQL before this point.
The correct value was silently overwritten by `"Unknown"`.

**Fix:** `_resolve_field()` helper added at module level:

```python
_UNKNOWN_SENTINELS = frozenset({"unknown", "n/a", "none", "not available", "not found", ""})

def _resolve_field(extracted_val, fallback: str) -> str:
    if extracted_val and str(extracted_val).strip().lower() not in _UNKNOWN_SENTINELS:
        return str(extracted_val)
    return fallback

# FIXED
client_name = _resolve_field(packet.get("client_name", {}).get("value"), client_name)
property_address = _resolve_field(packet.get("property_address", {}).get("value"), property_address)
```

---

## Root Cause 2: Excel state has no county column

**File:** `agent_a2_data_collector.py` — line ~499

A1 saves orders to Excel but does NOT save the county field (Excel schema has no county column).
When A2 reads `db_row.get("county", "")` it always gets `""`.
The FTF API also didn't return county for these orders.
Result: the county property appraiser lookup failed with "No county provided".

**Fix:** Direct MySQL fallback added:

```python
_db_county = db_row.get("county", "")
if not _db_county:
    try:
        _mysql_row = mysql_get_order_details(order_id)
        _db_county = str(_mysql_row.get("ng_property_county") or "")
    except Exception:
        pass
```

---

## Why These Orders Were Escalating

A3's Claude AI escalated all three with `escalate_flag = True`. Some reasons were caused
by this bug; others are legitimate and remain after the fix:

| Order | Escalation Reason | Bug-caused? | Remains? |
|-------|------------------|-------------|----------|
| 1000283728 | Duplicate of order 1000278035 (same folio/address) | No | Yes |
| 1000283728 | Missing legal description | No | Yes |
| 1000283564 | FTF submission had no address/county/client | Partly | Partly |
| 1000283564 | Commercial property, certification name unverified | No | Yes |
| 1000283486 | CAD scope unclear | Partly | Partly |
| 1000283486 | Suspected duplicates (1000215601, 1000281647) | No | Yes |

---

## Pattern to Watch

Any `save_order_state()` call that uses bare `or` with an AI-extracted value is vulnerable:

```python
# Dangerous pattern — check ALL occurrences
some_field = str(packet.get("field_name", {}).get("value") or db_fallback)
```

AI models return non-empty sentinel strings when data is missing. They don't return
Python `None` or empty string. Use `_resolve_field()` everywhere AI output feeds into
`save_order_state()`.

---

## Verification

After the fix:
1. Run `python skills/verify-a2-output/run.py` — must return PASS
2. Orders 1000283728, 1000283564, 1000283486 should show correct names/addresses
3. Some escalation flags may remain (duplicates, missing legal desc) — those are correct
