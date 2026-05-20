# Sprint 1 — Agent 2: Monitor

## Overview

| Field | Value |
|-------|-------|
| Goal | AI polls FTF CRM every 60 min, detects new unprocessed orders, writes to state DB |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | [sprint_00_foundation.md](sprint_00_foundation.md) — needs `core/ftf_client.py`, `core/db.py`, `core/logger.py`, `db/schema.sql` (processed_orders table) all confirmed working |
| Outputs | `agents/estimate_generation/agent_02_monitor.py`, `tests/unit/test_monitor.py` — confirmed: new orders detected, duplicates skipped, state DB rows created correctly |

---

## Tasks

- [ ] `agents/estimate_generation/agent_02_monitor.py`
  - Call `ftf_client.get_orders(status="pending", limit=500)`
  - For each order: `db.get_pending_order(order_id)` → skip if already exists
  - New orders → `db.save_order_state(order_id, status="pending")`
  - Log each new order via `log.info()`
  - Return list of new order IDs to orchestrator
  - No LLM calls — pure API + DB logic
  - Model: none (Haiku assigned in models.py but not used here)
- [ ] `tests/unit/test_monitor.py`
  - Test: 3 mock orders returned by API → all 3 written to DB
  - Test: 1 order already in DB → skipped, only 2 new ones written
  - Test: API returns empty list → no errors, returns empty list
- [ ] Integration test on staging: submit 3 real test orders to FTF → confirm all 3 detected within 60 min

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| 3 new test orders detected within 60 min | 🔲 | |
| 0 duplicates on 2nd run (same orders) | 🔲 | |
| `processed_orders` rows created with `status="pending"` | 🔲 | |
| `agent_decision_log` row written per order | 🔲 | |
| Unit tests pass (3 scenarios) | 🔲 | |
| Empty order list handled without errors | 🔲 | |

---

## Blockers

_None expected._

---

## Decisions Made

_Log here as they happen during this sprint._

---

## Completion Brief

_Written here when sprint is marked ✅ Complete. Then add one-liner link to `memory.md` → Sprint Briefs._

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 2:**
