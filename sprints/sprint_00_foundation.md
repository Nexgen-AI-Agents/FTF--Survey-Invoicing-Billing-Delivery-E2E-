# Sprint 0 — Foundation & Connections

## Overview

| Field | Value |
|-------|-------|
| Goal | GitHub repo, full folder scaffold, all core/ infrastructure, config/, DB schema, test all 5 API connections |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | — (first sprint, no dependencies) |
| Outputs | `core/` (7 files), `config/` (4 files), `db/schema.sql`, `.env.example`, `scripts/test_connections.py`, `.github/workflows/` (3 stubs), confirmed green on all 5 API checks |

---

## Tasks

### Repo & Structure
- [ ] Create GitHub repo `ftf-agentic-ai-os` — private, under `Nexgen-AI-Agents` org
- [ ] Scaffold full folder structure per `Resources/Agentic_AI_Folder_Structure_v2.docx`
- [ ] Add all GitHub Secrets: `FTF_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `TEAMS_WEBHOOK_URL`
- [ ] Create `.gitignore` (include `.env`, `logs/`, `__pycache__/`)
- [ ] Create `README.md` with setup instructions

### core/ — Infrastructure (build in this order)
- [ ] `core/exceptions.py` — `AgentError`, `ReviewerFailError`, `MaxRetriesError`, `LLMUnavailableError`, `PricingError`, `FEMAUnavailableError`
- [ ] `core/logger.py` — unified logging, masks PII (first 3 chars + `***`), never `print()` in agents
- [ ] `core/db.py` — `get_pending_order()`, `save_order_state()`, `log_decision()`, `get_unprocessed_reminder()`
- [ ] `core/state.py` — `mark_classified()`, `mark_flagged()`, `mark_priced()`, `mark_sent()`
- [ ] `core/ftf_client.py` — wraps ALL 3 FTF APIs: `get_orders()`, `get_order()`, `get_customer()`, `get_pricing()`, `get_pricing_overrides()`, `create_invoice()`, `send_invoice()`, `send_reminder()`, `mark_estimate_sent()`, `health_check()`
- [ ] `core/fema_client.py` — `check_flood_zone(lat, lng)` → zone code or `"UNAVAILABLE"`
- [ ] `core/claude_client.py` — `call(model, system, user, max_tokens)`, 3x retry on rate limit, raises `LLMUnavailableError`

### config/ — Configuration
- [ ] `config/settings.py` — `MAX_REVIEWER_RETRIES=3`, `ESTIMATE_DELAY_MIN=360`, `ESTIMATE_DELAY_MAX=780`, `AR_ESCALATION_DAYS=90`, `ELEVATION_CERT_PRICE=225`, `SERVICE_STATE="FL"`
- [ ] `config/models.py` — Haiku for Monitor/AR Scanner/Scheduler; Sonnet for all reasoning agents
- [ ] `config/flag_triggers.py` — `ALWAYS_FLAG_SERVICES`, `SERVICE_STATE="FL"`, `COMPETITOR_NAMES=[]` (placeholder), `NEVER_AUTO_QUOTE=[]` (placeholder)
- [ ] `config/knowledge_base/service_names.json` — all 24 services with exact names + prices

### Database
- [ ] `db/schema.sql` — 5 tables: `processed_orders`, `ar_reminders`, `monthly_statements`, `agent_decision_log`, `excluded_ar_clients`
- [ ] Provision PostgreSQL instance (staging)
- [ ] Run schema against fresh DB — confirm no errors

### Environment & CI
- [ ] `.env.example` — all 10 vars documented with comments
- [ ] `scripts/test_connections.py` — tests all 5 APIs (see test results table below)
- [ ] `.github/workflows/estimate_generation.yml` — cron `*/60 * * * *` stub
- [ ] `.github/workflows/ar_followup.yml` — cron `0 7 * * *` stub
- [ ] `.github/workflows/monthly_statements.yml` — cron `0 8 1 * *` stub

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| `GET /health` → 200 | 🔲 | FTF API alive |
| `GET /orders?limit=1` → returns data | 🔲 | FTF CRM readable |
| `GET /pricing?service=Boundary+Survey` → $350 | 🔲 | Pricing API correct |
| FEMA zone check on FL lat/lng → returns zone code | 🔲 | FEMA API reachable |
| Claude Haiku `messages.create` → response received | 🔲 | Anthropic API alive |
| `db/schema.sql` runs on fresh PostgreSQL | 🔲 | DB schema valid |
| All `.github/workflows/` YAML valid (no parse errors) | 🔲 | CI stubs parseable |

---

## Blockers

_None expected for Sprint 0._

---

## Decisions Made

_Log here as they happen during this sprint._

---

## Completion Brief

_Written here when sprint is marked ✅ Complete. Then add one-liner link to `memory.md` → Sprint Briefs._

- **Built:**
- **Tests:** all 5 API checks green / DB schema clean
- **Changed from plan:**
- **Carry forward for Sprint 1:**
