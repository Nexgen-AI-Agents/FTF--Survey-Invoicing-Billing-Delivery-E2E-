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
