# Supporting Workflows (Non-Sprint-11)

These workflows belong to earlier sprints (7, 8, 9). They run independently of the Sprint 11 invoice pipeline. Several carry active warnings about PostgreSQL dependencies that were not migrated during the Excel state store transition.

**Last Updated:** 2026-06-02

---

## ar_followup.yml — AR Follow-Up Loop

**Sprint:** 7
**Status:** Active (PostgreSQL dependency — requires `DATABASE_URL` secret set to a live PostgreSQL instance)

| Field | Value |
|-------|-------|
| Trigger | Daily at 7:00 AM UTC |
| Agents | Agent 10 (AR Scanner), Agent 11 (AR Escalation) |
| Entry points | `code/sprint_07_ar_followup/agents/agent_10_ar_scanner.py`, `agent_11_ar_escalation.py` |
| State store | PostgreSQL via `DATABASE_URL` (legacy — NOT Excel) |
| External | FTF Books API (`FTF_BOOKS_BASE_URL`, `FTF_BOOKS_USER`, `FTF_BOOKS_PASSWORD`) |

**WARNING:** This workflow uses the legacy `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` env var pattern (not `MYSQL_*` and not `DATABASE_URL`). It requires a running PostgreSQL instance. If the PostgreSQL host is down, this workflow will fail silently (no Teams failure notification configured).

**Env vars:** `FTF_API_KEY`, `FTF_BOOKS_BASE_URL`, `FTF_BOOKS_USER`, `FTF_BOOKS_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `TEAMS_WEBHOOK_URL`

---

## monthly_statements.yml — Monthly Statements Loop

**Sprint:** 8
**Status:** Active (PostgreSQL dependency — requires legacy `DB_*` secrets)

| Field | Value |
|-------|-------|
| Trigger | 1st of every month at 8:00 AM UTC |
| Agents | Agent 15 (Statement Generator), Agent 16 (Statement Reviewer), Agent 17 (Statement Sender) |
| Entry points | `code/sprint_08_monthly_statements/agents/agent_15_statement_generator.py`, `agent_16_statement_reviewer.py`, `agent_17_statement_sender.py` |
| State store | PostgreSQL via `DB_*` env vars (legacy) |
| Output | `/tmp/statements/` directory on the runner (ephemeral — not committed) |

**WARNING:** Statement files are written to `/tmp/statements/` which is ephemeral on GitHub Actions runners. If Agent 17 fails after Agent 15 generates files, the statements are lost and the run must be triggered manually. Consider adding a commit step for statement artifacts in a future sprint.

**WARNING:** PostgreSQL dependency. Same risk as `ar_followup.yml`.

**Env vars:** `FTF_API_KEY`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `TEAMS_WEBHOOK_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `STATEMENT_OUTPUT_DIR`

---

## estimate_generation.yml — Estimate Generation Loop

**Sprint:** 9
**Status:** CRITICAL WARNING — `DATABASE_URL` orphan, may fail

| Field | Value |
|-------|-------|
| Trigger | Every hour (`:00`) |
| Entry point | `code/sprint_09_memory_loop/agents/agent_01_orchestrator.py` |
| State store | Expects PostgreSQL via `DATABASE_URL` (orphan after Sprint 11 migration) |

**CRITICAL:** `DATABASE_URL` is injected but the PostgreSQL instance it referenced may no longer be provisioned. If `agent_01_orchestrator.py` imports `db.py` and attempts a connection at startup, the workflow will crash on every hourly run with a connection error. This generates noise in GitHub Actions and may mask real failures.

**Recommended action:** Either provision a PostgreSQL instance and set `DATABASE_URL`, or migrate this agent to use the Excel state store and remove the `DATABASE_URL` dependency.

**Env vars:** `FTF_API_KEY`, `FTF_API_BASE_URL`, `FTF_BOOKS_BASE_URL`, `FTF_BOOKS_USER`, `FTF_BOOKS_PASSWORD`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `TEAMS_WEBHOOK_URL`

---

## nightly_memory.yml — Nightly Memory Loop

**Sprint:** 9
**Status:** WARNING — `DATABASE_URL` orphan

| Field | Value |
|-------|-------|
| Trigger | Daily at 4:00 AM UTC (midnight ET) |
| Entry points | `code/sprint_09_memory_loop/agents/memory/memory_manager.py`, `dream_processor.py` |
| Commits | `docs/memory/` and `docs/reflection.md` back to repo |

**WARNING:** `DATABASE_URL` is injected. If memory agents attempt a DB connection, they will fail. However, these agents may be partially functional if they can fall back to file-based state. Verify that `memory_manager.py` and `dream_processor.py` do not hard-fail on missing DB connection before relying on this workflow.

The commit step uses `|| true` guards, so a partial failure will not block the git push.

**Env vars:** `DATABASE_URL`

---

## order_listener.yml — Order State Listener

**Sprint:** 9
**Status:** CRITICAL WARNING — `DATABASE_URL` orphan, may fail

| Field | Value |
|-------|-------|
| Trigger | Every 6 hours (`0 */6 * * *`) |
| Entry point | `code/sprint_09_memory_loop/agents/agent_00_listener.py` |
| Runtime | Up to 5h55m per run (GitHub Actions 6h hard limit) |
| Timeout | `timeout-minutes: 355` |

**CRITICAL:** This is a long-running listener that restarts every 6 hours via cron. It expects `DATABASE_URL` for state persistence. If the PostgreSQL connection fails at startup, the listener exits immediately, leaving orders unmonitored for up to 6 hours until the next scheduled restart. This is high-impact.

**Recommended action:** Priority migration candidate — either restore PostgreSQL connectivity or port `agent_00_listener.py` to the Excel state store.

**Env vars:** `DATABASE_URL`, `FTF_API_KEY`, `ANTHROPIC_API_KEY`, `TEAMS_WEBHOOK_URL`

---

## Migration Priority

| Workflow | Risk Level | Recommended Action |
|----------|-----------|-------------------|
| `order_listener.yml` | CRITICAL | Migrate to Excel state store or restore PostgreSQL |
| `estimate_generation.yml` | CRITICAL | Migrate to Excel state store or restore PostgreSQL |
| `nightly_memory.yml` | MEDIUM | Verify graceful degradation; migrate if hard-failing |
| `ar_followup.yml` | LOW | Already using legacy `DB_*` pattern; functional if PostgreSQL is up |
| `monthly_statements.yml` | LOW | Functional if PostgreSQL is up; fix ephemeral output risk |

---

## Related

- [Architecture Index](../README.md)
- [Invoice Pipeline Workflow](invoice_pipeline.md)
