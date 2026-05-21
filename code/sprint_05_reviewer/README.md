# Sprint 5 — Estimate Reviewer (Agents 7 + 8)

## What This Sprint Builds

- Agent 7: Estimate Reviewer — AI reviews the estimate for accuracy, completeness, and tone. Returns corrected estimate or escalates after 3 failed loops.
- Agent 8: Estimate Approver — applies final formatting and prepares estimate for FTF Books submission.

## Agents Built
- `agents/agent_07_reviewer.py`
- `agents/agent_08_approver.py`

## How to Run
```bash
python code/sprint_05_reviewer/agents/agent_07_reviewer.py
```

## How to Run Tests
```bash
pytest code/sprint_05_reviewer/tests/ -v
```

## Dependencies on Shared
- `code/shared/core/claude_client.py`
- `code/shared/config/prompts/estimate_reviewer.txt`
- `code/shared/core/db.py` — loop counter persistence (max 3 retries)

## Sprint Status
- Sprint file: `sprints/sprint_05_reviewer.md`
- QA test cases: `TEAM/qa/test_cases/sprint_05_test_cases.md`
