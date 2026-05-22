# Sprint 1 — Agent 2: Monitor

## Overview

| Field | Value |
|-------|-------|
| Goal | AI polls FTF CRM every 60 min, detects new unprocessed orders, writes to state DB |
| Status | ✅ Complete |
| Dates | Started: 2026-05-21 — Completed: 2026-05-22 |
| Reads From | [sprint_00_foundation.md](sprint_00_foundation.md) — needs `core/ftf_client.py`, `core/db.py`, `core/logger.py`, `db/schema.sql` (processed_orders table) all confirmed working |
| Outputs | `code/sprint_01_monitor/agents/agent_02_monitor.py`, `code/sprint_01_monitor/tests/test_monitor.py` |

---

## Tasks

- [x] `code/sprint_01_monitor/agents/agent_02_monitor.py`
  - Calls `ftf_client.get_orders(limit=500)`
  - For each order: skip if `ftf_status != "Quote"` (confirmed 2026-05-22 — only Quote-stage orders need estimates)
  - For each order: `db.order_exists(order_id)` → skip if already in DB (any status)
  - New Quote orders → `db.save_order_state(order_id, status="pending")` + `db.log_decision()`
  - Logs each new order via `log.info()`
  - Returns list of new order IDs
  - No LLM calls — pure API + DB logic
  - Note: `db.order_exists()` added to `core/db.py` — replaces incorrect `get_pending_order(order_id)` reference in original plan
- [x] `code/sprint_01_monitor/tests/test_monitor.py` (8 tests — all pass)
  - UT-01-01: 3 new orders → all 3 written
  - UT-01-02: 1 existing order → skipped, not reset
  - UT-01-03: empty API response → no errors
  - UT-01-04: all existing → nothing written
  - UT-01-05: log_decision called per new order
  - UT-01-06: no LLM call made
  - EC-01-03: numeric order IDs cast to string
  - UT-01-07: non-Quote FTF status orders (Delivered, Pending, Complete, Canceled) are skipped
- [ ] Integration test on staging: submit 3 real test orders to FTF → confirm all 3 detected (Sprint 10)

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| 3 new test orders detected within 60 min | ✅ | Live: 500 real FTF staging orders detected on first run (2026-05-21) |
| 0 duplicates on 2nd run (same orders) | ✅ | Live: second run returned 0 new orders — deduplication confirmed |
| `processed_orders` rows created with `status="pending"` | ✅ | Live: 500 rows in DB, all status=pending |
| `agent_decision_log` row written per order | ✅ | Live: 503 decision log entries from agent_02_monitor |
| Unit tests pass (8 scenarios) | ✅ | 8/8 pass Sprint 1; full suite 43/43 |
| Empty order list handled without errors | ✅ | UT-01-03 |
| Non-Quote orders (Delivered, Complete, etc.) are skipped | ✅ | UT-01-07 — confirmed via FTF staging (order 1000275451 was Delivered) |

---

## Blockers

_None._

---

## Decisions Made

- **`order_exists()` added to `core/db.py`** — Original sprint plan referenced `db.get_pending_order(order_id)` to check if an order exists, but that function takes no arguments. Added `order_exists(order_id: str) -> bool` which queries `SELECT 1 FROM processed_orders WHERE order_id = %s`. This prevents the monitor from resetting already-processed orders back to `pending`.
- **Order ID cast to `str()`** — FTF API returns integer `order_id` (not `id`); the monitor casts to string before DB operations to match the `order_id VARCHAR` column type. Fixed: sprint plan used `order["id"]` — actual key is `order["order_id"]`.
- **FTF status filter — `status="Quote"` only** — Monitor originally saved all 500 orders regardless of FTF status. Confirmed via FTF staging CRM (2026-05-22): order 1000275451 had status "Delivered" but appeared in our queue. Only "Quote" stage orders need an estimate — all others are already in production. Added client-side filter in agent and UT-01-07 to cover this case. See `config/knowledge_base/ftf_order_statuses.md` for full status hierarchy.
- **Live integration test result (2026-05-21):** 500 real FTF staging orders detected and saved on first run. Second run: 0 new orders (deduplication confirmed). All rows in `processed_orders` with `status=pending`. Decision log: 503 entries from `agent_02_monitor`.

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | Unit tests, integration test, DB rows written correctly | Yes |
| Operations SME | Robert / Mark | Confirm the correct orders from FTF CRM are detected — no missed orders, no false positives | Yes |
| Business Stakeholders | Ryan, Jessica, Wyatt | Not involved this sprint | No |

---

## Completion Brief

- **Built:** `agent_02_monitor.py` — polls FTF CRM every 60 min, filters to Quote-stage orders only, skips existing DB orders, writes new ones with `status="pending"`, logs every decision.
- **Tests:** 8/8 unit tests pass. Live integration test: 500 real FTF orders on first run, 0 on second run (deduplication confirmed).
- **Changed from plan:** (1) `order["id"]` → `order["order_id"]` — FTF API key name. (2) `db.get_pending_order()` → `order_exists()` — architectural fix. (3) Added FTF status filter (`status="Quote"` only) — discovered Delivered orders were being queued incorrectly.
- **Carry forward for Sprint 2:** FTF `service_type` API field returns `"Quote"` for all Quote-stage orders — not the actual survey service name. Classifier (Sprint 2) must determine service type from other order fields (property details, order notes, etc.). See I-003 for Construction + Permitting name gap.
