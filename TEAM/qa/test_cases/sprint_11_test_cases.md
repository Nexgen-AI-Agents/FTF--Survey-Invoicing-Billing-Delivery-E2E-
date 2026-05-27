# Sprint 11 — Test Cases: Limited Production (First 5 Real Estimates)

> Written by Senior QA before dev starts. All cases must pass before Sprint 11 is marked ✅ Complete.
> Reference: `sprints/sprint_11_limited_production.md`

---

## Unit Tests (Production Readiness Checks)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-11-01 | `estimate_generation.yml` reads `FTF_API_BASE_URL` from GitHub Actions secret | Workflow file inspection | `FTF_API_BASE_URL` is sourced from `${{ secrets.FTF_API_BASE_URL }}` — not hardcoded | 🔲 |
| UT-11-02 | Production `FTF_API_KEY` is distinct from staging key | Manual credential check | Production key differs from staging key set in Sprint 0 | 🔲 |
| UT-11-03 | `monitor_first5_estimates.py` outputs clean console report | Run with `--dry-run` against staging | Console shows order_id, customer_type, service, price, status for each of 5 estimates | 🔲 |
| UT-11-04 | `monitor_first5_estimates.py --teams` sends Teams card | Run with `--teams` flag against staging DB | Teams card received with order details + FTF link for each estimate | 🔲 |
| UT-11-05 | Production FTF API reachable — health check | Run API ping against production `FTF_API_BASE_URL` | HTTP 200 returned within 5 seconds | 🔲 |
| UT-11-06 | PII masking active in production logs | Check log output for first production run | Customer emails masked (`j***@example.com`); no raw PII in log lines | 🔲 |
| UT-11-07 | First production run — no `ERROR` level log entries | Run workflow_dispatch trigger | Zero `ERROR` lines in GitHub Actions run log | 🔲 |
| UT-11-08 | First estimate reaches `status="sent"` in DB | First real order processed | `processed_orders` row shows `status="sent"` | 🔲 |
| UT-11-09 | Estimate sends within send window (8AM–6PM ET) | First production run | `send_estimate()` confirms current time within window before sending | 🔲 |
| UT-11-10 | AR loop stays on staging — NOT promoted to production | Check `ar_followup.yml` secrets | Workflow still points to staging `FTF_BOOKS_BASE_URL` | 🔲 |
| UT-11-11 | Statement loop stays on staging — NOT promoted to production | Check `monthly_statements.yml` secrets | Workflow still points to staging DB/SMTP | 🔲 |
| UT-11-12 | Estimate #5 processed — count stops at 5 for observation | 5 production orders | `monitor_first5_estimates.py` reports 5/5 complete; no 6th estimate sent without review | 🔲 |

---

## Integration Tests (Live Production — Sprint 11)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-11-01 | First real estimate delivered to real customer | Set production secrets; trigger `workflow_dispatch`; wait | Real customer receives estimate email from NexGen within 60 min | 🔲 |
| IT-11-02 | Robert/Mark review first estimate — confirm accuracy | Robert/Mark open estimate in FTF + inbox | Robert/Mark confirm: correct service, correct price, correct address, change order clause present | 🔲 |
| IT-11-03 | 5/5 estimates pass Robert/Mark review | After 5th estimate sent | Robert/Mark confirm all 5 are accurate and professional — report to Prateek | 🔲 |
| IT-11-04 | No critical failures during 1-week observation | Monitor GitHub Actions for 1 week | Zero `ERROR` status in `processed_orders`; zero failed invoice creates | 🔲 |
| IT-11-05 | Ryan issues GO/NO-GO for Sprint 12 | After Robert/Mark sign-off | Ryan says GO — Sprint 12 unblocked | 🔲 |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-11-01 | First production order is an ALTA (always-flag) | First order type is ALTA Table A Survey | Flagged and halted at Human Gate — NOT sent to customer | 🔲 |
| EC-11-02 | First production order has special pricing | `special_pricing=True` customer is first order | Override price applied correctly — standard price NOT used | 🔲 |
| EC-11-03 | Production FTF API returns transient 5xx on first attempt | Network blip on first production run | Retry logic fires; estimate succeeds on 2nd attempt; no duplicate invoice | 🔲 |
| EC-11-04 | Real customer has unusual name characters (accents, hyphens) | `customer_name="María López-García"` | Name appears correctly in estimate email — not mangled or escaped | 🔲 |
| EC-11-05 | Reviewer fails 3× on a production order | LLM returns bad draft 3 consecutive times | Human Gate escalation fires; Robert/Mark notified via Teams; no estimate sent to customer | 🔲 |
| EC-11-06 | Production order arrives at 7:55 AM ET (before send window) | Order processed at 07:55 ET | Estimate queued; NOT sent until 08:00 ET | 🔲 |

---

## Acceptance Criteria (All must be green to close Sprint 11)

- [ ] Production `FTF_API_BASE_URL` and `FTF_API_KEY` secrets set in GitHub Actions
- [ ] First real estimate sent to real customer (IT-11-01)
- [ ] Robert/Mark review and approve all 5 estimates
- [ ] 1-week observation period complete with zero critical failures
- [ ] PII masking confirmed active in production logs (I-018)
- [ ] AR loop and Statement loop remain on staging — NOT promoted
- [ ] `monitor_first5_estimates.py` used by Robert/Mark — correct output
- [ ] Ryan issues GO for Sprint 12
- [ ] Prateek monitors system health for full 1-week period

---

## Notes

- This is the first live production sprint — all estimates go to real customers.
- AR loop and Statement loop intentionally stay on staging to limit blast radius.
- `monitor_first5_estimates.py --teams` sends a Teams card to reviewers with order details + FTF links.
- Sprint 11 status: In Progress as of 2026-05-27 — production credential swap pending.
- After credential swap: trigger via GitHub Actions → "Estimate Generation Loop" → Run workflow (workflow_dispatch).
