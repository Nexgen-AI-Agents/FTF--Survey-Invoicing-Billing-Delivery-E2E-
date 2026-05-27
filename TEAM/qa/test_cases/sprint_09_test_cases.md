# Sprint 9 — Test Cases: Agent 1 Orchestrator + Memory/Dream Loops + Agent 18 Business Analyst

> Written by Senior QA before dev starts. All cases must pass before Sprint 9 is marked ✅ Complete.
> Reference: `sprints/sprint_09_memory_loop.md`

---

## Unit Tests (`code/sprint_09_memory_loop/tests/`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-09-01 | Memory manager writes dated log file | `agent_decision_log` has 10 rows for today | `docs/memory/YYYY-MM-DD.md` created with today's decisions | ✅ |
| UT-09-02 | Memory manager writes `latest.md` | Any successful run | `docs/memory/latest.md` overwritten with today's summary | ✅ |
| UT-09-03 | Memory manager groups decisions by agent | 5 decisions from agent_02, 3 from agent_03 | Memory file groups entries under `## agent_02_monitor` and `## agent_03_classifier` sections | ✅ |
| UT-09-04 | Memory manager counts errors correctly | 2 errors out of 10 decisions | `error_rate=20%` shown in memory file | ✅ |
| UT-09-05 | Memory manager handles empty decision log | `get_decisions_for_date()` returns `[]` | `docs/memory/YYYY-MM-DD.md` created with "No decisions today" — no crash | ✅ |
| UT-09-06 | Dream processor writes `reflection.md` | 7 days of decision log data | `docs/reflection.md` updated with pattern analysis | ✅ |
| UT-09-07 | Dream processor flags agents >10% error rate | Agent 03 has 15% error rate over 7 days | `reflection.md` contains `NEEDS ATTENTION` tag for agent_03 | ✅ |
| UT-09-08 | Dream processor appends on 2nd run (history preserved) | Run dream processor twice | `reflection.md` has entries from both runs — first run not overwritten | ✅ |
| UT-09-09 | Dream processor does NOT flag agents ≤10% error rate | Agent 02 has 5% error rate | `reflection.md` does NOT flag agent_02 | ✅ |
| UT-09-10 | Orchestrator logs `loop_start` decision | `agent_01_orchestrator.run()` called | `log_decision()` called with `decision="loop_start"` at beginning | ✅ |
| UT-09-11 | Orchestrator logs `loop_complete` decision | Successful pipeline run | `log_decision()` called with `decision="loop_complete"` at end | ✅ |
| UT-09-12 | Orchestrator saves `loop_state`: `"running"` → `"completed"` | `run()` completes successfully | `save_loop_state(loop_name=..., status="completed")` called | ✅ |
| UT-09-13 | Listener triggers pipeline on `"pending"` order | `NOTIFY` event with `order_id` and `status="pending"` | Pipeline triggered for that `order_id` | ✅ |
| UT-09-14 | Listener logs `started` and `stopped` | Listener starts and stops cleanly | `log_decision()` called with `decision="listener_started"` and `"listener_stopped"` | ✅ |
| UT-09-15 | Malformed LISTEN/NOTIFY payload does not crash | `NOTIFY` payload is `"not_json"` or `{}` | Warning logged; listener continues — no crash | ✅ |
| UT-09-16 | `get_decisions_since()` scopes to correct date range | 7 days requested | Returns only decisions from last 7 days | ✅ |
| UT-09-17 | `loop_state` UNIQUE constraint — upsert pattern works | Same `loop_name` called twice | No duplicate rows; second call updates existing row | ✅ |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-09-01 | Nightly memory log written on staging | Wait for GitHub Actions `nightly_memory.yml` to run at 04:00 UTC | `docs/memory/YYYY-MM-DD.md` and `latest.md` written to repo | ✅ |
| IT-09-02 | Dream processor flags no issues after clean run | After sprint 10 staging run with no errors | `reflection.md` updated; no `NEEDS ATTENTION` tags | ✅ |
| IT-09-03 | Orchestrator runs full estimate pipeline end-to-end | New test order inserted to DB as `"pending"`; run orchestrator | Order progresses through agents 2→3→5→4→6→7→8; final `status="sent"` | ✅ |
| IT-09-04 | DB trigger fires LISTEN/NOTIFY on order insert | Insert new `processed_orders` row with `status="pending"` | `notify_order_state_change()` trigger fires; listener receives notification | ✅ |
| IT-09-05 | GitHub Actions workflow `nightly_memory.yml` scheduled correctly | Check Actions schedule | Workflow shows scheduled at `04:00 UTC daily` | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-09-01 | Business Analyst distinguishes INVOICED vs COLLECTED vs POTENTIAL | Report request for revenue summary | Output explicitly labels and separates: INVOICED ≠ COLLECTED ≠ POTENTIAL — no conflation | ✅ |
| EC-09-02 | Dream processor run with only 1 day of data (not 7) | First day of production | Dream processor runs on available data; no crash on short history | ✅ |
| EC-09-03 | Orchestrator lazy-loads agents — no import errors | `agent_01_orchestrator.py` imported | Each agent module imported only when needed; no circular import | ✅ |
| EC-09-04 | Listener restarts every 6 hours (Actions schedule) | Check `order_listener.yml` | Workflow set to restart on 6-hour schedule | ✅ |
| EC-09-05 | Memory file written even if some agents had errors | 3 errors in decision log | Memory file written with error entries labeled; no crash | ✅ |
| EC-09-06 | `docs/memory/` directory created if missing | First run on fresh repo | Directory created; log file written; no crash | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 9)

- [ ] UT-09-01 through UT-09-17 all pass
- [ ] `docs/memory/YYYY-MM-DD.md` written nightly — date-stamped
- [ ] `docs/memory/latest.md` always reflects most recent run
- [ ] `reflection.md` appends on every run — history not overwritten
- [ ] Agents >10% error rate flagged `NEEDS ATTENTION` in reflection
- [ ] `loop_state` table UPSERT is idempotent
- [ ] Listener handles malformed payload without crashing
- [ ] Business Analyst output correctly distinguishes INVOICED / COLLECTED / POTENTIAL
- [ ] Orchestrator lazy-loads agents — unit tests remain clean
- [ ] `nightly_memory.yml` GitHub Actions workflow scheduled at 04:00 UTC
- [ ] `order_listener.yml` GitHub Actions workflow set to restart every 6 hours
- [ ] Prateek (CTO) sole sign-off (internal AI system — no business stakeholder testing)

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 9.
- Memory files go to `docs/memory/` (not `.claude/`).
- Agent 18 Business Analyst: key domain rule — INVOICED ≠ COLLECTED ≠ POTENTIAL. Test must verify no conflation.
- Sprint 9 completed 2026-05-26 — 17/17 tests pass; full suite 256/256 (combined).
