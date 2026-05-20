# Sprint 6 — Sender + Daily Reporter (Agent 9)

## What This Sprint Builds

Agent 9: Estimate Sender + Daily Reporter — sends approved estimates via FTF Books API (with 6–13 min random delay), then generates and sends a daily digest report to MS Teams.

## Agents Built
- `agents/agent_09_sender_reporter.py`

## How to Run
```bash
python code/sprint_06_sender_reporter/agents/agent_09_sender_reporter.py
```

## How to Run Tests
```bash
pytest code/sprint_06_sender_reporter/tests/ -v
```

## Dependencies on Shared
- `code/shared/core/ftf_client.py` — FTF Books send API
- `code/shared/config/settings.py` — send delay range (6–13 min)
- `code/shared/core/db.py` — sent estimate log

## Key Rules
- Send delay: randomized 6–13 minutes per estimate (never 0)
- Post-approval send: AI sends automatically — no manual click
- Daily digest: sent to MS Teams + email to relevant stakeholders

## Sprint Status
- Sprint file: `sprints/sprint_06_sender_reporter.md`
- QA test cases: `qa_team/test_cases/sprint_06_test_cases.md`
