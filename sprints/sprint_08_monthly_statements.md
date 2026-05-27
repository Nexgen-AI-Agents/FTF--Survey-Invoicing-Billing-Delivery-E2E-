# Sprint 8 — Agents 15–17: Monthly Statement Loop

## Overview

| Field | Value |
|-------|-------|
| Goal | 1st of every month — compile all B2B orders, generate Excel + PDF per client, deliver via email + Teams |
| Status | ✅ Complete (2026-05-27) |
| Reads From | FTF REST API (B2B orders), `db/schema.sql` (monthly_statements) |
| Outputs | `agent_15_statement_generator.py`, `agent_16_statement_reviewer.py`, `agent_17_statement_sender.py`, 3 new DB functions, `get_b2b_orders_for_month()` in ftf_client.py, SMTP + output dir settings, 19 tests |

---

## Tasks

- [x] `code/shared/config/settings.py` — add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `STATEMENT_OUTPUT_DIR`
- [x] `code/shared/core/ftf_client.py` — add `get_b2b_orders_for_month(month)`
- [x] `code/shared/core/db.py` — add `upsert_monthly_statement`, `get_generated_statements`, `update_statement_status`
- [x] `code/sprint_08_monthly_statements/agents/agent_15_statement_generator.py`
- [x] `code/sprint_08_monthly_statements/agents/agent_16_statement_reviewer.py`
- [x] `code/sprint_08_monthly_statements/agents/agent_17_statement_sender.py`
- [x] `code/sprint_08_monthly_statements/tests/conftest.py`
- [x] `code/sprint_08_monthly_statements/tests/test_statement_generator.py` (10 tests)
- [x] `code/sprint_08_monthly_statements/tests/test_statement_reviewer.py` (5 tests)
- [x] `code/sprint_08_monthly_statements/tests/test_statement_sender.py` (4 tests)

---

## Statement Spec (Confirmed 2026-05-27)

| Field | Value |
|-------|-------|
| Format | Excel (2 tabs: Unpaid Detail + Summary) + PDF (summary page) |
| Trigger | 1st of every calendar month (generates prior month's statement) |
| B2B filter | `customer_type="b2b"` from FTF REST API |
| Columns | Order #, Service Type, Date of Service, Invoice Amount, Payment Status, Balance Due |
| Delivery | Email attachment to billing contact + Teams to Ryan, Wyatt, Jessica |
| Exclusion list | Empty on launch; supported by schema |

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| `_order_row` unpaid includes balance | ✅ | |
| `_order_row` paid shows $0.00 balance | ✅ | |
| `_build_excel` creates .xlsx file | ✅ | |
| Excel has "Unpaid Detail" + "Summary" sheets | ✅ | |
| Detail tab row count matches order list | ✅ | |
| Summary tab totals reflect order amounts | ✅ | |
| `_build_pdf` creates .pdf file | ✅ | |
| `_group_by_client` groups by billing email | ✅ | |
| `_group_by_client` skips blank emails | ✅ | |
| Agent 15 run generates 1 statement per client | ✅ | |
| Reviewer validates correct statement → pass | ✅ | |
| Reviewer detects row count mismatch → fail | ✅ | |
| Reviewer handles missing Excel gracefully | ✅ | |
| Reviewer marks valid statement 'reviewed' | ✅ | |
| Reviewer marks failed when PDF missing | ✅ | |
| Sender skips email if SMTP_HOST not set | ✅ | |
| Sender skips Teams if webhook not set | ✅ | |
| Sender marks statement 'sent' on success | ✅ | |
| Sender marks 'failed' on exception | ✅ | |

**239/239 total tests pass** (220 prior + 19 new)

---

## Decisions Made

- Logger PII filter was converting integer args to strings, breaking `%d` format strings. Fixed `_safe_mask()` to only apply PII masking to string values; non-strings pass through unchanged.
- `update_statement_status` called with keyword args — tests assert against `call_args.kwargs["status"]`.
- `get_b2b_orders_for_month` fetches all orders then filters client-side (API doesn't expose month/customer_type query params yet).

---

## Completion Brief

- **Built:** Excel + PDF statement generator (openpyxl + reportlab), reviewer with file/count/amount/duplicate validation, SMTP email sender + Teams notification
- **Tests:** 19/19 new pass; 239/239 total pass
- **Changed from plan:** No `statement_generator.txt` prompt needed — statement content is deterministic data formatting, not LLM-generated. Real Wyatt review remains Sprint 10 staging.
- **Carry forward for Sprint 9:** Orchestrator (agent_00 scheduler integration for monthly + AR loops)
