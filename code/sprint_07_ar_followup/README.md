# Sprint 7 — AR Follow-Up (Agents 10–14)

## What This Sprint Builds

The full AR automation loop:
- Agent 10: AR Scanner — scans unpaid invoices daily
- Agent 11: AR Scheduler — determines reminder schedule per invoice age
- Agent 12: AR Writer — writes personalized reminder emails via Claude
- Agent 13: AR Sender — sends reminders via FTF Books
- Agent 14: AR Escalator — escalates accounts past threshold (90 days?) to Jessica

## Agents Built
- `agents/agent_10_ar_scanner.py`
- `agents/agent_11_ar_scheduler.py`
- `agents/agent_12_ar_writer.py`
- `agents/agent_13_ar_sender.py`
- `agents/agent_14_ar_escalator.py`

## How to Run Tests
```bash
pytest code/sprint_07_ar_followup/tests/ -v
```

## Dependencies
- `code/shared/core/ftf_client.py` — invoice data + send API
- `code/shared/core/claude_client.py` — reminder email writing
- `code/shared/config/prompts/ar_reminder.txt`

## Blocked By
- Jessica's recording session (escalation threshold, client exclusion list)

## Sprint Status
- Sprint file: `sprints/sprint_07_ar_followup.md`
- QA test cases: `qa_team/test_cases/sprint_07_test_cases.md`
