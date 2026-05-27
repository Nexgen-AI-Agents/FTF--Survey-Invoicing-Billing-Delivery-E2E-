# Sprint 5 — Test Cases: Agent 7 Reviewer (Self-Correction Loop)

> Written by Senior QA before dev starts. All cases must pass before Sprint 5 is marked ✅ Complete.
> Reference: `sprints/sprint_05_reviewer.md`

---

## Unit Tests (`code/sprint_05_reviewer/tests/test_reviewer.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-05-01 | Correct estimate passes all 4 checks on first review | Draft with correct price, name, address, and full clause | Returns `"approved"` on first pass — no retry | ✅ |
| UT-05-02 | Wrong price detected — sends back to Writer with correction note | Draft has `"$500"` but pricing engine says `$450` | `_run_checks()` returns `["price_mismatch"]`; `write_estimate(correction_note=)` called | ✅ |
| UT-05-03 | Wrong customer name detected — sends back to Writer | Draft has `"J. Doe"` but order has `"John Doe"` | `_run_checks()` returns `["customer_name_mismatch"]`; retry triggered | ✅ |
| UT-05-04 | Wrong property address detected — sends back to Writer | Draft has abbreviated address; order has full address | `_run_checks()` returns `["address_mismatch"]`; retry triggered | ✅ |
| UT-05-05 | Missing change order clause detected — sends back to Writer | Draft ends without clause text | `_run_checks()` returns `["missing_clause"]`; retry triggered | ✅ |
| UT-05-06 | Modified clause detected — sends back to Writer | Clause text differs by one word from `change_order_clause.txt` | `_run_checks()` returns `["clause_modified"]`; retry triggered | ✅ |
| UT-05-07 | 2nd attempt passes after 1st failure | Retry draft corrects the price | Returns `"approved"` on 2nd attempt | ✅ |
| UT-05-08 | 3rd consecutive failure → `ReviewerFailError` raised | 3 drafts all fail same check | `ReviewerFailError` raised after 3rd loop | ✅ |
| UT-05-09 | `ReviewerFailError` triggers Human Gate escalation | `ReviewerFailError` from 3rd failure | Agent 4 Human Gate notified with `flag_reason="reviewer_failed_3x"` | ✅ |
| UT-05-10 | Retry counter resets correctly on a new order | Order A fails 2×, then Order B processed | Order B starts at retry count 0 | ✅ |
| UT-05-11 | `_run_checks()` is a pure deterministic function — no LLM | Any valid inputs | No LLM call in `_run_checks()` — string comparison only | ✅ |
| UT-05-12 | Multiple failures on single attempt — all reasons returned | Draft missing both price and clause | `_run_checks()` returns list with both `"price_mismatch"` and `"missing_clause"` | ✅ |
| UT-05-13 | DB status updated to `"reviewed"` on pass | Draft passes all 4 checks | `processed_orders.status = "reviewed"` | ✅ |
| UT-05-14 | DB status remains `"written"` during retry | Draft fails check, retry triggered | Status stays `"written"` — not advanced until final pass | ✅ |
| UT-05-15 | Correction note includes specific check that failed | Retry triggered for price mismatch | `correction_note` passed to Writer contains `"price"` — specific, not generic | ✅ |
| UT-05-16 | `write_estimate` imported at module level for mockability | Any reviewer test | `write_estimate` patchable without importing agent_06 | ✅ |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-05-01 | End-to-end: estimate passes reviewer on first attempt | Submit clean individual order; run full pipeline through agent 7 | `status="reviewed"` in DB; no retries in decision log | ✅ |
| IT-05-02 | Reviewer catches incorrect price — corrected on retry | Submit order; mock Writer to produce wrong price first, correct on retry | Decision log shows 2 attempts; final status `"reviewed"` | ✅ |
| IT-05-03 | 3x failure → Human Gate escalation on staging | Force 3 consecutive bad drafts from Writer mock | Teams alert received with `flag_reason="reviewer_failed_3x"`; order halted | ✅ |
| IT-05-04 | Clause unmodified confirmed on staging estimate | Generate real estimate on staging | Clause in final draft matches `change_order_clause.txt` byte-for-byte | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-05-01 | Writer returns empty draft on retry | `AgentError` raised — empty draft fails all 4 checks immediately | ✅ |
| EC-05-02 | Clause present but not as final section | `_run_checks()` returns `["clause_not_last"]`; retry triggered | ✅ |
| EC-05-03 | Price in draft matches but formatting differs (`$450` vs `450.00`) | Reviewer normalizes format for comparison — not a false mismatch | ✅ |
| EC-05-04 | All 4 checks fail simultaneously on first attempt | All 4 failure reasons listed in correction note; 1 retry counted (not 4) | ✅ |
| EC-05-05 | `change_order_clause.txt` updated after agent starts | Reviewer loads clause fresh each check — detects old clause in draft | ✅ |
| EC-05-06 | Writer returns draft with extra whitespace around clause | Clause comparison strips trailing whitespace — not a false mismatch | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 5)

- [ ] UT-05-01 through UT-05-16 all pass
- [ ] All 4 validation checks (price, name, address, clause) covered by at least 2 tests each
- [ ] 3-retry limit enforced — `ReviewerFailError` raised on 3rd failure (never on 2nd or earlier)
- [ ] `ReviewerFailError` routes to Human Gate — not silenced
- [ ] Retry counter isolated per order — no bleed between orders
- [ ] `_run_checks()` is deterministic — no LLM involved in validation
- [ ] DB status advances to `"reviewed"` only on clean pass
- [ ] Clause exact-match check implemented — partial matches fail
- [ ] Prateek (CTO) sole sign-off (no business stakeholder involvement this sprint)

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 5.
- Reviewer is deterministic — pure string matching, no LLM needed for 4 checks.
- `estimate_reviewer.txt` prompt stub available for future LLM enrichment if needed.
- Sprint 5 completed 2026-05-26 — 16 unit tests (6 pure + 10 integration) all passing; full suite 125/125.
