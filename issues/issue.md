# Issue Tracker — FTF Agentic AI OS

## Status Lifecycle

```
OPEN → IN DEV → DEV COMPLETE → QA JUNIOR → QA SENIOR → QA MANAGER → RELEASED → CLOSED
                                      ↑____________________________|
                                      (QA FAIL at any level → back to IN DEV)
```

## Severity Definitions

| Severity | Meaning |
|----------|---------|
| **BLOCKER** | Cannot proceed to next sprint. Stops all work on this sprint now. |
| **CRITICAL** | Must fix before release. Does not block other sprint work. |
| **MAJOR** | Significant regression or incorrect behavior. Should fix in current sprint. |
| **MINOR** | Cosmetic or low-impact. Tracked but not sprint-blocking. |

---

## Open Issues

| ID | Sprint | Severity | Title | Assigned | Status | Opened | Notes |
|----|--------|----------|-------|----------|--------|--------|-------|
| I-001 | Sprint 2 | CRITICAL | Competitor names + domains list missing — Agent 4 flag logic incomplete | dev_manager | OPEN | 2026-05-21 | Robert/Mark must provide before Sprint 3 (Human Gate). `flag_triggers.py`: COMPETITOR_NAMES=[], COMPETITOR_DOMAINS=[]. Blocks trigger #3 and #4. |
| I-002 | Sprint 2 | CRITICAL | Never-auto-quote service list missing — Agent 4 flag trigger #2 incomplete | dev_manager | OPEN | 2026-05-21 | Robert/Mark must provide before Sprint 3. `flag_triggers.py`: NEVER_AUTO_QUOTE=[]. Blocks trigger #2. |
| I-003 | Sprint 2 | CRITICAL | Exact FTF names for Construction + Permitting surveys unknown | dev_manager | OPEN | 2026-05-21 | Robert/Mark must provide before Sprint 2 (Classifier). 22 of 24 services confirmed. These 2 cannot be classified correctly without exact names. |
| I-004 | Sprint 2 | MAJOR | B-II Title Review flag status unconfirmed | dev_manager | OPEN | 2026-05-21 | `service_names.json`: `"flag": "pending_confirmation"`. Robert/Mark to confirm: always-flag or auto-quote? Blocks classifier for this service type. |
| I-005 | Sprint 2 | MAJOR | Wetland Delineation — does NexGen perform this service? | dev_manager | OPEN | 2026-05-21 | `service_names.json`: `"flag": "pending_confirmation"`. Robert/Mark to confirm if this service should be in the 24-service list or removed. |
| I-006 | Sprint 7 | CRITICAL | Jessica recording (Recording 10) not yet conducted | dev_manager | OPEN | 2026-05-21 | Blocks Sprint 7 AR loop. Need: exact 5-tier reminder schedule, 90-day escalation confirmation, client exclusion list. Jessica AI agent STUB until enriched. |
| I-007 | Sprint 8 | CRITICAL | Wyatt recording (Recording 11) not yet conducted | dev_manager | OPEN | 2026-05-21 | Blocks Sprint 8 monthly statements. Need: statement format confirmation, B2B delivery method confirmation. Wyatt AI agent STUB until enriched. |
| I-008 | Sprint 6 | MAJOR | Change order clause not reviewed by Ryan before go-live | dev_manager | OPEN | 2026-05-21 | `config/knowledge_base/change_order_clause.txt` must be drafted and sent to Ryan for review before Sprint 6 milestone. Confirmed: in-house draft, not blocked for build. |
| I-013 | Sprint 11 | MAJOR | FTF API returns 207,622 orders but CRM shows 275,693 — 68,071 orders missing from API | dev_manager | OPEN | 2026-05-22 | Probed all params (archived, deleted, all, include_archived) — total fixed at 207,622. Likely API key scope issue. Also: order 1000276072 API=Quote, CRM=Checking — status field accuracy unconfirmed. Code is correct; this is a pre-production concern only. FTF developer to answer before Sprint 11 go-live: (1) Why are 68,071 orders missing? (2) Is the API key scoped to a subset? (3) Does `?status=Quote` reliably reflect CRM status? Does NOT block Sprint 2 or any build sprint. |
| I-014 | Sprint 2 | BLOCKER | Geocoding capability missing — no way to convert property_address to lat/lng for FEMA flood zone check | dev_manager | OPEN | 2026-05-22 | Raised by BA review. FEMA client takes lat/lng but FTF API only provides property_address string. No geocoding client exists in core/. No geocoding service mentioned in BRD or ADRs. Sprint 2 FEMA integration tests cannot pass without this. Action: ADR required + build core/geocoding_client.py as Sprint 2 first task. Options: Google Maps Geocoding API (paid) or OpenStreetMap Nominatim (free). |
| I-015 | Sprint 2 | CRITICAL | GET /orders/{id} individual order response schema unknown — may be only path to actual service_type | dev_manager | OPEN | 2026-05-22 | Raised by BA review. Bulk GET /orders returns service_type="Quote" for all Quote-stage orders — actual service name unavailable. Individual order endpoint get_order(order_id) exists in ftf_client.py but response schema not confirmed. If it returns richer fields (notes, description, actual service), classifier can use it. Action: test GET /orders/{id} on staging immediately and document full response schema before Sprint 2 code is written. |
| I-016 | Sprint 2 | CRITICAL | GET /customers/{id} response schema unknown — customer type (B2B/individual) and email field names unconfirmed | dev_manager | OPEN | 2026-05-22 | Raised by BA review. Sprint 2 Classifier needs customer type for pricing tier. get_customer(customer_id) exists in ftf_client.py but response schema not confirmed. Action: test GET /customers/{id} on staging and document full response schema before Sprint 2 classifier is built. |
| I-017 | Sprint 2 | MAJOR | Monitor stores only order_id at detection time — Classifier must call get_order() per order, API call volume impact unknown | dev_manager | OPEN | 2026-05-22 | Raised by BA review. processed_orders table has no property_address, customer_id, created_at columns. Sprint 2 Classifier must call get_order(order_id) for each pending order to retrieve data needed for classification. With 500+ orders per run, this is 500+ sequential API calls. Confirm FTF API rate limit applies to bulk GET /orders only (not individual GETs) before Sprint 2 design is finalized. |
| I-018 | Sprint 6 | MINOR | PII masking in logger.py covers email addresses only — phone numbers, property addresses, customer names logged in plain text | dev_manager | OPEN | 2026-05-22 | Raised by Dev Manager + BA review. logger.py _mask_pii() regex matches email format only. Property addresses and customer names will flow through Sprint 2+. Must be resolved before Sprint 6 (Sender) when real customer data flows through estimate emails. Not urgent for Sprint 2. |
| I-019 | Sprint 10 | MINOR | No prompt caching in claude_client.py — cost risk at scale with 7000+ Quote orders | dev_manager | OPEN | 2026-05-22 | Raised by BA review. claude_client.py does not implement cache_control headers. At staging scale (Sprint 10 cost benchmark), every reasoning agent call is a fresh context. Recommend adding cache_control to system prompts before Sprint 10. Non-blocking until then. |
| I-020 | Sprint 2 | MAJOR | ftf_client.py pagination silently returns empty list if API returns total=0 on first call | dev_manager | OPEN | 2026-05-22 | Raised by Dev Manager review. If API returns total=0 on first page (misconfigured or flaky), offset >= total (0 >= 0) exits immediately with empty list and no warning. In an automated billing pipeline, silent empty return is dangerous. Fix: add logger.warning if total=0 and no orders returned on first page. |
| I-021 | Sprint 2 | MAJOR | logger.py dict-style record.args converted to string before masking — breaks dict-format log calls with TypeError | dev_manager | OPEN | 2026-05-22 | Raised by Dev Manager review. logger.py line 22: if record.args is a dict, it is converted to str before masking, making record.args a string. Logging formatter then tries %(...) substitution against a string → TypeError at emit time. No current code uses dict-style logging but any future log call with %(key)s format will crash. Fix: mask dict values individually: {k: _mask_pii(str(v)) for k, v in record.args.items()}. |
| I-022 | Sprint 2 | MINOR | SERVICE_STATE = "FL" defined in both flag_triggers.py and settings.py — duplicate constant, one is dead code | dev_manager | OPEN | 2026-05-22 | Raised by Dev Manager review. Low risk but creates confusion about which is authoritative. Remove from flag_triggers.py (settings.py is the correct home for config constants). |

