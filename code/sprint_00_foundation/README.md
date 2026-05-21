# Sprint 0 — Foundation

## What This Sprint Builds

The entire infrastructure layer that all other sprints depend on:
- GitHub repo + full folder structure (already done)
- `db/schema.sql` — PostgreSQL schema for orders, estimates, AR, statements
- `code/shared/core/` — all shared modules: `ftf_client.py`, `claude_client.py`, `fema_client.py`, `db.py`, `logger.py`
- `code/shared/config/` — `settings.py`, `models.py`, `flag_triggers.py`
- `code/shared/models/` — data models (`order.py`, `estimate.py`, etc.)
- `.env.example` — template for environment variables

## Agents Built
None. Sprint 0 is infrastructure only.

## How to Run
```bash
# Install dependencies
pip install -r requirements.txt

# Provision PostgreSQL (requires DB credentials in .env)
psql -U $DB_USER -d $DB_NAME -f code/sprint_00_foundation/db/schema.sql
```

## How to Run Tests
```bash
pytest code/sprint_00_foundation/tests/ -v
```

## Dependencies on Shared
This sprint CREATES `code/shared/`. All other sprints depend on it.

## Sprint Status
- Sprint file: `sprints/sprint_00_foundation.md`
- QA test cases: `TEAM/qa/test_cases/sprint_00_test_cases.md`
