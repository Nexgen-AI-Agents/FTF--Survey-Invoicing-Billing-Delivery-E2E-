# Sprint 11 — Limited Production (Milestone)

## What This Sprint Does

Limited production rollout — system runs live for a subset of real orders. Monitor for 2 weeks before full production.

## Scope
- Live FTF API (production credentials)
- Estimate loop active for selected order types only
- AR loop active for selected clients only
- Human oversight at every flag
- Daily monitoring by Prateek

## How to Run Tests
```bash
pytest code/sprint_11_limited_production/tests/ -v
```

## Prerequisites
- Sprint 10 staging milestone signed off
- Production credentials configured in `.env`
- Ryan approval received
- Rollback procedure ready (see `code/RELEASE_RUNBOOK.md`)

## Milestone Requirements
- 2 weeks stable operation with no BLOCKER issues
- Prateek and Ryan sign-off before Sprint 12

## Sprint Status
- Sprint file: `sprints/sprint_11_limited_production.md`
- QA test cases: `TEAM/qa/test_cases/sprint_11_test_cases.md`
