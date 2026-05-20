# Sprint 1 — CRM Monitor

## What This Sprint Builds

Agent 2: CRM Monitor — polls the FTF API every 60 minutes, retrieves new orders, and pushes them to the processing queue.

## Agents Built
- `agents/agent_02_monitor.py` — FTF CRM poller

## How to Run
```bash
python code/sprint_01_monitor/agents/agent_02_monitor.py
```

## How to Run Tests
```bash
pytest code/sprint_01_monitor/tests/ -v
```

## Dependencies on Shared
- `code/shared/core/ftf_client.py` — FTF API calls
- `code/shared/core/db.py` — order persistence
- `code/shared/core/logger.py` — logging
- `code/shared/config/settings.py` — poll interval, max orders

## Sprint Status
- Sprint file: `sprints/sprint_01_monitor.md`
- QA test cases: `qa_team/test_cases/sprint_01_test_cases.md`
