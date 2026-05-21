# Sprint 4 — Estimate Writer (Agent 6)

## What This Sprint Builds

Agent 6: Estimate Writer — uses Claude to generate professional estimate text from classified + priced order data. Applies change order clause. Outputs structured estimate ready for FTF Books.

## Agents Built
- `agents/agent_06_writer.py`

## How to Run
```bash
python code/sprint_04_writer/agents/agent_06_writer.py
```

## How to Run Tests
```bash
pytest code/sprint_04_writer/tests/ -v
```

## Dependencies on Shared
- `code/shared/core/claude_client.py` — LLM call
- `code/shared/config/prompts/estimate_writer.txt` — prompt template
- `code/shared/config/models.py` — model selection
- `code/shared/config/knowledge_base/change_order_clause.txt` — change order text

## Prerequisites
- Change order clause text must be drafted before this sprint starts

## Sprint Status
- Sprint file: `sprints/sprint_04_writer.md`
- QA test cases: `TEAM/qa/test_cases/sprint_04_test_cases.md`
