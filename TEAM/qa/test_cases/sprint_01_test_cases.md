# Sprint 1 — Test Cases: CRM Monitor (Agent 2)

> Written by Senior QA before dev starts. All cases must pass before Sprint 1 is marked ✅ Complete.
> Reference: `sprints/sprint_01_monitor.md`

---

## Unit Tests (`code/sprint_01_monitor/tests/test_monitor.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-01-01 | 3 new orders from API, none in DB | API returns `[{id: O-001}, {id: O-002}, {id: O-003}]`; `order_exists()` returns False for all | Returns `["O-001", "O-002", "O-003"]`; `save_order_state()` called 3× with `status="pending"` | 🔲 |
| UT-01-02 | 1 order already in DB — skipped | API returns `[{id: O-001}, {id: O-002}, {id: O-003}]`; `order_exists()` returns True for O-001 only | Returns `["O-002", "O-003"]`; `save_order_state()` called 2×; O-001 NOT reset | 🔲 |
| UT-01-03 | Empty API response | API returns `[]` | Returns `[]`; `save_order_state()` NOT called; no errors raised | 🔲 |
| UT-01-04 | All orders already in DB | API returns 3 orders; `order_exists()` returns True for all | Returns `[]`; `save_order_state()` NOT called | 🔲 |
| UT-01-05 | `log_decision()` called per new order | 2 new orders detected | `log_decision()` called exactly 2× with agent_name="agent_02_monitor" | 🔲 |
| UT-01-06 | Agent runs without LLM call | Any input | `claude_client.call()` is NEVER invoked | 🔲 |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-01-01 | 3 real test orders detected | Submit 3 orders via FTF staging CRM; run `python code/sprint_01_monitor/agents/agent_02_monitor.py` | 3 rows in `processed_orders` with `status="pending"` within 60 min | 🔲 |
| IT-01-02 | No duplicates on 2nd run | Run monitor twice with same 3 orders | `processed_orders` still has exactly 3 rows; no resets | 🔲 |
| IT-01-03 | `agent_decision_log` populated | After IT-01-01 run | 3 rows in `agent_decision_log` with `agent_name="agent_02_monitor"`, `decision="new_order_detected"` | 🔲 |
| IT-01-04 | Existing order NOT overwritten | Pre-insert O-001 with `status="classified"`; run monitor; API returns O-001 | O-001 still has `status="classified"` after monitor run | 🔲 |
| IT-01-05 | Empty CRM (no pending orders) | Run monitor against staging with 0 orders | No errors; returns `[]`; no DB rows created | 🔲 |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-01-01 | FTF API returns 500 error | `AgentError` raised; no DB writes; error logged | 🔲 |
| EC-01-02 | DB connection failure | Exception propagates up; no silent failures | 🔲 |
| EC-01-03 | Order ID is numeric (FTF sends int) | `str(order["id"])` cast works; saved correctly as string | 🔲 |
| EC-01-04 | 500 orders returned (max batch) | All 500 processed without timeout; duplicates correctly skipped | 🔲 |

---

## Acceptance Criteria (All must be green to close Sprint 1)

- [ ] UT-01-01 through UT-01-06 all pass
- [ ] No BLOCKER or CRITICAL issues in `issues/issue.md`
- [ ] `agent_02_monitor.py` has no `TODO`, `FIXME`, or unimplemented stubs
- [ ] No raw `httpx`, `psycopg2`, or `anthropic` calls inside agent file
- [ ] `order_exists()` used — existing orders are NEVER reset to `status="pending"`
- [ ] QE Manual confirmed: no PII in log output (emails masked)
- [ ] Prateek (CTO) sign-off on code review
- [ ] Robert / Mark (SME) confirm correct orders are being detected (integration test)

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 1.
- EC-01-01 and EC-01-02 are error path tests — run as part of unit test suite with mocks.
- Agent 2 has no LLM calls — all testing is deterministic.
