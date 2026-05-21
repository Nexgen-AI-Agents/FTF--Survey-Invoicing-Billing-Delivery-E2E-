# ADR-001 — PostgreSQL as Primary State Store

## Date
2026-05-21

## Status
`Accepted`

## Context

The system runs 17 agents across 3 async loops. Order state must be persisted between runs (each loop fires independently — hourly, daily, monthly). Multiple agents read and write the same order record as it progresses from `pending` → `classified` → `priced` → `written` → `reviewed` → `sent`. The AR loop and monthly statement loop also require date-range queries, filtering by client and status, and an immutable audit trail.

## Decision

Use PostgreSQL (v18 on Windows dev; hosted PostgreSQL in staging/prod) as the sole state store. Schema defined in `db/schema.sql`. All DB access goes through `code/shared/core/db.py`.

## Consequences

### Positive
- ACID compliance: no partial writes when an agent crashes mid-run
- Multi-agent safe: row-level locking prevents duplicate processing
- Complex queries: date range, status filters, JOIN support needed for AR + statements
- Audit trail: `agent_decision_log` is append-only, supports full replay
- Single migration file (`db/schema.sql`) — easy to provision any environment

### Negative / Trade-offs
- Requires PostgreSQL running locally for dev (not zero-setup)
- psycopg2-binary has no async support — synchronous agents only (acceptable for current scope)
- Schema changes require migration management in future sprints

### Neutral
- SQLite was evaluated for local dev simplicity but rejected (no concurrent write safety)
- All tests mock `_get_cursor()` — no test DB needed for unit tests

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| SQLite | No concurrent write safety; no hosted prod equivalent |
| Redis | No complex query support; no audit trail; volatile by default |
| JSON files | Not ACID; no query capability; fails at scale |

## Related
- `db/schema.sql` — full schema (5 tables)
- `code/shared/core/db.py` — all DB operations
- Sprint 0: `sprints/sprint_00_foundation.md`
