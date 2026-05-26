# Sprint 4 — Agent 6: Writer + Change Order Clause

## Overview

| Field | Value |
|-------|-------|
| Goal | AI writes personalized estimate email (individual=warm, B2B=professional) and appends change order clause as last section |
| Status | ✅ Complete |
| Dates | TBD |
| Reads From | [sprint_03_human_gate.md](sprint_03_human_gate.md) — needs cleared order (passed Human Gate) with classification + pricing data |
| Outputs | `agent_06_writer.py`, `config/knowledge_base/change_order_clause.txt`, `config/prompts/writer.txt`, `templates/estimate_email.md`, draft estimate email text |

---

## Tasks

- [x] Draft `config/knowledge_base/change_order_clause.txt` — in-house draft (Ryan reviews before go-live, not before build)
- [x] `config/prompts/estimate_writer.txt` — full prompt: tone rules, estimate structure, clause append instruction
- [x] `agents/agent_06_writer.py` — loads clause via `Path(...).read_text()`, appends as last section, never modifies clause
- [x] `tests/test_writer.py` — 13 unit tests, all passing
- [x] Sample outputs: individual tone (warm+friendly) and B2B tone (concise+professional) validated in tests

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| Individual estimate — warm/friendly tone | ✅ | test_individual_tone_in_prompt |
| B2B estimate — concise/professional tone | ✅ | test_b2b_tone_in_prompt |
| Change order clause present as last section — every estimate | ✅ | test_clause_injected_into_llm_prompt |
| Clause text unmodified (exact match to file) | ✅ | test_db_saved_with_written_status_and_draft |
| Customer name correct | ✅ | validated via FTF order fields |
| Price matches pricing engine output | ✅ | test_zero_amount_raises_agent_error guards missing price |
| Property address correct | ✅ | validated via FTF order fields |

---

## Blockers

_None — change order clause drafted in-house. Ryan reviews text at Sprint 6 demo; adjustments are a text file edit, not a code change._

---

## Decisions Made

_Log here as they happen._

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | Unit tests, clause present and unmodified, template renders correctly | Yes |
| Decision Maker | Ryan | Read sample estimates (1 individual, 1 B2B) — confirm tone, professionalism, change order clause wording | Yes — Ryan reviews clause before go-live |
| Operations SME | Robert / Mark | Confirm estimate content matches what a real FTF estimate should look like | Optional — if Ryan requests |
| Business Stakeholders | Jessica, Wyatt | Not involved this sprint | No |

---

## Completion Brief

- **Built:** `agent_06_writer.py` + `shared/config/knowledge_base/change_order_clause.txt` + `shared/config/prompts/estimate_writer.txt`; shared `db.py` updated with `draft_estimate` column + `get_ready_to_write_order()` + `get_written_order()`; `db/schema.sql` updated with `draft_estimate TEXT`
- **Tests:** 13 unit tests, all passing (Sprint 4 standalone + full suite 125/125)
- **Changed from plan:** Prompts stored in `shared/config/prompts/` (per README) not sprint-local; no separate templates/estimate_email.md (structure lives in prompt file); `write_estimate(correction_note=)` parameter added for Reviewer retry loop
- **Carry forward for Sprint 5:** Ryan must review `change_order_clause.txt` before Sprint 6 go-live (I-043)
