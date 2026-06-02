# Workflow: Invoice Pipeline (Sprint 11)

**File:** `.github/workflows/invoice_pipeline.yml`
**Version:** 1.2.0
**Status:** Active
**Last Updated:** 2026-06-02

---

## Version History

| Version | Change |
|---------|--------|
| 1.0.0 | Initial Sprint 11 pipeline — PostgreSQL state store |
| 1.1.0 | Replaced PostgreSQL with Excel state store; switched to MySQL env vars for order detection |
| 1.2.0 | Added `GOOGLE_MAPS_API_KEY`, `GOOGLE_REVIEW_URL`, `TEAMS_WEBHOOK_URL`; added `NOTIFICATION_FROM_EMAIL`, `NOTIFICATION_TO_EMAILS`; fixed MySQL env var names (`MYSQL_*` not `DB_*`); added `permissions: contents: write` for state commit step |

---

## Trigger

```yaml
on:
  schedule:
    - cron: "*/5 * * * *"   # every 5 minutes
  workflow_dispatch:          # manual trigger from GitHub Actions UI
```

Runs every 5 minutes. GitHub Actions minimum cron interval is 5 minutes. Also triggerable manually.

---

## Purpose

Drives the full end-to-end Sprint 11 invoice pipeline. On each run:

1. A1 queries MySQL (`nexgen_ftf_db`) for new completed orders that need invoicing and writes them to the Excel state store.
2. A2 collects all data needed to price each order (FTF API, IMAP, Google Maps, county lookups).
3. A3 uses Claude to draft invoice line items and post a review card to Teams.
4. A4 polls Teams for APPROVE/REJECT/HOLD replies and updates order status.
5. A5 creates the approved invoice in FTF Books.
6. A6 sends the finalized invoice to the client.
7. The updated Excel state file is committed back to the repo.

---

## Steps (In Order)

| Step | Action |
|------|--------|
| 1 | `actions/checkout@v4` — check out the repo |
| 2 | `actions/setup-python@v5` — Python 3.11 |
| 3 | `pip install -r requirements.txt` — install dependencies |
| 4 | `cd code/sprint_11_invoice_pipeline && python -m agents.agent_a0_orchestrator` — run the pipeline |
| 5 | `git add data/invoice_pipeline_state.xlsx` + commit `"chore: update pipeline state [skip ci]"` — persist state (runs even if pipeline step fails, via `if: always()`) |

The `[skip ci]` tag on the state commit prevents an infinite trigger loop.

---

## Entry Point

```
code/sprint_11_invoice_pipeline/agents/agent_a0_orchestrator.py
```

A0 is the only script called directly. It imports and calls A1–A6 in sequence.

---

## Environment Variables

All injected as GitHub Actions secrets.

| Variable | Purpose |
|----------|---------|
| `FTF_API_KEY` | FTF platform API key |
| `FTF_API_BASE_URL` | Base URL for FTF REST API |
| `ANTHROPIC_API_KEY` | Claude API key (used by A3 for invoice drafting) |
| `MYSQL_HOST` | MySQL server hostname |
| `MYSQL_PORT` | MySQL server port (default 3306) |
| `MYSQL_USER` | MySQL username |
| `MYSQL_PASSWORD` | MySQL password |
| `MYSQL_DB` | MySQL database (`nexgen_ftf_db`) |
| `TEAMS_TENANT_ID` | Azure AD tenant ID |
| `TEAMS_APP_ID` | Azure AD app (client) ID |
| `TEAMS_CLIENT_SECRET` | Azure AD app secret |
| `TEAMS_TEAM_ID` | Target Teams team ID |
| `TEAMS_CHANNEL_ID` | Target Teams channel ID |
| `TEAMS_INCOMING_WEBHOOK_URL` | Webhook URL for posting adaptive cards to Teams |
| `TEAMS_WEBHOOK_URL` | Alternate/legacy Teams webhook |
| `IMAP_HOST` | IMAP server hostname |
| `IMAP_PORT` | IMAP port (default 993) |
| `IMAP_USER` | IMAP username |
| `IMAP_PASSWORD` | IMAP password |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `SMTP_FROM` | From address for outbound emails |
| `FTF_ORDER_URL` | Base URL for order deep links in Teams messages |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key (A2 distance/location lookups) |
| `GOOGLE_REVIEW_URL` | Google review link appended to sent invoices |

---

## Permissions

```yaml
permissions:
  contents: write
```

Required so the workflow can commit the updated `data/invoice_pipeline_state.xlsx` back to the repo.

---

## State File

`data/invoice_pipeline_state.xlsx` — committed to repo after every run (even on failure). Managed by `code/shared/core/excel_db.py`.

---

## Related

- [Agent Data Contracts](../AGENT_CONTRACTS.md)
- [Architecture Index](../README.md)
