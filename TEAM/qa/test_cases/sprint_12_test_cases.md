# Sprint 12 — Test Cases: Full Production (All 3 Loops Live)

> Written by Senior QA before dev starts. All cases must pass before Sprint 12 is marked ✅ Complete.
> Reference: `sprints/sprint_12_full_production.md`

---

## Unit Tests (Production Configuration Checks)

| ID | Scenario | Input | Expected Output | Pass? |
|----|----------|-------|-----------------|-------|
| UT-12-01 | AR loop `ar_followup.yml` points to production FTF Books URL | Workflow file inspection | `FTF_BOOKS_BASE_URL` secret is production URL, not staging | 🔲 |
| UT-12-02 | Statement loop `monthly_statements.yml` points to production SMTP | Workflow file inspection | `SMTP_HOST`, `SMTP_USER` secrets are production credentials | 🔲 |
| UT-12-03 | All 3 GitHub Actions workflows enabled — not paused | GitHub Actions → All Workflows | `estimate_generation.yml`, `ar_followup.yml`, `monthly_statements.yml` all show `Active` | 🔲 |
| UT-12-04 | `nightly_memory.yml` running on production schedule | GitHub Actions schedule check | Workflow fires at 04:00 UTC nightly; no missed runs | 🔲 |
| UT-12-05 | `order_listener.yml` restarts every 6 hours in production | GitHub Actions schedule check | Listener workflow restarts on 6-hour cycle | 🔲 |
| UT-12-06 | UptimeRobot monitor configured for all 3 workflows | UptimeRobot dashboard | 3 monitors active; alert emails configured for Prateek | 🔲 |
| UT-12-07 | Daily Teams digest received by all stakeholders | Run `agent_09_reporter.py` on production | Digest received by Ryan, Robert/Mark, Jessica, Wyatt at end of business day | 🔲 |
| UT-12-08 | AR loop: Day 60 alert fires in production | Real invoice crosses 60-day threshold | Teams alert delivered to Jessica within 24h of threshold crossing | 🔲 |
| UT-12-09 | AR loop: Day 90 alert fires to all 5 stakeholders in production | Real invoice crosses 90-day threshold | Teams alert delivered to all 5 stakeholders | 🔲 |
| UT-12-10 | Statement loop: statement delivered on 1st of month in production | Calendar date = 1st of month | Excel + PDF statement emailed to B2B billing contacts; Teams notification sent | 🔲 |
| UT-12-11 | Refund requests NEVER handled by AI in production | Real refund request arrives | Routed to Jessica ONLY — no AI action; `status="refund_pending_jessica"` | 🔲 |
| UT-12-12 | 30-day monitoring: zero critical pipeline failures | 30-day production window | No `status="error"` in `processed_orders` persisting >24h; no missed AR alerts | 🔲 |

---

## Integration Tests (Full Production — Sprint 12)

| ID | Scenario | How to Run | Expected Result | Pass? |
|----|----------|-----------|-----------------|-------|
| IT-12-01 | Estimate loop running autonomously in production | Monitor `estimate_generation.yml` for 30 days | Estimates delivered 24/7; no manual intervention required | 🔲 |
| IT-12-02 | AR loop running autonomously in production | Monitor `ar_followup.yml` for 30 days | Escalations fire at correct thresholds; Jessica confirms replacemenent of manual process | 🔲 |
| IT-12-03 | Statement loop delivers first production monthly statement | Wait for 1st of next calendar month | B2B clients receive correct Excel + PDF statements; Wyatt confirms format | 🔲 |
| IT-12-04 | Daily digest received every business day for 30 days | Check Teams channel daily | No missed digests; all 5 stats present each day | 🔲 |
| IT-12-05 | Phase 2 roadmap document delivered | After 30-day monitoring window | `docs/phase_2_roadmap.md` published — POF + NGE expansion scope defined | 🔲 |

---

## Edge Cases

| ID | Scenario | Expected Behavior | Pass? |
|----|----------|-------------------|-------|
| EC-12-01 | Production estimate for NEVER_AUTO_QUOTE service — no auto-send | Real `Lot Split` or `Topography Survey` order arrives | Flagged and halted; Robert/Mark approve manually before sending | 🔲 |
| EC-12-02 | Multiple B2B clients receive statements on same 1st-of-month run | 5 B2B clients active | 5 separate Excel+PDF statements generated and sent; no client receives another's statement | 🔲 |
| EC-12-03 | UptimeRobot fires alert — workflow not running | A GitHub Actions workflow misses a scheduled run | UptimeRobot alert sent to Prateek within 15 min | 🔲 |
| EC-12-04 | Production order volume spikes (10x normal) | High-volume day with many new orders | All orders processed in order; no timeouts; queue depth visible in daily digest | 🔲 |
| EC-12-05 | AR: client pays after 60d alert but before 90d | Payment received between Day 60 and Day 90 | Day 90 alert NOT fired for paid invoice; `escalation_level` not advanced | 🔲 |
| EC-12-06 | Monthly statement for client with zero B2B orders | New B2B client added mid-month with no orders | No empty statement generated or emailed | 🔲 |

---

## Acceptance Criteria (All must be green to close Sprint 12 — Phase 1 Complete)

- [ ] All 3 loops (Estimate, AR, Statement) running autonomously in production
- [ ] Estimate delivered within 60 min of order arrival (24/7)
- [ ] AR escalations firing at correct thresholds — Day 60 → Jessica; Day 90 → all 5
- [ ] Monthly statement delivered on 1st of calendar month
- [ ] Daily Teams digest received by all stakeholders every business day
- [ ] UptimeRobot monitors configured and actively alerting
- [ ] 30-day monitoring window complete — zero critical failures
- [ ] Refund requests confirmed: 100% routed to Jessica — zero AI handling
- [ ] Jessica confirms AR loop replaces manual process
- [ ] Wyatt confirms monthly statement delivery and format
- [ ] Robert/Mark confirm ongoing estimate quality (ongoing spot checks)
- [ ] Ryan issues final Phase 1 sign-off after 30-day monitoring
- [ ] Phase 2 roadmap (POF + NGE expansion) documented and ready

---

## Notes

- This sprint has no new agent code — all 17 agents are built. Work is deployment, configuration, and monitoring.
- All test cases are 🔲 (not yet run) — Sprint 12 has not started as of 2026-05-28.
- Prerequisite: Sprint 11 must clear with no critical failures and Ryan GO.
- Phase 1 definition of done: all 3 loops running 24/7 for 30 days with Ryan sign-off.
- Phase 2 scope: POF (Poff's Power Solutions) + NGE (NexGen Enterprises) expansion.
