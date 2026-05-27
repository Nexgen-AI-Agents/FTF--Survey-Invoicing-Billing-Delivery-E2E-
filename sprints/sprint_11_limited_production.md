# Sprint 11 — Limited Production Launch ⭐

## Overview

| Field | Value |
|-------|-------|
| Goal | Estimate loop goes live on real FTF. Robert/Mark monitor first 5 estimates. 1-week observation before expanding. |
| Status | 🔄 In Progress — started 2026-05-27 |
| Dates | 2026-05-27 → TBD (1-week observation window) |
| Reads From | [sprint_10_staging_test.md](sprint_10_staging_test.md) — GO from Ryan ✅ |
| Outputs | First 5 real estimates sent to real customers, Robert/Mark sign-off, GO/NO-GO for Sprint 12 |

---

## Tasks

- [x] Blocker cleared — Sprint 10 complete, Ryan issued GO/NO-GO: GO
- [x] `scripts/monitor_first5_estimates.py` — Robert/Mark review tool built
- [x] `estimate_generation.yml` — `FTF_API_BASE_URL` secret added so production URL swap requires no code change
- [ ] Set `FTF_API_BASE_URL` GitHub Actions secret to production FTF URL
- [ ] Confirm `FTF_API_KEY` secret is production key (not staging)
- [ ] Trigger first production estimate loop run (workflow_dispatch or wait for hourly cron)
- [ ] Robert/Mark monitor first 5 real estimates — run `python scripts/monitor_first5_estimates.py --teams`
- [ ] 1-week observation period — flag any edge cases
- [ ] AR loop + Statement loop remain on staging during this sprint

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| First real estimate delivered to real customer | 🔲 | Awaiting production credential swap |
| Robert/Mark: estimate correct and professional | 🔲 | |
| 5/5 estimates pass Robert/Mark review | 🔲 | |
| No critical failures in 1-week period | 🔲 | |
| Ryan GO/NO-GO for full production | 🔲 | |

---

## Milestone Sign-Off

**Robert/Mark:** review first 5 estimates, confirm correct → report to Ryan.
**Ryan:** GO/NO-GO for Sprint 12 full production.

---

## Production Credential Swap Instructions

To go live, set these GitHub Actions repository secrets:

| Secret | Value |
|--------|-------|
| `FTF_API_BASE_URL` | `https://app.fieldtofinish.jobs/ftf-ai-api/v1` (production) |
| `FTF_API_KEY` | Production API key from FTF admin panel |
| `FTF_BOOKS_BASE_URL` | `https://app.fieldtofinish.jobs` (production) |
| `FTF_BOOKS_USER` | Production FTF Books login email |
| `FTF_BOOKS_PASSWORD` | Production FTF Books login password |

_All other secrets (DB, Anthropic, Teams) remain unchanged._

After setting secrets:
1. Go to GitHub Actions → "Estimate Generation Loop" → Run workflow (workflow_dispatch)
2. Watch the run logs for the first estimate
3. Run `python scripts/monitor_first5_estimates.py` to verify and optionally notify Robert/Mark

---

## Blockers

_None — blocker cleared (Sprint 10 GO from Ryan)._

---

## Decisions Made

- AR Loop and Statement Loop remain on staging during Sprint 11 to limit blast radius
- Robert/Mark review all 5 estimates before Sprint 12 gate — not just a spot check
- `monitor_first5_estimates.py --teams` sends a Teams card to reviewers with order details + FTF links

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | Monitor first 5 estimates for errors, confirm system health | Yes |
| Operations SME | Robert / Mark | Read every one of the first 5 real estimates sent to real customers — confirm accuracy, tone, and professionalism. Report issues to Prateek within 24 hours. | Yes — MILESTONE |
| Decision Maker | Ryan | Receive Robert/Mark sign-off; issue GO/NO-GO for Sprint 12 | Yes — MILESTONE SIGN-OFF |
| AR Lead | Jessica | Not involved — AR loop stays on staging this sprint | No |
| Oversight | Wyatt | Not involved — Statement loop stays on staging this sprint | No |

---

## Completion Brief

- **Built:** `scripts/monitor_first5_estimates.py` (console report + Teams card), `estimate_generation.yml` updated with `FTF_API_BASE_URL` secret support
- **Tests:** 239/239 passing (no new agent code — tooling only)
- **Changed from plan:** Production credential swap documented as secret configuration only — no code changes required
- **Carry forward for Sprint 12:** Full production for all 3 loops (estimate + AR + statements)
