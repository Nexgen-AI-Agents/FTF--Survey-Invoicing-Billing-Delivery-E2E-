# Release Runbook — FTF Agentic AI OS

## Overview

This runbook defines the exact steps to deploy any sprint from development to staging and production.
Run these steps in order. No step may be skipped.

---

## Pre-Release Gate (QA Manager must confirm before any deploy)

- [ ] All items in `TEAM/qa/DEFINITION_OF_DONE.md` checked
- [ ] No BLOCKER or CRITICAL issues open in `issues/issue.md`
- [ ] All tests pass
- [ ] Code on GitHub remote (master branch)

---

## Deploy to Staging (Sprint 10+)

1. Pull latest code: `git pull origin master`
2. Set environment: copy `.env.example` → `.env`, fill in staging credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run DB schema (if schema changed): `psql -U $DB_USER -d $DB_NAME -f db/schema.sql`
5. Run full test suite: `pytest code/sprint_NN/tests/ -v`
6. Start the agent loop: `python code/sprint_NN/agents/agent_01_orchestrator.py`
7. Monitor logs for 10 minutes — check `logs/` for errors
8. Run manual smoke test (see sprint test cases Section 1)
9. Report status to QA Manager

---

## Deploy to Production (Sprint 11+ — Prateek sign-off required)

1. Confirm staging has been stable for ≥48 hours
2. Get explicit approval from Prateek before proceeding
3. Repeat staging steps 1–8 with production credentials
4. Monitor for 30 minutes post-deploy
5. Update `CHANGELOG.md` with prod release entry
6. Notify Prateek and Ryan via MS Teams

---

## Rollback Procedure

If a production issue is found post-deploy:
1. Stop the agent loop immediately
2. Revert to previous commit: `git revert HEAD` (do NOT force-push)
3. Redeploy previous version using steps above
4. Log the incident in `issues/issue.md` as BLOCKER
5. Notify Prateek immediately

---

## Environment Variables Required

See `.env.example` (created in Sprint 0) for the full list.
Never commit `.env` — it is gitignored.
