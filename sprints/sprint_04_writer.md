# Sprint 4 — Agent 6: Writer + Change Order Clause

## Overview

| Field | Value |
|-------|-------|
| Goal | AI writes personalized estimate email (individual=warm, B2B=professional) and appends change order clause as last section |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | [sprint_03_human_gate.md](sprint_03_human_gate.md) — needs cleared order (passed Human Gate) with classification + pricing data |
| Outputs | `agent_06_writer.py`, `config/knowledge_base/change_order_clause.txt`, `config/prompts/writer.txt`, `templates/estimate_email.md`, draft estimate email text |

---

## Tasks

- [ ] Draft `config/knowledge_base/change_order_clause.txt` — in-house draft (Ryan reviews before go-live, not before build)
- [ ] `config/prompts/writer.txt` — full prompt: tone rules, estimate structure, clause append instruction
- [ ] `templates/estimate_email.md` — reusable email structure
- [ ] `agents/estimate_generation/agent_06_writer.py` — loads clause via `Path(...).read_text()`, appends as last section, never modifies clause
- [ ] `tests/unit/test_writer.py`
- [ ] Sample outputs: 1 individual estimate, 1 B2B estimate

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| Individual estimate — warm/friendly tone | 🔲 | |
| B2B estimate — concise/professional tone | 🔲 | |
| Change order clause present as last section — every estimate | 🔲 | |
| Clause text unmodified (exact match to file) | 🔲 | |
| Customer name correct | 🔲 | |
| Price matches pricing engine output | 🔲 | |
| Property address correct | 🔲 | |

---

## Blockers

_None — change order clause drafted in-house. Ryan reviews text at Sprint 6 demo; adjustments are a text file edit, not a code change._

---

## Decisions Made

_Log here as they happen._

---

## Completion Brief

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 5:**
