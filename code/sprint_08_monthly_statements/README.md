# Sprint 8 — Monthly Statements (Agents 15–17)

## What This Sprint Builds

The B2B monthly statement loop (runs 1st of every month):
- Agent 15: Statement Compiler — aggregates B2B orders for the month
- Agent 16: Statement Generator — generates Excel + PDF statement
- Agent 17: Statement Deliverer — sends via MS Teams + email to billing contact

## Agents Built
- `agents/agent_15_statement_compiler.py`
- `agents/agent_16_statement_generator.py`
- `agents/agent_17_statement_deliverer.py`

## How to Run Tests
```bash
pytest code/sprint_08_monthly_statements/tests/ -v
```

## Dependencies
- `code/shared/core/ftf_client.py` — order data
- `code/shared/config/settings.py` — monthly trigger date (1st of month)

## Key Rules
- Trigger: 1st of every calendar month
- Format: Excel + PDF
- Delivery: MS Teams + email to billing contact (master email; fallback to most recent order email)

## Blocked By
- Wyatt's recording session (statement format confirmation)
- Jessica's recording session (billing contact rules)

## Sprint Status
- Sprint file: `sprints/sprint_08_monthly_statements.md`
- QA test cases: `qa_team/test_cases/sprint_08_test_cases.md`
