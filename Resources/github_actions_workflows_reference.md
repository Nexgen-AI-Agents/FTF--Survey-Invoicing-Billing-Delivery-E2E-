# GitHub Actions Workflows — Sprint 11 Reference

_Captured: 2026-06-03_

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| **Invoice Pipeline** | Every 30 min | Main pipeline — picks up new orders, creates invoices (A1→A7), posts to Teams group chat |
| **Approval Poller** | Every 10 min _(was 2 min)_ | Fast-response loop — checks group chat for approval replies and sends approved invoices (A4→A6) without waiting 30 min |
| **Feedback Learner (A7)** | Every 30 min at :15/:45 _(was 5 min)_ | Scans Teams for corrections, updates learned_rules.json |
| **Teams Approval Monitor** | Event-triggered (after Invoice Pipeline) | **LEGACY — polls old Teams channel. Replaced by Approval Poller. Should be deleted.** |
| **Daily Approval Reminder** | 2pm weekdays | Sends reminders for invoices waiting >24h for approval |
| **Order State Listener** | Every 6 hours | Syncs order statuses from FTF MySQL into the Excel state store |
| **AR Follow-Up Loop** | 7am daily | Sends accounts-receivable follow-up emails to overdue clients |
| **Monthly Statements Loop** | 1st of month, 8am | Generates and emails monthly statements |
| **Nightly Memory Loop** | 4am daily | Consolidates learnings, updates the memory/rules file |

## Notes

- **Teams Approval Monitor** (`poll_approval_monitor.yml`) fires via `workflow_run` event every time Invoice Pipeline completes. It runs `poll_teams_approvals.py` — the old Teams channel script, not group chat. This is dead code. Delete to stop the ghost runs.
- All active notification/approval logic now routes through the **group chat** (`19:2e562f562ff14d298e2ce7d741d8f8d3@thread.v2`) via the Logic App webhook.
- Schedules shown in the original screenshot (Approval Poller: 2 min, Feedback Learner: 5 min) were reduced to save GitHub Actions minutes before the repo was made public.
