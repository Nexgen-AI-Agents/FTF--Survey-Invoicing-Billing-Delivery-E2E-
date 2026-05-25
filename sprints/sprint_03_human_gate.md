# Sprint 3 — Agent 4: Human Gate

## Overview

| Field | Value |
|-------|-------|
| Goal | AI evaluates 9 flag triggers per order — routes flagged orders to MS Teams, clears others to continue |
| Status | ✅ Complete — 2026-05-25. All buildable items done. I-025 approval mechanism + escalation check built; live Teams integration test deferred to Sprint 10. |
| Dates | TBD |
| Reads From | [sprint_02_classifier_pricing.md](sprint_02_classifier_pricing.md) — needs classification dict (customer type, service, flood zone, special_pricing) as input |
| Outputs | `agent_04_human_gate.py`, `config/flag_triggers.py` (updated with competitor list when received), MS Teams alert confirmed working |

---

## Tasks

- [x] `agents/agent_04_human_gate.py` — notify_human(), check_approval() (stub), run(); Teams POST, DB state transitions
- [x] Triggers 1–5 (service flags, competitor name/domain) and 8–9 (FEMA unavail, out-of-state) moved to Agent 3 Classifier
- [x] Monroe County hard flag (I-034) added to Agent 3 Classifier
- [x] `tests/conftest.py` + `tests/test_human_gate.py` — 13 tests covering notify, approval polling, error handling, payload structure
- [x] `db/schema.sql` — status values updated to include awaiting_approval, approved, rejected
- [x] `agent_02_monitor.py` — `main(argv)` CLI entrypoint with `--run-now` flag (I-023)
- [x] `agent_04_human_gate.py` — `process_approval_reply()`, `run_escalation_check()`, `_send_escalation_alert()`, full CLI entrypoint (I-025 code-complete)
- [x] `core/db.py` — `get_overdue_approvals(timeout_hours)` added
- [x] `config/settings.py` — `APPROVAL_TIMEOUT_HOURS` added (default 24h, env-configurable)
- [x] Tests: UT-01-13, UT-01-14 (CLI), UT-03-09 through UT-03-16 (approval + escalation) — 131/131 pass
- [ ] MS Teams webhook live integration test (needs real TEAMS_WEBHOOK_URL — Sprint 10+)
- [ ] `config/flag_triggers.py` — COMPETITOR_NAMES + NEVER_AUTO_QUOTE validated by Robert/Mark (I-038)
- [ ] Integration test: competitor, ALTA, Other Services, out-of-state — all fire alerts on staging

---

## 9 Flag Triggers Reference

1. Service in `ALWAYS_FLAG_SERVICES` (ALTA Table A Survey, Other Services)
2. Service in `NEVER_AUTO_QUOTE` (Robert/Mark list — pending)
3. Company name in `COMPETITOR_NAMES` (Robert/Mark list — pending)
4. Email domain in `COMPETITOR_DOMAINS` (Robert/Mark list — pending)
5. Unusual property (large acreage, tidal, special site)
6. New customer — uncertain genuine vs. competitor
7. Reviewer failure after 3 loops
8. FEMA API returned `"UNAVAILABLE"`
9. `property_state != "FL"` — NGE Florida-only

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| ALTA Table A Survey → Teams alert fired | ✅ | UT-02-03 in test_classifier.py |
| Other Services → Teams alert fired | ✅ | UT-02-03 |
| Out-of-state property → Teams alert fired | ✅ | UT-02-17 |
| Competitor company name → Teams alert fired | ✅ | UT-02-15 |
| Competitor email domain → Teams alert fired | ✅ | UT-02-16 |
| Monroe County → Teams alert fired (I-034) | ✅ | UT-02-18 |
| Normal FL order → passes through, no alert | ✅ | multiple passing tests |
| Teams alert contains order_id, service, flag reason | ✅ | UT-03-08 |
| notify_human() saves awaiting_approval status | ✅ | UT-03-02 |
| check_approval() polls DB status (stub) | ✅ | UT-03-04 |
| Missing TEAMS_WEBHOOK_URL → AgentError | ✅ | UT-03-05 |
| Teams HTTP/network failure → AgentError | ✅ | UT-03-06 |
| process_approval_reply() approve/reject updates DB | ✅ | UT-03-09, UT-03-10 |
| process_approval_reply() invalid/wrong-status → AgentError | ✅ | UT-03-11, UT-03-13 |
| run_escalation_check() fires orange alert for overdue orders | ✅ | UT-03-15 |
| run_escalation_check() no webhook → AgentError | ✅ | UT-03-16 |
| CLI --run-now triggers monitor run (I-023) | ✅ | UT-01-13 |
| Post-approval: AI auto-sends without manual click | 🔲 | Requires live Teams integration — Sprint 10 |

---

## Blockers

_`COMPETITOR_NAMES` + `NEVER_AUTO_QUOTE` pending from Robert/Mark — framework built now, list plugs in when received._

---

## Decisions Made

_Log here as they happen._

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | All 9 flag triggers fire correctly, Teams webhook delivers alert | Yes |
| Operations SME | Robert / Mark | Confirm the right orders are flagged — no false flags on normal orders, no missed flags on ALTA/Other Services/competitor | Yes |
| Decision Maker | Ryan | Review Teams alert format — confirm it contains all info needed to make a decision | Yes |
| Business Stakeholders | Jessica, Wyatt | Not involved this sprint | No |

---

## Completion Brief

- **Built:** agent_04_human_gate.py (notify_human, check_approval stub, run, process_approval_reply, run_escalation_check, main CLI); 4 new flag triggers added to Agent 3 (competitor name, competitor domain, out-of-state, Monroe County); get_flagged_order() + get_order_by_id() + get_overdue_approvals() added to db.py; APPROVAL_TIMEOUT_HOURS added to settings.py; agent_02_monitor.py CLI entrypoint with --run-now flag (I-023)
- **Tests:** 21/21 pass (Sprint 3); 131/131 pass (full suite — Sprints 0–3)
- **Changed from plan:** Flag trigger logic kept in Agent 3 Classifier (not duplicated in Agent 4); check_approval() is a DB-polling stub (I-025 inbound mechanism TBD); process_approval_reply() is the inbound handler — any mechanism (CLI, Teams bot, webhook) can call it
- **Carry forward for Sprint 4:** Live Teams webhook integration test (Sprint 10); Robert/Mark competitor list validation (I-038)
