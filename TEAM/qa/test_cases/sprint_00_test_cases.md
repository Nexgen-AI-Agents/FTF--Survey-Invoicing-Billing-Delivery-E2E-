# Sprint 0 — Test Cases

**Sprint:** 0 — Foundation & Connections
**Author:** QA Manager
**Status:** Ready for execution

---

## Acceptance Criteria (from sprint_00_foundation.md)

All 7 checks below must be green before Sprint 0 is marked ✅ Complete.

---

## TC-00-01 — FTF API Health Check

| Field | Value |
|-------|-------|
| **What** | `GET /health` returns HTTP 200 |
| **How** | Run `python scripts/test_connections.py` — check line "FTF /health → 200" |
| **Pass** | PASS logged, no exception |
| **Fail** | Any non-200 response, connection refused, or timeout |
| **Blocks** | Entire estimate pipeline — no orders can be fetched |

---

## TC-00-02 — FTF Orders Endpoint

| Field | Value |
|-------|-------|
| **What** | `GET /orders?limit=1` returns a non-empty list |
| **How** | Run `python scripts/test_connections.py` — check "FTF /orders?limit=1 → data" |
| **Pass** | List with ≥1 order dict returned |
| **Fail** | Empty list, parse error, or HTTP error |
| **Blocks** | Agent 2 Monitor (Sprint 1) |

---

## TC-00-03 — FTF Pricing Endpoint

| Field | Value |
|-------|-------|
| **What** | `GET /pricing` returns a non-empty response |
| **How** | Run `python scripts/test_connections.py` — check "FTF /pricing → response" |
| **Pass** | Pricing dict/list returned with at least one entry |
| **Fail** | Empty response, parse error, or HTTP error |
| **Manual check** | Verify Boundary Survey price = $350 in the returned data |
| **Blocks** | Agent 5 Pricing Engine (Sprint 2) |

---

## TC-00-04 — FEMA Flood Zone API

| Field | Value |
|-------|-------|
| **What** | FEMA zone check for Lake Park, FL (lat 26.7998, lng -80.0642) returns a zone code |
| **How** | Run `python scripts/test_connections.py` — check "FEMA FL lat/lng → zone code" |
| **Pass** | Non-empty zone code returned (e.g. "AE", "X") |
| **Fail** | `FEMAUnavailableError` raised, empty string, or timeout |
| **Blocks** | Agent 3 Classifier flood zone logic (Sprint 2) |

---

## TC-00-05 — Anthropic Claude API

| Field | Value |
|-------|-------|
| **What** | Claude Haiku `messages.create` call returns a text response |
| **How** | Run `python scripts/test_connections.py` — check "Claude Haiku → response received" |
| **Pass** | Non-empty string returned |
| **Fail** | `LLMUnavailableError`, auth error, or empty response |
| **Blocks** | All AI-powered agents (Sprints 2–9) |

---

## TC-00-06 — PostgreSQL DB Schema

| Field | Value |
|-------|-------|
| **What** | `db/schema.sql` runs on a fresh PostgreSQL database without errors |
| **How 1** | `psql -U $DB_USER -d $DB_NAME -f db/schema.sql` — confirm no error output |
| **How 2** | Run `python scripts/test_connections.py` — check "DB processed_orders → accessible" |
| **Pass** | All 5 tables created, `get_pending_order()` returns None (empty table) without exception |
| **Fail** | Any SQL error, missing table, or psycopg2 exception |
| **Verify tables** | `\dt` in psql — expect: `processed_orders`, `ar_reminders`, `monthly_statements`, `agent_decision_log`, `excluded_ar_clients` |
| **Blocks** | All DB-backed agents |

---

## TC-00-07 — GitHub Actions YAML Validity

| Field | Value |
|-------|-------|
| **What** | All 3 `.github/workflows/` YAML files parse without errors |
| **How** | Run `python scripts/test_connections.py` — check "GitHub Actions YAML → valid" |
| **Pass** | All 3 files load via `yaml.safe_load()` without exception |
| **Fail** | YAML parse error, missing file, or schema error |
| **Files** | `estimate_generation.yml`, `ar_followup.yml`, `monthly_statements.yml` |
| **Blocks** | CI/CD pipeline activation (Sprint 10) |

---

## Unit Test Suite

Run: `pytest code/sprint_00_foundation/tests/ -v`

| Test File | Coverage |
|-----------|---------|
| `test_exceptions.py` | All 6 exception classes, inheritance, message preservation |
| `test_logger.py` | Logger creation, PII masking (single + multiple emails), handler count |
| `test_db.py` | get_pending_order (None + dict), save_order_state (update + upsert + invalid column), log_decision |
| `test_state.py` | All 4 state transitions with correct field values |
| `test_ftf_client.py` | health_check (success + failure), get_orders, get_pricing, create_invoice, send_invoice, mark_estimate_sent |
| `test_fema_client.py` | Zone found, no features → "X", timeout → FEMAUnavailableError, generic error |
| `test_claude_client.py` | Success, retry on rate limit, LLMUnavailableError after max retries |

---

## QA Sign-Off Checklist

- [ ] All 7 acceptance checks green (`python scripts/test_connections.py` exits 0)
- [ ] All unit tests pass (`pytest code/sprint_00_foundation/tests/ -v`)
- [ ] No open BLOCKER issues in `issues/issue.md`
- [ ] `db/schema.sql` confirmed clean on staging PostgreSQL
- [ ] `requirements.txt` installs without errors (`pip install -r requirements.txt`)
- [ ] `.env.example` matches all vars used in `config/settings.py`
- [ ] `CHANGELOG.md` Sprint 0 entry written
- [ ] Code on GitHub remote (master branch)
