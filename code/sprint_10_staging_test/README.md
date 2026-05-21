# Sprint 10 — Staging Test (Milestone)

## What This Sprint Does

End-to-end integration test of all agents on the staging environment. No new agents are built — this sprint validates the full system works together.

## Test Scope
- Full Estimate Generation loop (Agents 1–9)
- Full AR Follow-Up loop (Agents 10–14)
- Full Monthly Statements loop (Agents 15–17)
- All 9 flag triggers fire correctly
- Staging FTF API responds correctly
- DB writes and reads verified

## How to Run Tests
```bash
pytest code/sprint_10_staging_test/tests/ -v
```

## Prerequisites
- All Sprints 0–9 complete and QA-signed
- Staging credentials configured in `.env`
- DB provisioned on staging

## Milestone Requirements
- All QA Checklist sections pass including Performance (Section 4)
- Prateek sign-off before Sprint 11 begins

## Sprint Status
- Sprint file: `sprints/sprint_10_staging_test.md`
- QA test cases: `TEAM/qa/test_cases/sprint_10_test_cases.md`
