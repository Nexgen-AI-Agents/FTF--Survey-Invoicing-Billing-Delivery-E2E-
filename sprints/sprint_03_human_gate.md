# Sprint 3 — Agent 4: Human Gate

## Overview

| Field | Value |
|-------|-------|
| Goal | AI evaluates 9 flag triggers per order — routes flagged orders to MS Teams, clears others to continue |
| Status | ✅ Complete (partial) — 2026-05-25. Triggers 1–5, 8, 9 + Monroe County built. Approval inbound (I-025) stubbed. |
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
- [ ] MS Teams webhook live integration test (needs real TEAMS_WEBHOOK_URL — Sprint 10+)
- [ ] `config/flag_triggers.py` — COMPETITOR_NAMES + NEVER_AUTO_QUOTE validated by Robert/Mark (I-038)
- [ ] Approval inbound mechanism (I-025 — Ryan/Robert decision needed)
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
| Post-approval: AI auto-sends without manual click | 🔲 | Blocked on I-025 (approval mechanism undefined) |

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

- **Built:** agent_04_human_gate.py (notify_human, check_approval stub, run); 4 new flag triggers added to Agent 3 (competitor name, competitor domain, out-of-state, Monroe County); get_flagged_order() + get_order_by_id() added to db.py
- **Tests:** 13/13 pass (Sprint 3); 119/119 pass (full suite — Sprints 0–3)
- **Changed from plan:** Flag trigger logic kept in Agent 3 Classifier (not duplicated in Agent 4); check_approval() is a DB-polling stub pending I-025 resolution
- **Carry forward for Sprint 4:** I-025 approval mechanism; Robert/Mark competitor list validation (I-038); live Teams webhook integration test
