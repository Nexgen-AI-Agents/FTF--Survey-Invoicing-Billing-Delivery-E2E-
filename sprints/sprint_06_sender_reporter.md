# Sprint 6 — Agent 8: Sender + Agent 9: Reporter ⭐

## Overview

| Field | Value |
|-------|-------|
| Goal | AI sends validated estimate with 6–13 min random delay; daily digest to all stakeholders via MS Teams. MILESTONE: first full end-to-end estimate on staging. |
| Status | ✅ Complete |
| Dates | 2026-05-26 |
| Reads From | [sprint_05_reviewer.md](sprint_05_reviewer.md) — needs validated estimate + invoice line items; needs `core/ftf_client.py` (`create_invoice`, `send_invoice`, `mark_estimate_sent`) |
| Outputs | `agent_08_sender.py`, `agent_09_reporter.py`, `config/prompts/reporter.txt`, confirmed estimate in Ryan's inbox, daily Teams digest |

---

## Pre-Sprint Dependency Check

### ✅ Buildable Without External Dependencies

| Item | Notes |
|------|-------|
| Agent 8 Sender | `create_invoice` + `send_invoice` + `mark_estimate_sent` all exist in `ftf_client.py` |
| Agent 9 Reporter | Teams webhook + POST pattern already used in Agent 4 |
| DB helpers (`get_reviewed_order`, `get_daily_summary`) | Pure SQL queries |
| All unit tests | All external calls mocked |

### ⚠️ Noted (Non-blocking)

| Item | Notes |
|------|-------|
| I-018 PII masking | Customer email in log lines — resolve before production (Sprint 11) |
| I-043 change order clause | Ryan reviews text before go-live; no code change required |

---

## Tasks

- [x] `code/sprint_06_sender_reporter/agents/agent_08_sender.py` — create invoice → random delay → send → mark sent → log
- [x] `code/sprint_06_sender_reporter/agents/agent_09_reporter.py` — daily digest from DB → Teams post (deterministic template)
- [x] `code/shared/config/prompts/reporter.txt` — reporter prompt stub (available for future LLM enrichment)
- [x] `code/shared/core/db.py` — add `get_reviewed_order()` + `get_daily_summary()`
- [x] `code/sprint_06_sender_reporter/tests/conftest.py` — sys.path setup
- [x] `code/sprint_06_sender_reporter/tests/test_sender.py` — 8 unit tests
- [x] `code/sprint_06_sender_reporter/tests/test_reporter.py` — 5 unit tests

---

## Status Flow

```
reviewed → (Agent 8: delay + FTF create_invoice + send_invoice + mark_estimate_sent) → sent
```

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| send_estimate creates invoice and sends | ✅ | test_send_estimate_creates_and_sends_invoice |
| send_estimate updates DB to 'sent' | ✅ | test_send_estimate_updates_db_to_sent |
| send_estimate logs decision | ✅ | test_send_estimate_logs_decision |
| delay applied (in [360, 780]) | ✅ | test_send_estimate_applies_delay |
| missing order → AgentError | ✅ | test_send_estimate_raises_on_missing_order |
| wrong status → AgentError | ✅ | test_send_estimate_raises_on_wrong_status |
| zero amount → AgentError | ✅ | test_send_estimate_raises_on_zero_amount |
| outside 8AM–6PM ET → returns None, no invoice created (I-024) | ✅ | test_send_estimate_returns_none_outside_send_window |
| transient failure → retries, succeeds on 2nd attempt (I-024) | ✅ | test_send_estimate_retries_on_transient_failure |
| all MAX_SENDER_RETRIES fail → status=error, AgentError (I-024) | ✅ | test_send_estimate_marks_error_after_max_retries |
| run() picks reviewed order | ✅ | test_run_picks_reviewed_order |
| report POSTs to Teams webhook | ✅ | test_report_posts_to_teams |
| report contains sent_today count | ✅ | test_report_contains_sent_today_count |
| report contains flagged count | ✅ | test_report_contains_flagged_count |
| report returns True on success | ✅ | test_report_returns_true_on_success |
| webhook failure → AgentError | ✅ | test_report_raises_on_webhook_failure |

---

## Milestone Sign-Off

**Ryan must confirm:** test estimate received, looks correct and professional → GO for Sprint 10 staging tests.

---

## Blockers

_None._

---

## Decisions Made

- Sender uses `time.sleep()` directly — patchable via `patch("agents.agent_08_sender.time.sleep")`.
- Reporter is fully deterministic (no LLM for this sprint) — stats digest doesn't need language generation. Reporter prompt stub (`reporter.txt`) available for future LLM enrichment.
- Invoice ID extracted with `.get("invoice_id") or .get("id", "")` fallback — FTF API key unconfirmed.
- `get_daily_summary()` uses PostgreSQL `FILTER (WHERE ...)` aggregates — one query for all stats.
- Split into two files (`agent_08_sender.py` + `agent_09_reporter.py`) per "one agent, one job" rule. README had combined into single file — corrected.

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | All 13 tests, delay behavior, Teams digest payload | Yes |
| Decision Maker | Ryan | Open test estimate in inbox — confirm it looks professional, correct, change order clause visible. **Must sign off before Sprint 10.** | Yes — MILESTONE |
| Operations SME | Robert AI | Confirm sent estimate status transitions are correct | Via AI agent |
| Business Stakeholders | Jessica, Wyatt | Review daily Teams digest format | Optional |

---

## Completion Brief

- **Built:** `agent_08_sender.py` (create→delay→send→mark FTF flow + 8AM–6PM ET window + MAX_SENDER_RETRIES retry loop); `agent_09_reporter.py` (deterministic Teams digest with 5 stats); `db.py` updated with `get_reviewed_order()` + `get_daily_summary()`; `reporter.txt` prompt stub
- **Tests:** 16 unit tests, all passing; full suite 141/141
- **Changed from plan:** Reporter is fully deterministic (no LLM) — template-based stats digest is faster, cheaper, and no hallucination risk. LLM prompt stub (`reporter.txt`) available for future enrichment. Split two agents into separate files (original README had combined).
- **Carry forward for Sprint 7:** I-006 (Jessica recording) required before AR Follow-Up; I-018 PII masking must resolve before Sprint 11; I-043 Ryan reviews change order clause text before go-live
