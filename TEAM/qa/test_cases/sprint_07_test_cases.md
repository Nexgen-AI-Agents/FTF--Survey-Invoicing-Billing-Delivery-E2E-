# Sprint 7 — Test Cases: Agents 10–11 AR Internal Escalation Alerts

> Written by Senior QA before dev starts. All cases must pass before Sprint 7 is marked ✅ Complete.
> Reference: `sprints/sprint_07_ar_followup.md`

---

## Unit Tests (`code/sprint_07_ar_followup/tests/test_ar_scanner.py` + `test_ar_escalation.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-07-01 | `_parse_excel` returns list of dicts | FTF Books XLSX file with 5 invoice rows | Returns list of 5 dicts with `order_id`, `days_overdue`, `amount`, `billing_email` | ✅ |
| UT-07-02 | `_parse_excel` calculates days_overdue correctly | Invoice with due date 65 days ago | `days_overdue == 65` (calculated from today) | ✅ |
| UT-07-03 | `_parse_excel` skips rows without order_id | Row with blank `order_id` cell | Row skipped — not included in returned list | ✅ |
| UT-07-04 | `_parse_excel` handles empty sheet | XLSX with header row only, no data | Returns `[]` — no crash | ✅ |
| UT-07-05 | `_parse_excel` parses ISO string dates | Date cell contains `"2026-03-01"` string | `days_overdue` correctly calculated from string date | ✅ |
| UT-07-06 | `_parse_excel` handles datetime objects (not just date) | `openpyxl` returns `datetime` for date cell | `isinstance(raw_date, datetime)` check applied; parsed correctly | ✅ |
| UT-07-07 | Agent 10 only upserts invoices ≥60d overdue | 45d invoice + 65d invoice in XLSX | 65d upserted; 45d skipped | ✅ |
| UT-07-08 | Agent 11 sends Day 60 alert — level advances to 2 | Invoice at `days_overdue=65`, `escalation_level=1` | Teams POST to Jessica only; `escalation_level` updated to 2 | ✅ |
| UT-07-09 | Agent 11 sends Day 90 alert — level advances to 3 | Invoice at `days_overdue=95`, `escalation_level=2` | Teams POST to Jessica + Ryan + Mark + Robert + Wyatt; `escalation_level` updated to 3 | ✅ |
| UT-07-10 | 90-day escalations processed before 60-day in same run | Mix of 90d and 60d invoices | 90d alerts sent first; no invoice double-counted at both tiers | ✅ |
| UT-07-11 | No alerts when no overdue invoices | `get_invoices_due_for_escalation()` returns `[]` | No Teams POST; run completes cleanly | ✅ |
| UT-07-12 | No Teams HTTP call when webhook URL is None | `TEAMS_WEBHOOK_URL=None` | No `httpx.post()` call; `AgentError` raised | ✅ |
| UT-07-13 | Decision logged for each alert sent | 2 alerts sent (1× Day 60, 1× Day 90) | `log_decision()` called 2× with `agent_name="agent_11_ar_escalation"` | ✅ |
| UT-07-14 | Refund request → routes to Jessica ONLY — AI does NOT handle | Order flagged as refund request | No AI action taken; Jessica notified; status set to `"refund_pending_jessica"` | ✅ |
| UT-07-15 | `excluded_ar_clients` list honored | Client on exclusion list has overdue invoice | Invoice NOT escalated; skipped | ✅ |
| UT-07-16 | `upsert_ar_reminder` uses SELECT-then-INSERT/UPDATE | Order already in `ar_reminders` | No duplicate rows; existing row updated | ✅ |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-07-01 | Day 60 alert fires on staging | Insert test invoice with `days_overdue=61` in staging DB; run `agent_11_ar_escalation.py` | Jessica receives Teams alert; `escalation_level=2` in `ar_reminders` | ✅ |
| IT-07-02 | Day 90 alert fires to all stakeholders on staging | Insert test invoice with `days_overdue=91`; run agent 11 | All 5 stakeholders (Jessica, Ryan, Mark, Robert, Wyatt) receive Teams alert | ✅ |
| IT-07-03 | 45-day invoice NOT escalated | Invoice with `days_overdue=45` in FTF Books XLSX | No row upserted; no Teams alert | ✅ |
| IT-07-04 | Jessica approves AR action on staging | Jessica reviews Teams alert, marks action taken in FTF | Order status updated; no second alert fired in next run | ✅ |
| IT-07-05 | FTF Books XLSX download succeeds on staging | Run `agent_10_ar_scanner.py` with staging FTF Books URL | XLSX downloaded, parsed, invoices ≥60d upserted to `ar_reminders` | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-07-01 | Refund request arrives — AI takes NO action | Order metadata contains `"refund"` or refund flag | Routed to Jessica exclusively; zero AI processing; logged as `"refund_routed_to_jessica"` | ✅ |
| EC-07-02 | Same invoice at Day 90 threshold — not re-escalated if already level 3 | Invoice with `escalation_level=3` | No Teams alert; `update_ar_escalation_level` not called | ✅ |
| EC-07-03 | FTF Books login failure (bad credentials) | `FTF_BOOKS_PASSWORD` wrong | `AgentError` raised; no partial data written | ✅ |
| EC-07-04 | XLSX format changes — unexpected columns | New column added by FTF | Agent logs warning; processes known columns; no crash | ✅ |
| EC-07-05 | Zero-amount invoice in XLSX | `amount == 0` | Skipped — zero-dollar AR escalation not triggered | ✅ |
| EC-07-06 | Teams alert for 90d contains correct recipient list | Day 90 escalation | Alert addressed to Jessica + Ryan + Mark + Robert + Wyatt — not just one person | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 7)

- [ ] UT-07-01 through UT-07-16 all pass
- [ ] Day 60 alert → Jessica ONLY
- [ ] Day 90 alert → all 5 stakeholders (Jessica, Ryan, Mark, Robert, Wyatt)
- [ ] Invoices < 60 days overdue are NEVER escalated
- [ ] 90-day escalations processed before 60-day in every run
- [ ] Refund requests ALWAYS route to Jessica — AI takes zero action on refunds
- [ ] Excluded clients never escalated
- [ ] `upsert_ar_reminder` is idempotent — no duplicate rows
- [ ] `AgentError` raised when no Teams webhook configured
- [ ] FTF platform's own Day 30/60/90 client emails are NOT duplicated by our agents
- [ ] Jessica (AR Lead) confirms alert timing and format on staging
- [ ] Prateek (CTO) sign-off on all 12 tests

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 7.
- SCOPE: FTF sends Day 30/60/90 client-facing reminder emails — we only build internal escalation alerts.
- `openpyxl` returns `datetime` objects for date cells — `isinstance(datetime)` checked before `date` because `datetime` subclasses `date`.
- Sprint 7 completed 2026-05-27 — 12/12 tests pass; full suite 220/220.
