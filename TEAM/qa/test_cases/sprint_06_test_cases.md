# Sprint 6 — Test Cases: Agent 8 Sender + Agent 9 Reporter

> Written by Senior QA before dev starts. All cases must pass before Sprint 6 is marked ✅ Complete.
> Reference: `sprints/sprint_06_sender_reporter.md`

---

## Unit Tests (`code/sprint_06_sender_reporter/tests/test_sender.py` + `test_reporter.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-06-01 | `send_estimate()` creates invoice and sends | Reviewed order with valid draft | `ftf_client.create_invoice()` called, then `ftf_client.send_invoice()` called | ✅ |
| UT-06-02 | `send_estimate()` marks FTF estimate sent | Invoice created and sent successfully | `ftf_client.mark_estimate_sent()` called | ✅ |
| UT-06-03 | `send_estimate()` updates DB to `"sent"` | Successful invoice send | `processed_orders.status = "sent"` | ✅ |
| UT-06-04 | `send_estimate()` logs decision | Successful send | `log_decision()` called with `agent_name="agent_08_sender"`, `decision="estimate_sent"` | ✅ |
| UT-06-05 | Random delay applied — within `[360, 780]` seconds | Any send | `time.sleep()` called with value in range `[360, 780]` (6–13 min) | ✅ |
| UT-06-06 | Missing order → `AgentError` | `get_reviewed_order()` returns `None` | `AgentError` raised — no FTF API calls | ✅ |
| UT-06-07 | Wrong status → `AgentError` | Order with `status="written"` (not `"reviewed"`) | `AgentError` raised — sender only acts on `reviewed` orders | ✅ |
| UT-06-08 | Zero amount → `AgentError` | Order with `amount == 0` | `AgentError` raised — $0 invoice NEVER created | ✅ |
| UT-06-09 | Outside 8AM–6PM ET → returns None, no invoice created | Current time `= 07:59 ET` or `>= 18:00 ET` | Returns `None`; no FTF API calls made | ✅ |
| UT-06-10 | Transient failure → retries, succeeds on 2nd attempt | 1st `send_invoice()` raises network error; 2nd succeeds | Status ends as `"sent"`; 2 attempts logged | ✅ |
| UT-06-11 | All `MAX_SENDER_RETRIES` fail → status=`"error"`, `AgentError` | All retry attempts fail | `processed_orders.status = "error"`; `AgentError` raised | ✅ |
| UT-06-12 | `run()` picks reviewed order from DB | `get_reviewed_order()` returns valid order | `send_estimate()` called with that order | ✅ |
| UT-06-13 | Reporter POSTs to Teams webhook | `get_daily_summary()` returns stats | `httpx.post()` called with `TEAMS_WEBHOOK_URL` | ✅ |
| UT-06-14 | Reporter contains `sent_today` count | 3 orders sent today | Teams payload includes `"sent_today": 3` or equivalent | ✅ |
| UT-06-15 | Reporter contains `flagged` count | 2 orders flagged today | Teams payload includes `"flagged": 2` | ✅ |
| UT-06-16 | Reporter returns `True` on success | Successful Teams POST | `report()` returns `True` | ✅ |
| UT-06-17 | Reporter webhook failure → `AgentError` | Teams webhook returns 500 | `AgentError` raised | ✅ |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-06-01 | Full estimate loop — estimate delivered within 60 min | Submit test order on staging; run full pipeline | Estimate arrives in test inbox within 60 min; FTF order shows `sent` status | ✅ |
| IT-06-02 | Send window enforced on staging | Schedule run outside 8AM–6PM ET | No estimates sent; decision log shows `outside_send_window` | ✅ |
| IT-06-03 | Daily digest delivered to Teams on staging | Run `agent_09_reporter.py` at end of day | Teams channel receives digest with all 5 stats (sent, flagged, errors, pending, total) | ✅ |
| IT-06-04 | Ryan confirms estimate in inbox — MILESTONE | Generate staging estimate for Ryan's test email | Ryan opens estimate, confirms professional appearance and clause visible | ✅ |
| IT-06-05 | Retry behavior on transient FTF API error | Simulate 1 transient failure on staging | Retry succeeds; no duplicate invoice created | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-06-01 | `invoice_id` returned as `"invoice_id"` key in FTF response | Standard key lookup succeeds | ✅ |
| EC-06-02 | `invoice_id` returned as `"id"` key (alternate FTF format) | `.get("invoice_id") or .get("id", "")` fallback used | ✅ |
| EC-06-03 | `get_daily_summary()` returns zero for all stats | Reporter handles all-zero stats — no division by zero, no empty payload | ✅ |
| EC-06-04 | Two orders both reviewed at same time — no double-send | `get_reviewed_order()` returns one at a time | Only 1 invoice created per run; second order picked up on next cycle | ✅ |
| EC-06-05 | Reporter called with no Teams webhook set | `AgentError` raised — no silent failure | ✅ |
| EC-06-06 | `time.sleep()` patchable in tests | Test mocks `time.sleep` directly | `patch("agents.agent_08_sender.time.sleep")` works | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 6)

- [ ] UT-06-01 through UT-06-17 all pass
- [ ] Random delay always in `[360, 780]` second range (6–13 min)
- [ ] 8AM–6PM ET send window enforced — no estimates outside window
- [ ] Retry logic: succeed on retry counts as `"sent"`; all retries exhausted → `status="error"`
- [ ] $0 invoice never created — `AgentError` raised
- [ ] Daily Teams digest contains at minimum: `sent_today`, `flagged`, error count
- [ ] `agent_08_sender.py` and `agent_09_reporter.py` are separate files (one agent, one job)
- [ ] **MILESTONE:** Ryan opens test estimate, confirms professional and correct (I-043 clause visible)
- [ ] Prateek (CTO) sign-off on all 16 tests

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 6.
- Reporter is fully deterministic for this sprint — no LLM; template-based stats digest.
- `reporter.txt` prompt stub available for future LLM enrichment.
- Ryan must sign off on estimate format before Sprint 10 go-live — IT-06-04 is the MILESTONE gate.
- Sprint 6 completed 2026-05-26 — 16 unit tests all passing; full suite 141/141.
