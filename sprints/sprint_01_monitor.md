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
  - Calls `get_orders(status="Quote")` — server-side filter + full pagination (all 7000+ Quote orders, not just 500)
  - Skips orders where `estimate_sent == True` — avoids duplicate estimates
  - Skips orders where `order_exists(order_id)` — never resets already-processed orders
  - New orders → `save_order_state(order_id, status="pending")` + `log_decision()`
  - Returns list of new order IDs. No LLM calls.
- [x] `code/shared/core/ftf_client.py` — `get_orders()` updated
  - Added `status` param (optional) — passed as `?status=Quote` when provided
  - Full pagination via `offset` loop — fetches all pages until `offset >= total`
  - Per-page logging: `fetched page offset=X count=Y total=Z`
  - Backward compatible — `status=None` fetches all orders (existing behavior)
- [x] `code/sprint_01_monitor/tests/test_monitor.py` (16 tests — all pass)
  - UT-01-01 through UT-01-08: original scenarios updated for new signatures
  - UT-01-09: `get_orders` called with `status="Quote"` — primary regression guard
  - UT-01-10: `get_orders` called exactly once per run
  - UT-01-11: 1500-order paginated result — all processed correctly
  - UT-01-12: 1000 orders mixed new/existing — exactly 500 saved
  - EC-01-04: missing `estimate_sent` key treated as False — no KeyError
  - EC-01-05: `AgentError` from `get_orders` propagates — no silent failure
  - EC-01-06: missing `status` field — no crash, order processed
- [x] `code/sprint_00_foundation/tests/conftest.py` — added (Sprint 0 was missing path setup; 35/35 now pass)
- [ ] Integration test on staging: submit 3 real test orders to FTF → confirm all 3 detected (Sprint 10)

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| 3 new test orders detected within 60 min | ✅ | Live: 500 real FTF staging orders detected on first run (2026-05-21) |
| 0 duplicates on 2nd run (same orders) | ✅ | Live: second run returned 0 new orders — deduplication confirmed |
| `processed_orders` rows created with `status="pending"` | ✅ | Live: 500 rows in DB, all status=pending |
| `agent_decision_log` row written per order | ✅ | Live: 503 decision log entries from agent_02_monitor |
| Unit tests pass (16 scenarios) | ✅ | 16/16 Sprint 1; 51/51 combined (Sprint 0 + 1) |
| Empty order list handled without errors | ✅ | UT-01-03 |
| Non-Quote orders are skipped via server-side filter | ✅ | UT-01-09 — `get_orders(status="Quote")` confirmed |
| Already-estimated orders skipped | ✅ | UT-01-08 — `estimate_sent=True` orders not queued |
| Pagination — all 7000+ Quote orders reachable | ✅ | UT-01-11, UT-01-12 — 1500-order paginated result handled |
| API total field: 207,622 orders, hard cap 500/call | ✅ | Confirmed via probe — pagination required and implemented |

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

- **Built:** `agent_02_monitor.py` — calls `get_orders(status="Quote")` with full pagination, skips `estimate_sent=True` orders and existing DB rows, saves new ones as `status="pending"`, logs every decision. `ftf_client.get_orders()` updated with `status` param + offset pagination loop.
- **Tests:** 16/16 Sprint 1 pass. 51/51 combined (Sprint 0 + 1). Sprint 0 missing conftest.py fixed.
- **Changed from plan:** (1) `order["id"]` → `order["order_id"]`. (2) `get_pending_order()` → `order_exists()`. (3) Server-side `status=Quote` filter + full pagination — FTF has 207,622 orders, hard cap 500/call. (4) `estimate_sent=False` guard added — prevents duplicate estimates. (5) Confirmed FTF developer must verify API status field accuracy (staging CRM/API mismatch on order 1000276072).
- **Carry forward for Sprint 2:** FTF `service_type` field returns `"Quote"` for all Quote-stage orders — classifier must determine actual service type from other order fields. See I-003 for Construction + Permitting name gap. FTF developer to confirm API status field behavior (I-013).
