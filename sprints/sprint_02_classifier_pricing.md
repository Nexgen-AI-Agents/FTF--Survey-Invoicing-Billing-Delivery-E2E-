# Sprint 2 — Agent 3: Classifier + Agent 5: Pricing Engine

## Overview

| Field | Value |
|-------|-------|
| Goal | AI classifies order (customer type, FEMA flood zone, pricing tier); AI looks up correct price using 2-level lookup |
| Status | ✅ Complete — 2026-05-25 |
| Dates | TBD |
| Reads From | [sprint_01_monitor.md](sprint_01_monitor.md) — needs Monitor's order list from DB as input; needs `core/ftf_client.py`, `core/fema_client.py`, `core/claude_client.py` |
| Outputs | `agent_03_classifier.py`, `agent_05_pricing_engine.py`, `config/prompts/classifier.txt` (stub), structured classification dict, pricing result dict |

---

## Tasks

- [x] `agents/agent_03_classifier.py` — classify_order(); 14 flag triggers (ALWAYS_FLAG, NEVER_AUTO_QUOTE, VE zone, missing county, false FL lat, FEMA unavail)
- [x] `agents/agent_05_pricing_engine.py` — price_order(); FTF API lookup, override support, elevation cert add-on
- [x] `code/shared/config/prompts/classifier.txt` — stub; LLM disabled until Robert/Mark recordings (Sprint 3)
- [x] `tests/conftest.py` — sys.path setup for shared + sprint root
- [x] `tests/test_classifier.py` — 22 unit tests covering all flag triggers + DB persistence
- [x] `tests/test_pricing_engine.py` — 15 unit tests covering pricing logic, overrides, elevation cert, error propagation
- [ ] Integration test: 1 individual order, 1 B2B, 1 flood zone property, 1 special-pricing customer

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| Individual customer type classified correctly | ✅ | UT-02-01 |
| B2B customer type classified correctly | ✅ | UT-02-02 |
| Flood zone property → `elevation_cert_required=True` | ✅ | UT-02-08 |
| Non-flood property → no elevation cert | ✅ | UT-02-08 |
| FEMA unavailable → flagged for human review | ✅ | UT-02-10 |
| VE zone → coastal flag (I-035) | ✅ | UT-02-09 |
| Missing county → data quality flag (I-036) | ✅ | UT-02-06 |
| False FL coordinate → flag (I-037) | ✅ | UT-02-07 |
| service_type="Quote" → flag (I-033) | ✅ | UT-02-05 |
| Pricing: correct amount from FTF API | ✅ | UT-02-15 |
| Pricing: company override used when `special_pricing=True` | ✅ | UT-02-18 |
| Pricing: elevation cert adds $225 | ✅ | UT-02-17 |
| PricingError propagates on API failure | ✅ | UT-02-20 |
| I-029 append-only guard in db.log_decision | ✅ | db.py dedup guard |

---

## Blockers

_Classifier LLM prompt needs recordings from Robert/Mark — build FEMA + customer type logic now; enrich prompt after recordings arrive._

---

## Decisions Made

_Log here as they happen._

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | Unit tests, FEMA integration, pricing accuracy vs. service_names.json | Yes |
| Operations SME | Robert / Mark | Verify service classification is correct for real FTF order types; confirm pricing amounts match what they expect | Yes |
| Business Stakeholders | Ryan, Jessica, Wyatt | Not involved this sprint | No |

---

## Completion Brief

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 3:**
