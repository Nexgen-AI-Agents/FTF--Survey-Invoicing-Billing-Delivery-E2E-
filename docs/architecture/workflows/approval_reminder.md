# Workflow: Daily Approval Reminder

**File:** `.github/workflows/approval_reminder.yml`
**Version:** 1.1.0
**Status:** Active (fixed — was crashing with psycopg2)
**Last Updated:** 2026-06-02

---

## Version History

| Version | Change |
|---------|--------|
| 1.0.0 | Initial — used `DATABASE_URL` (PostgreSQL) to query pending approvals; crashed on ubuntu-latest after PostgreSQL removal |
| 1.1.0 | Removed `DATABASE_URL` orphan env var; pending approval query now reads from Excel state store via `excel_db.py` |

---

## Trigger

```yaml
on:
  schedule:
    - cron: "0 14 * * 1-5"   # 2:00 PM UTC = 9:00 AM ET, Monday–Friday only
  workflow_dispatch:
```

Fires once per weekday at 9 AM Eastern Time. Weekend runs are suppressed (`1-5` day-of-week restriction).

---

## Purpose

Queries the Excel state store for all orders currently in `invoice_draft_posted` status (i.e., waiting for a Teams approval reply). Posts a summary card to the Teams channel reminding the reviewer of each pending invoice, including a direct link to the FTF order. Prevents invoices from stalling silently if an approval card was missed or buried.

---

## Steps (In Order)

| Step | Action |
|------|--------|
| 1 | `actions/checkout@v4` |
| 2 | `actions/setup-python@v5` — Python 3.11 |
| 3 | `pip install -r requirements.txt` |
| 4 | `python scripts/send_daily_approval_reminder.py` — compose and post reminder card |
| 5 | On failure: `python scripts/notify_workflow_failure.py` — posts a failure card to Teams |

---

## Entry Point

```
scripts/send_daily_approval_reminder.py
```

Reads all rows from Excel state store with `status = invoice_draft_posted`. Formats a Teams adaptive card listing each order with its `teams_message_id` (link context) and `FTF_ORDER_URL` deep link. Posts via `TEAMS_INCOMING_WEBHOOK_URL`.

If no orders are pending, the script exits cleanly without posting (no noise).

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `TEAMS_TENANT_ID` | Azure AD tenant ID |
| `TEAMS_APP_ID` | Azure AD app (client) ID |
| `TEAMS_CLIENT_SECRET` | Azure AD app secret |
| `TEAMS_TEAM_ID` | Target Teams team ID |
| `TEAMS_CHANNEL_ID` | Target Teams channel ID |
| `TEAMS_INCOMING_WEBHOOK_URL` | Webhook for posting the reminder card |
| `NOTIFICATION_FROM_EMAIL` | From address for failure notification emails |
| `NOTIFICATION_TO_EMAILS` | Recipient list for failure notification emails |
| `FTF_ORDER_URL` | Base URL for order deep links in the reminder card |

Note: `DATABASE_URL` is NOT present — removed in v1.1.0. Excel state store requires no connection string.

---

## Known Issues Fixed

- **v1.0.0 crash:** `DATABASE_URL` was injected but psycopg2 was not available on the runner. Script imported `db.py` which attempted `import psycopg2` and crashed before any Teams message was sent. Pending approvals accumulated silently.
- **Fix applied in v1.1.0:** Removed the env var; rewrote pending order query to use `excel_db.py`.

---

## Behavior When No Orders Are Pending

Script exits with code 0 and no Teams message is sent. This is intentional — a "no pending invoices" card every morning would be noise.

---

## Related

- [Poll Approval Monitor Workflow](poll_approval_monitor.md)
- [Invoice Pipeline Workflow](invoice_pipeline.md)
- [Architecture Index](../README.md)
