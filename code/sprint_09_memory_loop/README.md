# Sprint 9 — Memory Loop (Agent 1)

## What This Sprint Builds

Agent 1: Orchestrator / Memory Loop — the top-level controller that schedules and coordinates all agent loops (estimate, AR, monthly statements). Tracks loop state, handles failures, and restarts loops as needed.

## Agents Built
- `agents/agent_01_orchestrator.py`

## How to Run
```bash
python code/sprint_09_memory_loop/agents/agent_01_orchestrator.py
```

## How to Run Tests
```bash
pytest code/sprint_09_memory_loop/tests/ -v
```

## Dependencies
- All sprint 0–8 agents (orchestrates them)
- `code/shared/core/db.py` — loop state persistence
- `code/shared/core/logger.py`

## Sprint Status
- Sprint file: `sprints/sprint_09_memory_loop.md`
- QA test cases: `qa_team/test_cases/sprint_09_test_cases.md`
