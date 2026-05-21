# Sprint 3 — Human Gate (Agent 4)

## What This Sprint Builds

Agent 4: Human Review Gate — evaluates all 9 flag triggers, routes flagged orders to human review via MS Teams alert, routes clean orders to the estimate writer.

## Agents Built
- `agents/agent_04_human_gate.py`

## How to Run
```bash
python code/sprint_03_human_gate/agents/agent_04_human_gate.py
```

## How to Run Tests
```bash
pytest code/sprint_03_human_gate/tests/ -v
```

## Dependencies on Shared
- `code/shared/config/flag_triggers.py` — all 9 flag conditions
- `code/shared/core/db.py` — flag status persistence
- `code/shared/core/logger.py`

## Key Business Rules
- ALTA Table A Survey → always flag
- Other Services → always flag
- Out-of-state property → always flag
- Reviewer fails 3 loops → flag
- FEMA API unavailable → flag (cannot determine flood zone)

## Sprint Status
- Sprint file: `sprints/sprint_03_human_gate.md`
- QA test cases: `TEAM/qa/test_cases/sprint_03_test_cases.md`
