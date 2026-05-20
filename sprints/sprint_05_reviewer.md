# Sprint 5 — Agent 7: Reviewer

## Overview

| Field | Value |
|-------|-------|
| Goal | AI validates estimate before sending — 4 checks (price, name, address, clause). Self-corrects up to 3x. On 3rd fail → Human Gate escalation. |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | [sprint_04_writer.md](sprint_04_writer.md) — needs draft estimate email from Agent 6 Writer + original order data for comparison |
| Outputs | `agent_07_reviewer.py`, `config/prompts/reviewer.txt`, validated estimate or `ReviewerFailError` after 3 loops |

---

## Tasks

- [ ] `agents/estimate_generation/agent_07_reviewer.py` — 4 checks, up to 3 retry loops
- [ ] `config/prompts/reviewer.txt`
- [ ] `tests/unit/test_reviewer.py`
- [ ] Test: wrong price in estimate → reviewer catches, sends back to Writer
- [ ] Test: 3 consecutive failures → `ReviewerFailError` raised → Human Gate flag triggered

---

## 4 Validation Checks

1. Price in estimate matches `pricing_engine` output (exact match)
2. Customer name matches FTF order (exact, no abbreviation)
3. Property address matches FTF order (exact)
4. Change order clause present and unmodified (string compare against `change_order_clause.txt`)

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| Wrong price detected → sent back to Writer with correction note | 🔲 | |
| Wrong customer name detected → corrected | 🔲 | |
| Missing change order clause detected → corrected | 🔲 | |
| 3rd loop failure → `ReviewerFailError`, Human Gate alerted | 🔲 | |
| Correct estimate passes all 4 checks on first review | 🔲 | |

---

## Blockers

_None._

---

## Decisions Made

_Log here as they happen._

---

## Completion Brief

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 6:**
