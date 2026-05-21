# Sprint 2 — Agent 3: Classifier + Agent 5: Pricing Engine

## Overview

| Field | Value |
|-------|-------|
| Goal | AI classifies order (customer type, FEMA flood zone, pricing tier); AI looks up correct price using 2-level lookup |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | [sprint_01_monitor.md](sprint_01_monitor.md) — needs Monitor's order list from DB as input; needs `core/ftf_client.py`, `core/fema_client.py`, `core/claude_client.py` |
| Outputs | `agent_03_classifier.py`, `agent_05_pricing_engine.py`, `config/prompts/classifier.txt` (stub), structured classification dict, pricing result dict |

---

## Tasks

- [ ] `agents/estimate_generation/agent_03_classifier.py`
- [ ] `agents/estimate_generation/agent_05_pricing_engine.py`
- [ ] `config/prompts/classifier.txt` (stub — will be enriched after Robert/Mark recordings)
- [ ] `tests/unit/test_classifier.py`
- [ ] `tests/unit/test_pricing_engine.py`
- [ ] Integration test: 1 individual order, 1 B2B, 1 flood zone property, 1 special-pricing customer

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| Individual customer type classified correctly | 🔲 | |
| B2B customer type classified correctly | 🔲 | |
| Flood zone property → `elevation_cert_required=True` | 🔲 | |
| Non-flood property → no elevation cert | 🔲 | |
| FEMA unavailable → `FEMAUnavailableError` raised | 🔲 | |
| Pricing: correct amount returned for 5 service types | 🔲 | |
| Pricing: company override used when `special_pricing=True` | 🔲 | |
| Unknown service → `PricingError` raised | 🔲 | |

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
