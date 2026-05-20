# Code Standards — FTF Agentic AI OS

## Language & Runtime
- Python 3.11+. No other languages in agent code.
- All dependencies declared in `requirements.txt`. No undeclared imports.

---

## File Structure Rules

| Rule | Detail |
|------|--------|
| One agent = one file | Never combine two agents in one `.py` file |
| No raw API calls in agents | All FTF API, DB, and LLM calls go through `code/shared/core/` |
| No inline prompts | All prompts live in `code/shared/config/prompts/` as `.txt` files |
| No hardcoded model names | All model IDs in `code/shared/config/models.py` |
| No hardcoded prices | Prices fetched via API at runtime |
| No hardcoded business rules | Flag triggers in `code/shared/config/flag_triggers.py` |
| No hardcoded credentials | All secrets via environment variables (`.env`) |

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Files | `snake_case.py` | `agent_02_monitor.py` |
| Agents | `agent_NN_name.py` | `agent_05_pricing.py` |
| Classes | `PascalCase` | `OrderClassifier` |
| Functions & variables | `snake_case` | `fetch_orders()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Test files | `test_agent_NN_name.py` | `test_agent_02_monitor.py` |

---

## Imports

```python
# 1. Standard library
import os
import json

# 2. Third-party
import anthropic
import psycopg2

# 3. Internal (core/, config/)
from core.ftf_client import fetch_orders
from config.models import CLAUDE_SONNET
```

- No wildcard imports (`from x import *`)
- Alphabetical within each group

---

## Comments

Default: **no comments**. Only add a comment when the WHY is non-obvious:
- A hidden constraint or external requirement
- A workaround for a specific third-party bug
- A subtle invariant that would surprise a reader

Never explain WHAT the code does — well-named identifiers do that.
No multi-line docstrings except for functions that are part of a public API.

---

## Error Handling

- Validate at system boundaries only: API responses, DB query results, environment variable loading.
- Do not catch exceptions you cannot handle — let them propagate.
- Log all exceptions via `core/logger.py` before re-raising.
- Never swallow exceptions silently (`except: pass` is banned).

---

## Security

| Rule | Why |
|------|-----|
| No hardcoded credentials | Credential leakage |
| Parameterized queries only | SQL injection prevention |
| No `eval()` or `exec()` | Code injection prevention |
| No `shell=True` in subprocess | Shell injection prevention |
| `.env` always gitignored | Credential leak prevention |

---

## Testing

- Every agent file has a corresponding test file in `tests/`.
- Minimum coverage: one test per public function + one happy-path integration test.
- Tests must pass before code goes to Senior Dev review.
- Mock all external calls (FTF API, Claude API, DB) in unit tests.
- Integration tests (using staging credentials) run only in Sprint 10+.

---

## Git Commit Standard

```
[Sprint N] Short imperative description

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Example: `[Sprint 0] Add PostgreSQL schema with indexes for orders and payments`
