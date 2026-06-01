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

## Sprint 12 — Go-Live Deployment Checklist

Sprint 12 is not a development sprint. It is the final production go-live. Complete these steps once Sprint 11 staging tests pass.

### GitHub Secrets — confirm all set in production repo
- [ ] `FTF_API_KEY` — production key
- [ ] `FTF_API_BASE_URL` — production URL (not stage)
- [ ] `ANTHROPIC_API_KEY`
- [ ] `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — production DB
- [ ] `TEAMS_TENANT_ID` — `dcf3aeca-e559-407d-8564-0fea6eb730ca`
- [ ] `TEAMS_APP_ID` + `TEAMS_CLIENT_SECRET` — Azure AD app credentials
- [ ] `TEAMS_TEAM_ID` — `a512e2f6-2a17-4ec1-a0e3-7d2c44d689c7`
- [ ] `TEAMS_CHANNEL_ID` — `19:50IGnbm0MQft2C4eUkl8RXLk6wa2IRpEEE-ySnUeaV81@thread.tacv2`
- [ ] `TEAMS_INCOMING_WEBHOOK_URL` — Logic App relay URL
- [ ] `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD` — nesa@nexgenlogix.com
- [ ] `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- [ ] `FTF_ORDER_URL` — production order URL

### GitHub Secrets — delete these (no longer used)
- [ ] `TEAMS_CHAT_ID` — old group chat removed
- [ ] `TEAMS_WEBHOOK_URL` — legacy O365 connector
- [ ] `TEAMS_APPROVAL_WEBHOOK_URL` — legacy webhook receiver
- [ ] `TEAMS_OUTGOING_WEBHOOK_SECRET` — legacy webhook receiver

### Azure AD App — confirm permissions granted
- [ ] `ChannelMessage.Send` (application permission)
- [ ] `ChannelMessage.Read.All` (application permission)
- [ ] Admin consent granted for both

### Enable GitHub Actions Workflows
- [ ] `invoice_pipeline.yml` — enable (every 15 min + workflow_dispatch)
- [ ] `estimate_generation.yml` — enable
- [ ] `ar_followup.yml` — enable
- [ ] `monthly_statements.yml` — enable
- [ ] `nightly_memory.yml` — enable
- [ ] `poll_approval_monitor.yml` — enable
- [ ] `approval_reminder.yml` — enable

### Power Automate — Real-Time Approval Trigger
Set up a Power Automate flow for instant Teams reply processing:
1. Trigger: "When a new channel message is added" → FTF-Approvals channel
2. Condition: message body contains "APPROVE" OR "REJECT" OR "HOLD"
3. Action: HTTP POST to GitHub API
   - URL: `https://api.github.com/repos/{owner}/{repo}/actions/workflows/invoice_pipeline.yml/dispatches`
   - Method: POST
   - Headers: `Authorization: Bearer {GITHUB_PAT}`, `Accept: application/vnd.github.v3+json`
   - Body: `{"ref": "main"}`
4. This triggers the pipeline within ~1–2 min of the Teams reply (vs. 15 min cron)

### Final Checks
- [ ] Trigger `invoice_pipeline.yml` manually → confirm it completes without errors
- [ ] Verify Teams channel receives test message
- [ ] Confirm DB migration 002 applied successfully
- [ ] Monitor for 1 full business day before declaring stable

---

## Environment Variables Required

See `.env.example` (created in Sprint 0) for the full list.
Never commit `.env` — it is gitignored.
