# ADR-004 — Shared Core Architecture (code/shared/)

## Date
2026-05-21

## Status
`Accepted`

## Context

The system has 17 agents across 3 loops. All agents need: FTF API access, DB persistence, LLM calls, FEMA queries, logging, and exception handling. Without a shared layer, each agent would re-implement API auth, retry logic, connection management, and PII masking — causing divergence, duplication, and security risk.

## Decision

All external calls (API, DB, LLM) go through `code/shared/core/`. Agent files in `code/sprint_NN/agents/` import from shared and contain only business logic.

Structure:
```
code/shared/
  core/
    ftf_client.py     — FTF CRM + Books + Pricing API
    claude_client.py  — Anthropic Claude LLM
    fema_client.py    — FEMA flood zone lookup
    db.py             — PostgreSQL state + audit trail
    logger.py         — PII-masking logger
    exceptions.py     — Custom exception hierarchy
    state.py          — Order state transition helpers
  config/
    settings.py       — All env vars and tunable constants
    models.py         — Model ID constants
    flag_triggers.py  — Business rule lists (ALWAYS_FLAG, COMPETITOR, NEVER_AUTO_QUOTE)
    knowledge_base/   — service_names.json, change_order_clause.txt
    prompts/          — All LLM prompt .txt files
```

**Hard rule:** No raw `httpx.get()`, `psycopg2.connect()`, `anthropic.Anthropic()`, or `open("prompt.txt")` inside any agent file. All must go through shared core.

## Consequences

### Positive
- Single auth point: FTF API key, DB creds, Anthropic key set once in settings.py
- Testability: mock `_get_cursor()` or `ftf_client.get_orders` once, all agents benefit
- PII safety: email masking in logger applies to all agents automatically
- Retry logic: Claude client 3× retry applies to all LLM-calling agents
- Maintainability: FTF API URL change = 1 file edit, not 17

### Negative / Trade-offs
- sys.path manipulation needed in each sprint's agent files to import shared
- Tight coupling between sprint code and shared layer (acceptable — intentional)

### Neutral
- conftest.py in each sprint's test folder handles path setup for pytest
- Sprint N code imports from `code/shared/` — never from other sprints

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Copy shared utilities into each sprint | Diverges immediately; security patches require 17 edits |
| Python package install | Overkill for a single-repo project |
| Environment injection via __init__ | More complex; harder to test |

## Related
- `code/shared/core/` — all 7 shared core files
- `TEAM/dev/CODE_STANDARDS.md` — "No raw calls" rule
- ADR-001 (PostgreSQL), ADR-003 (Model selection)