---

## Closed Issues

| ID | Sprint | Severity | Title | Resolved By | Closed | Resolution |
|----|--------|----------|-------|-------------|--------|------------|
| I-009 | Sprint 0 | CRITICAL | `db.get_pending_order()` used in sprint plan to check if order exists — function takes no args | dev_manager | 2026-05-21 | Added `order_exists(order_id: str) -> bool` to `core/db.py`. Sprint 1 agent uses this instead. |
| I-010 | Sprint 0 | MINOR | `test_get_pricing_raises_pricing_error_on_failure` called `get_pricing()` without required `service` arg | dev_manager | 2026-05-21 | Fixed test to call `get_pricing("Boundary Survey")`. |
| I-011 | Sprint 0 | MINOR | `state.py` uses deprecated `datetime.datetime.utcnow()` — DeprecationWarning on Python 3.14 | dev_manager | 2026-05-21 | Replaced all 4 calls with `datetime.datetime.now(datetime.UTC)`. |
| I-012 | Sprint 1 | MAJOR | Monitor saved ALL FTF orders regardless of status — Delivered/Complete/Cancelled orders incorrectly queued | dev_manager | 2026-05-22 | Added FTF status filter: only `status="Quote"` orders are processed. Confirmed via FTF staging CRM — order 1000275451 was Delivered but appeared in queue. Added UT-01-07 to cover this case. 8/8 tests pass. |

---

## Issue ID Format

`I-NNN` — sequential. Example: `I-001`, `I-002`, `I-003`.

## How to Log a New Issue

Add a row to **Open Issues** with:
- **ID**: next sequential number
- **Sprint**: which sprint's code (e.g., Sprint 0)
- **Severity**: BLOCKER / CRITICAL / MAJOR / MINOR
- **Title**: one-line description of the problem
- **Assigned**: `junior_dev`, `senior_dev`, or `dev_manager`
- **Status**: `OPEN`
- **Opened**: YYYY-MM-DD
- **Notes**: exact input that caused it + what happened + what was expected

## How to Close an Issue

Move the row to **Closed Issues** and fill in Resolved By, Closed date, and Resolution.
