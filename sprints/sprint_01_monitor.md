# Sprint 1 — Agent 2: Monitor

## Overview

| Field | Value |
|-------|-------|
| Goal | AI polls FTF CRM every 60 min, detects new unprocessed orders, writes to state DB |
| Status | 🔄 In Progress |
| Dates | Started: 2026-05-21 |
| Reads From | [sprint_00_foundation.md](sprint_00_foundation.md) — needs `core/ftf_client.py`, `core/db.py`, `core/logger.py`, `db/schema.sql` (processed_orders table) all confirmed working |
| Outputs | `code/sprint_01_monitor/agents/agent_02_monitor.py`, `code/sprint_01_monitor/tests/test_monitor.py` |

---

## Tasks

- [x] `code/sprint_01_monitor/agents/agent_02_monitor.py`
  - Calls `ftf_client.get_orders(limit=500)`
  - For each order: `db.order_exists(order_id)` → skip if already in DB (any status)
  - New orders → `db.save_order_state(order_id, status="pending")` + `db.log_decision()`
  - Logs each new order via `log.info()`
  - Returns list of new order IDs
  - No LLM calls — pure API + DB logic
  - Note: `db.order_exists()` added to `core/db.py` — replaces incorrect `get_pending_order(order_id)` reference in original plan
- [x] `code/sprint_01_monitor/tests/test_monitor.py` (7 tests — all pass)
  - UT-01-01: 3 new orders → all 3 written
  - UT-01-02: 1 existing order → skipped, not reset
  - UT-01-03: empty API response → no errors
  - UT-01-04: all existing → nothing written
  - UT-01-05: log_decision called per new order
  - UT-01-06: no LLM call made
  - EC-01-03: numeric order IDs cast to string
- [ ] Integration test on staging: submit 3 real test orders to FTF → confirm all 3 detected (Sprint 10)

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| 3 new test orders detected within 60 min | 🔲 | Integration test — Sprint 10 |
| 0 duplicates on 2nd run (same orders) | 🔲 | Integration test — Sprint 10 |
| `processed_orders` rows created with `status="pending"` | 🔲 | Integration test — Sprint 10 |
| `agent_decision_log` row written per order | 🔲 | Integration test — Sprint 10 |
| Unit tests pass (7 scenarios) | ✅ | 42/42 pass (Sprint 0 + Sprint 1 combined) |
| Empty order list handled without errors | ✅ | UT-01-03 |

---

## Blockers

_None expected._

---

## Decisions Made

- **`order_exists()` added to `core/db.py`** — Original sprint plan referenced `db.get_pending_order(order_id)` to check if an order exists, but that function takes no arguments. Added `order_exists(order_id: str) -> bool` which queries `SELECT 1 FROM processed_orders WHERE order_id = %s`. This prevents the monitor from resetting already-processed orders back to `pending`.
- **Order ID cast to `str()`** — FTF API may return numeric order IDs; the monitor casts all IDs to string before DB operations to match the `order_id VARCHAR` column type.

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | Unit tests, integration test, DB rows written correctly | Yes |
| Operations SME | Robert / Mark | Confirm the correct orders from FTF CRM are detected — no missed orders, no false positives | Yes |
| Business Stakeholders | Ryan, Jessica, Wyatt | Not involved this sprint | No |

---

## Completion Brief

_Written here when sprint is marked ✅ Complete. Then add one-liner link to `memory.md` → Sprint Briefs._

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 2:**
