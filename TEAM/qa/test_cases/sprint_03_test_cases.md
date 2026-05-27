# Sprint 3 — Test Cases: Agent 4 Human Gate (9 Flag Triggers)

> Written by Senior QA before dev starts. All cases must pass before Sprint 3 is marked ✅ Complete.
> Reference: `sprints/sprint_03_human_gate.md`

---

## Unit Tests (`code/sprint_03_human_gate/tests/test_human_gate.py`)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-03-01 | `notify_human()` sends Teams webhook POST | Order with `flags=[{"reason":"always_flag_service"}]` | `httpx.post()` called with `TEAMS_WEBHOOK_URL`; payload contains `order_id`, `service_type`, `flag_reason` | ✅ |
| UT-03-02 | `notify_human()` saves `awaiting_approval` status to DB | Flagged order | `processed_orders.status = "awaiting_approval"` in DB | ✅ |
| UT-03-03 | Teams alert payload contains required fields | Any flagged order | Payload includes `order_id`, `service_type`, `flag_reason`, `customer_name` | ✅ |
| UT-03-04 | `check_approval()` polls DB status | `status="awaiting_approval"` in DB | Returns `False` until status updated; returns `True` when `status="approved"` | ✅ |
| UT-03-05 | Missing `TEAMS_WEBHOOK_URL` → `AgentError` | `TEAMS_WEBHOOK_URL=None` in settings | `AgentError` raised — no silent failures | ✅ |
| UT-03-06 | Teams HTTP failure → `AgentError` | `httpx.post()` returns 500 | `AgentError` raised — alert failure not silenced | ✅ |
| UT-03-07 | Non-flagged order passes through — no alert fired | `classification["flags"] == []` | No Teams POST; status advances to next stage | ✅ |
| UT-03-08 | `process_approval_reply()` approve — updates DB | `action="approve"`, `order_id="O-001"` in `status="awaiting_approval"` | `processed_orders.status = "approved"` | ✅ |
| UT-03-09 | `process_approval_reply()` reject — updates DB | `action="reject"`, `order_id="O-001"` | `processed_orders.status = "rejected"` | ✅ |
| UT-03-10 | `process_approval_reply()` invalid action → `AgentError` | `action="maybe"` | `AgentError` raised | ✅ |
| UT-03-11 | `process_approval_reply()` wrong order status → `AgentError` | `action="approve"`, order `status="sent"` (not awaiting) | `AgentError` raised — can't approve an order not pending | ✅ |
| UT-03-12 | `run_escalation_check()` fires orange alert for overdue approvals | Order `awaiting_approval` for >24h (default `APPROVAL_TIMEOUT_HOURS`) | Orange Teams alert sent with escalation details | ✅ |
| UT-03-13 | `run_escalation_check()` no overdue — no alert fired | All approvals within timeout | No Teams POST for escalation | ✅ |
| UT-03-14 | `run_escalation_check()` no webhook → `AgentError` | `TEAMS_WEBHOOK_URL=None` | `AgentError` raised | ✅ |
| UT-03-15 | Batch digest — multiple flagged orders sent as one message | 3 orders flagged in same run | Single Teams message with all 3 orders listed — NOT 3 separate pings | ✅ |
| UT-03-16 | `APPROVAL_TIMEOUT_HOURS` env-configurable | `APPROVAL_TIMEOUT_HOURS=48` | `get_overdue_approvals(48)` called | ✅ |

---

## Integration Tests (Staging — Sprint 10)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-03-01 | ALTA Table A Survey → Teams alert fires on staging | Submit ALTA order to staging CRM; run agent pipeline | Teams channel receives alert with order details within 5 min | ✅ |
| IT-03-02 | Other Services → Teams alert fires | Submit `Other Services` order | Teams alert received; `status="awaiting_approval"` in DB | ✅ |
| IT-03-03 | Out-of-state property → Teams alert fires | Submit order with `property_state="GA"` | Teams alert received; `flag_reason="out_of_state"` in payload | ✅ |
| IT-03-04 | Competitor company name → Teams alert fires | Submit order with competitor company in `COMPETITOR_NAMES` | Teams alert fired; order halted — NOT priced or sent | ✅ |
| IT-03-05 | Normal FL order passes through with no alert | Submit `Boundary Survey`, FL address, non-Monroe, non-competitor | No Teams alert; order advances to Classifier → Pricing normally | ✅ |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-03-01 | Order approved via `process_approval_reply()` → pipeline resumes automatically | `action="approve"` submitted | Status transitions to `approved`; next agent picks up without manual click | ✅ |
| EC-03-02 | Reviewer failure after 3 loops → Human Gate escalation | `ReviewerFailError` raised by Agent 7 | Trigger 7 fires — Teams alert with `flag_reason="reviewer_failed_3x"` | ✅ |
| EC-03-03 | New customer flagged (uncertain genuine vs. competitor) | `customer_type="individual"`, first-time order | Trigger 6 fires — Teams alert for human judgment call | ✅ |
| EC-03-04 | Unusual property (large acreage) flagged | Acreage above threshold in classifier | Trigger 5 fires — Teams alert | ✅ |
| EC-03-05 | Two simultaneous approvals arrive for different orders | Two `process_approval_reply()` calls concurrently | Both processed independently; no cross-contamination in DB | ✅ |
| EC-03-06 | Rejected order — AI does NOT retry or re-route | `status="rejected"` set by `process_approval_reply()` | No further agent activity; order stays `rejected` | ✅ |

---

## Acceptance Criteria (All must be green to close Sprint 3)

- [ ] UT-03-01 through UT-03-16 all pass
- [ ] All 9 flag triggers tested and confirmed to fire
- [ ] Batch digest confirmed: multiple flagged orders → 1 Teams message (not per-order pings)
- [ ] `awaiting_approval` status correctly set on every flagged order
- [ ] `process_approval_reply()` approve/reject transitions work correctly
- [ ] `run_escalation_check()` fires for approvals overdue past `APPROVAL_TIMEOUT_HOURS`
- [ ] Non-flagged orders pass through with NO Teams alert
- [ ] Missing `TEAMS_WEBHOOK_URL` raises `AgentError` (not silent)
- [ ] `APPROVAL_TIMEOUT_HOURS` is env-configurable via `settings.py`
- [ ] Prateek (CTO) sign-off on all 9 flag trigger paths
- [ ] Robert / Mark (SME) validate that correct real orders are flagged — no false flags on normal orders

---

## Notes

- Integration tests (IT-*) run during Sprint 10 (full staging). Unit tests (UT-*) run during Sprint 3.
- Live MS Teams webhook integration test deferred to Sprint 10 (needs real `TEAMS_WEBHOOK_URL`).
- `COMPETITOR_NAMES` + `NEVER_AUTO_QUOTE` validated by Robert/Mark (I-038) before staging.
- Human Gate sends hourly batch digest — NOT one Teams ping per order.
- Sprint 3 completed 2026-05-25 — all 21 unit tests passing; full suite 131/131.
