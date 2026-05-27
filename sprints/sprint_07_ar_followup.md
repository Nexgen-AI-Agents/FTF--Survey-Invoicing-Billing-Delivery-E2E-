# Sprint 7 — Agents 10–11: AR Internal Escalation Alerts

## Overview

| Field | Value |
|-------|-------|
| Goal | Daily internal Teams alerts when invoices cross Day 60 / Day 90 overdue thresholds |
| Status | ✅ Complete (2026-05-27) |
| Reads From | FTF Books API (XLSX), `db/schema.sql` (ar_reminders, excluded_ar_clients) |
| Outputs | `agent_10_ar_scanner.py`, `agent_11_ar_escalation.py`, `ftf_books_client.py`, 3 new DB functions, 12 tests |

**Scope change from original plan:** FTF platform sends Day 30/60/90 client-facing reminder emails automatically — we do NOT build those. Sprint 7 is internal-only: detect overdue invoices and fire Teams alerts to the right people. (Confirmed 2026-05-27.)

---

## Tasks

- [x] `code/shared/config/settings.py` — add `FTF_BOOKS_BASE_URL`, `FTF_BOOKS_USER`, `FTF_BOOKS_PASSWORD`, `AR_ALERT_DAYS_60`
- [x] `code/shared/core/ftf_books_client.py` — Books session login + Excel download + parse
- [x] `code/shared/core/db.py` — add `upsert_ar_reminder`, `get_invoices_due_for_escalation`, `update_ar_escalation_level`
- [x] `code/sprint_07_ar_followup/agents/agent_10_ar_scanner.py` — download invoices, upsert ≥60d into ar_reminders
- [x] `code/sprint_07_ar_followup/agents/agent_11_ar_escalation.py` — send Teams alerts (Day 60 → Jessica, Day 90 → all stakeholders)
- [x] `code/sprint_07_ar_followup/tests/conftest.py`
- [x] `code/sprint_07_ar_followup/tests/test_ar_scanner.py` (6 tests — _parse_excel + agent_10)
- [x] `code/sprint_07_ar_followup/tests/test_ar_escalation.py` (6 tests — agent_11 logic)

---

## Escalation Policy (Confirmed 2026-05-27)

| Days Past Due | Our Action | Channel | Teams Recipients |
|--------------|-----------|---------|-----------------|
| **Day 60** | Internal alert | Teams | Jessica only |
| **Day 90** | Internal alert | Teams | Jessica, Ryan, Mark, Robert, Wyatt |
| **90+** | Jessica handles manually | Manual | — |

FTF platform sends Day 30/60/90 **client-facing** emails — we do not touch those.

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| `_parse_excel` returns list of dicts | ✅ | |
| `_parse_excel` calculates days_overdue correctly | ✅ | |
| `_parse_excel` skips rows without order_id | ✅ | |
| `_parse_excel` handles empty sheet | ✅ | |
| `_parse_excel` parses ISO string dates | ✅ | |
| Agent 10 only upserts invoices ≥60d | ✅ | 45d invoice skipped |
| Agent 11 sends 90d alert, advances level to 3 | ✅ | |
| Agent 11 sends 60d alert, advances level to 2 | ✅ | |
| 90d processed before 60d (order check) | ✅ | |
| No alerts when no overdue invoices | ✅ | |
| No Teams HTTP call when webhook URL is None | ✅ | |
| Decision logged for each alert | ✅ | |

**220/220 total tests pass** (208 prior + 12 new)

---

## Decisions Made

- `openpyxl` returns `datetime` objects for date cells — check `isinstance(raw_date, datetime)` before `date` since `datetime` subclasses `date`
- `ar_reminders.order_id` has no UNIQUE constraint — use SELECT-then-INSERT/UPDATE in `upsert_ar_reminder`
- 90-day escalations queried and sent first so no invoice can be double-counted at both tiers in a single run

---

## Completion Brief

- **Built:** FTF Books XLSX client, AR scanner agent, AR escalation agent, 3 DB functions, 12 tests
- **Tests:** 12/12 new pass; 220/220 total pass
- **Changed from plan:** Reduced from 5 agents (10–14) to 2 agents (10–11) — FTF handles client reminder emails; we handle only internal escalation alerts
- **Carry forward for Sprint 8:** Monthly Statements Loop (Agents 15–17, Wyatt ACTIVE, unblocked)
