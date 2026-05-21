# Sprint 3 — Agent 4: Human Gate

## Overview

| Field | Value |
|-------|-------|
| Goal | AI evaluates 9 flag triggers per order — routes flagged orders to MS Teams, clears others to continue |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | [sprint_02_classifier_pricing.md](sprint_02_classifier_pricing.md) — needs classification dict (customer type, service, flood zone, special_pricing) as input |
| Outputs | `agent_04_human_gate.py`, `config/flag_triggers.py` (updated with competitor list when received), MS Teams alert confirmed working |

---

## Tasks

- [ ] `agents/estimate_generation/agent_04_human_gate.py` — evaluate all 9 triggers
- [ ] MS Teams webhook integration test (alert actually sends)
- [ ] `config/flag_triggers.py` — update `COMPETITOR_NAMES` + `NEVER_AUTO_QUOTE` when Robert/Mark deliver list
- [ ] `tests/unit/test_human_gate.py`
- [ ] Integration test: competitor, ALTA, Other Services, out-of-state — all 4 fire alerts

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
| ALTA Table A Survey → Teams alert fired | 🔲 | |
| Other Services → Teams alert fired | 🔲 | |
| Out-of-state property → Teams alert fired | 🔲 | |
| Normal order → passes through, no alert | 🔲 | |
| Teams alert contains order_id, customer, service, flag reason | 🔲 | |
| Post-approval: AI auto-sends without manual click | 🔲 | |

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

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 4:**
