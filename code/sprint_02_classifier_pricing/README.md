# Sprint 2 — Classifier + Pricing Engine

## What This Sprint Builds

- Agent 3: Order Classifier — determines customer type (new/existing/competitor), checks FEMA flood zone, auto-adds Elevation Certificate if in flood zone.
- Agent 5: Pricing Engine — looks up service prices via FTF API, calculates total, applies rules.

## Agents Built
- `agents/agent_03_classifier.py`
- `agents/agent_05_pricing.py`

## How to Run
```bash
python code/sprint_02_classifier_pricing/agents/agent_03_classifier.py
python code/sprint_02_classifier_pricing/agents/agent_05_pricing.py
```

## How to Run Tests
```bash
pytest code/sprint_02_classifier_pricing/tests/ -v
```

## Dependencies on Shared
- `code/shared/core/fema_client.py` — flood zone lookup
- `code/shared/core/ftf_client.py` — pricing API
- `code/shared/config/flag_triggers.py` — classification rules
- `code/shared/models/order.py`

## Sprint Status
- Sprint file: `sprints/sprint_02_classifier_pricing.md`
- QA test cases: `qa_team/test_cases/sprint_02_test_cases.md`
