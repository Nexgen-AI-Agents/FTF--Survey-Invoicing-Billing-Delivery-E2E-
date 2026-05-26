# Sprint 5 — Agent 7: Reviewer

## Overview

| Field | Value |
|-------|-------|
| Goal | AI validates estimate before sending — 4 checks (price, name, address, clause). Self-corrects up to 3x. On 3rd fail → Human Gate escalation. |
| Status | ✅ Complete |
| Dates | TBD |
| Reads From | [sprint_04_writer.md](sprint_04_writer.md) — needs draft estimate email from Agent 6 Writer + original order data for comparison |
| Outputs | `agent_07_reviewer.py`, `config/prompts/reviewer.txt`, validated estimate or `ReviewerFailError` after 3 loops |

---

## Tasks

- [x] `agents/agent_07_reviewer.py` — 4 checks, up to 3 retry loops; calls `write_estimate(correction_note=)` directly on failure
- [x] `shared/config/prompts/estimate_reviewer.txt` — reviewer system prompt (LLM-based check available for future use)
- [x] `tests/test_reviewer.py` — 16 unit tests (6 pure `_run_checks` + 10 integration), all passing
- [x] Test: wrong price in estimate → reviewer catches, sends back to Writer
- [x] Test: 3 consecutive failures → `ReviewerFailError` raised → Human Gate flag triggered

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
| Wrong price detected → sent back to Writer with correction note | ✅ | test_wrong_price_triggers_rewrite_then_passes |
| Wrong customer name detected → corrected | ✅ | test_run_checks_missing_customer_name |
| Missing change order clause detected → corrected | ✅ | test_missing_clause_triggers_rewrite |
| 3rd loop failure → `ReviewerFailError`, Human Gate alerted | ✅ | test_three_failures_raise_reviewer_fail_error |
| Correct estimate passes all 4 checks on first review | ✅ | test_review_estimate_passes_all_checks |

---

## Blockers

_None._

---

## Decisions Made

_Log here as they happen._

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | All 4 validation checks, retry loop behavior, ReviewerFailError escalation | Yes — sole tester |
| Business Stakeholders | Ryan, Robert, Mark, Jessica, Wyatt | Not involved — internal AI self-correction loop, no human-facing output this sprint | No |

---

## Completion Brief

- **Built:** `agent_07_reviewer.py` with deterministic 4-check validation + rewrite loop; `shared/config/prompts/estimate_reviewer.txt` drafted; `_run_checks()` pure function (no LLM needed for validation — deterministic string checks)
- **Tests:** 16 unit tests (6 pure + 10 integration), all passing; full suite 125/125
- **Changed from plan:** Reviewer is deterministic (no LLM call needed for 4 checks — pure string matching is more reliable and faster); LLM-based check available via estimate_reviewer.txt prompt for future enrichment; `write_estimate` imported at module level for mockability
- **Carry forward for Sprint 6:** I-044 design decision: Robert always reviews before sending — pipeline must be suggest-then-approve for ALL orders (not just flagged); affects Sprint 6 Sender
