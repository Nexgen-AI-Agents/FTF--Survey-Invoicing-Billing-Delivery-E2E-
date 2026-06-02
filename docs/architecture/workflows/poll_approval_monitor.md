# Workflow: Teams Approval Monitor

**File:** `.github/workflows/poll_approval_monitor.yml`
**Version:** 1.1.0
**Status:** Active (fixed — was crashing with psycopg2)
**Last Updated:** 2026-06-02

---

## Version History

| Version | Change |
|---------|--------|
| 1.0.0 | Initial — used `DATABASE_URL` (PostgreSQL) for state reads; crashed on ubuntu-latest runners after PostgreSQL removal |
| 1.1.0 | Removed `DATABASE_URL` orphan env var; approval state now read/written via Excel state store (`excel_db.py`); script updated to not import psycopg2 |

---

## Trigger

```yaml
on:
  schedule:
    - cron: "*/5 * * * *"   # every 5 minutes
  workflow_dispatch:
```

Runs every 5 minutes — same cadence as the main invoice pipeline, so approval state stays nearly real-time.

---

## Purpose

Polls the Microsoft Teams channel for APPROVE, REJECT, or HOLD replies to invoice draft cards posted by A3. When a recognized reply is found from an authorized sender (listed in `APPROVED_SENDERS`), the order status in the Excel state store is updated accordingly, allowing the next invoice pipeline run to advance the order to A5 (finalize) or flag it for human review.

This workflow is decoupled from the main pipeline intentionally: Teams reply latency is unpredictable, and a dedicated poller avoids blocking the main pipeline run.

---

## Steps (In Order)

| Step | Action |
|------|--------|
| 1 | `actions/checkout@v4` |
| 2 | `actions/setup-python@v5` — Python 3.11 |
| 3 | `pip install -r requirements.txt` |
| 4 | `python scripts/poll_teams_approvals.py --since-hours 1` — check last 1 hour of Teams messages |
| 5 | On failure: `python scripts/notify_workflow_failure.py` — posts a failure card to Teams |

---

## Entry Point

```
scripts/poll_teams_approvals.py
```

Accepts `--since-hours` argument (default: 1). Reads Teams channel messages, matches against known pending `teams_message_id` values from the Excel state store, applies decisions.

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `TEAMS_TENANT_ID` | Azure AD tenant ID |
| `TEAMS_APP_ID` | Azure AD app (client) ID |
| `TEAMS_CLIENT_SECRET` | Azure AD app secret |
| `TEAMS_TEAM_ID` | Target Teams team ID |
| `TEAMS_CHANNEL_ID` | Target Teams channel ID |
| `TEAMS_INCOMING_WEBHOOK_URL` | Webhook for posting failure notifications |
| `NOTIFICATION_FROM_EMAIL` | From address for failure notification emails |
| `NOTIFICATION_TO_EMAILS` | Recipient list for failure notification emails |
| `APPROVED_SENDERS` | Comma-separated Teams user display names/emails allowed to approve |
| `FTF_ORDER_URL` | Base URL for order deep links in notifications |
| `FTF_API_BASE_URL` | FTF API base URL (used if poller needs to verify order status) |
| `FTF_API_KEY` | FTF API key |

Note: `DATABASE_URL` is NOT present — this was the v1.0.0 bug. Excel state store requires no connection string.

---

## Known Issues Fixed

- **v1.0.0 crash:** `DATABASE_URL` was injected but psycopg2 was not available on the runner after PostgreSQL removal. Script attempted `import psycopg2` and crashed immediately, silently leaving all approvals unprocessed.
- **Fix applied in v1.1.0:** Removed the env var; rewrote state reads/writes to use `excel_db.py`.

---

## Related

- [Invoice Pipeline Workflow](invoice_pipeline.md)
- [Approval Reminder Workflow](approval_reminder.md)
- [Agent Data Contracts](../AGENT_CONTRACTS.md)
- [Architecture Index](../README.md)
