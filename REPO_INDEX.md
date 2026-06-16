# Nesa Repo — Single Authoritative Index & Indexing Workflow

> **This is the single authoritative index for the Nesa repo. Always load/refer to this file.**
> **Keep it updated every time something is added (Prateek's standing rule — a stale index is the bug it solves).**

**Keep this file updated after each git push and deployment.**

_Last updated: 2026-06-17 — Reliability hardening pass (resilience audit): failure-email alerts on every workflow, scheduled stuck-order health digest, A0 try/finally session cleanup, broadened Claude→OpenAI fallback (+OpenAI retry), A4 reject/hold terminal guard, poison-data guard, A3 strict dedup, backfill covers canceled/delivered. Plus earlier: A5 idempotency, approval-time duplicate check + Notes, throughput 12/run. Update the date + latest commit hash (`git rev-parse --short HEAD`) on every push._

---

## 0. What this project is

AI invoice pipeline for **Nexgen Surveying** (Field-to-Finish / FTF). Eight agents (A0→A7)
read new survey orders that carry the **invoice-needed (`$`) flag**, price them with Claude
(OpenAI fallback), post each to a human approval sheet in OneDrive, and — on **Approve** —
create the invoice in FTF and email it to the real customer.

- **Environment:** PROD (`DEPLOY_ENV=prod`). FTF prod = `https://fieldtofinish.jobs`.
- **Schedule:** invoice pipeline every 30 min (Power Automate → `workflow_dispatch`); other loops on cron (Eastern Time).
- **Model:** `claude-opus-4-8` interactive; pipeline agents call Claude via `claude_client.py` (FTF-dedicated key + OpenAI fallback).

---

## 1. The pipeline — agents A0→A7

All in `code/sprint_11_invoice_pipeline/agents/`:

| Agent | File | Role |
|-------|------|------|
| **A0** | `agent_a0_orchestrator.py` | Runs A1→A7 in order; syncs Pricing Rules tab → `data/pricing_rules.json` at start |
| **A1** | `agent_a1_flag_hunter.py` | Scans FTF MySQL for `ng_invoice_needed=1 AND ng_status!=0` (the `$` flag); queues new orders. Dedup via `order_exists()`. Cap `MAX_NEW_PER_RUN=100` |
| **A2** | `agent_a2_data_collector.py` | Gathers order packet: FTF API (`get_order`), MySQL, FEMA, appraiser, aerial analysis |
| **A3** | `agent_a3_invoice_compiler.py` | Prices the order. **Guards:** canceled (`ng_status==0`), **already-invoiced (`get_order().invoiced`)**, canceled/delivered (`ng_status_desc`), condo. **Pricing:** deterministic `match_pricing_rule()` exact override → else AI prompt (with Pricing Rules tab + A7 learned rules injected). Posts row to OneDrive Approvals |
| **A4** | `agent_a4_human_gate_v2.py` | Reads Approve/Reject/On-hold from the sheet; reconciles edited amounts (per-service breakdown + total) |
| **A5** | `agent_a5_invoice_finalizer.py` | Finalizes the approved invoice in FTF |
| **A6** | `agent_a6_sender_v2.py` | Emails the invoice to the customer. Recipient = `EMAIL_OVERRIDE_ALL or client_email` (override CLEARED in prod → real customers) |
| **A7** | `agent_a7_feedback_learner.py` | Learns approved per-service prices → `data/learned_rules.json` (2+ consistent approvals ⇒ `active`; injected into A3 prompt) |

**Run scripts / maintenance** (`code/sprint_11_invoice_pipeline/`):
`run_excel_watcher.py`, `run_approval_poller.py`, `backfill_excel_rows.py`,
`cleanup_stale_excel_rows.py`, `delete_duplicate_rows.py`, `fix_unknown_rows.py`,
`reset_stuck_orders.py`, `release_test_orders.py`, `set_excel_actions.py`.

---

## 2. Shared core (`code/shared/core/`)

| File | Responsibility |
|------|----------------|
| `claude_client.py` | LLM call wrapper. FTF-dedicated Anthropic key → 3 retries → **OpenAI gpt-4o fallback** |
| `ftf_client.py` | FTF REST API. **`get_order()` unwraps the `{"data":…,"success":…}` envelope** — read fields directly |
| `ftf_mysql.py` | FTF MySQL (AWS RDS). `get_invoice_needed_orders()` (the `$`-flag intake), `get_order_details()`, `get_company_info()`, `find_duplicate_orders()` |
| `ftf_portal_client.py` | FTF portal login (nesa HR user) for invoice generation/delivery |
| `ftf_books_client.py` | FTF Books endpoints |
| `onedrive_excel_client.py` | OneDrive workbook via Graph API. Approvals tab, Pipeline Guide, Pricing Rules, How-To. `append_approval_row()`, `get_pending_order_ids()` (dedup truth), `get_pricing_rules()`, `match_pricing_rule()`, `ensure_action_dropdown()` (self-heals J2:J10000 dropdown via openpyxl) |
| `excel_db.py` | **Authoritative state store** = `data/invoice_pipeline_state.xlsx`, sheet `pipeline_state`. `save_order_state()`, `get_orders_by_status()`, `order_exists()` |
| `fema_client.py` | FEMA flood-zone lookups |
| `governance.py`, `refund_guard.py` | Safety rails |
| `logger.py`, `exceptions.py`, `state.py`, `db.py` | Infra (db.py = legacy Postgres, superseded by excel_db) |

**Config (`code/shared/config/`):** `settings.py` (precedence: `os.getenv() or _PROFILE[...]` — env/Secret overrides profile), `env_profiles.py` (stage/prod), `models.py`, `roles.py`, `flag_triggers.py`, `prompts/`, `knowledge_base/`.

---

## 3. State & data (`data/`)

| File | Purpose | Git? |
|------|---------|------|
| `invoice_pipeline_state.xlsx` | **AUTHORITATIVE** pipeline state (sheets: pipeline_state, learnings, pending_confirmations, poll_state) | committed (bot auto-commits each run) |
| `pipeline_state.json` | Dashboard export only (mirror of state) | committed |
| `pricing_rules.json` | Synced from the OneDrive Pricing Rules tab each run | committed |
| `learned_rules.json` | A7 self-learned price rules + order overrides | committed |

**OneDrive workbook** (`FTF-Invoicing Agent.xlsx`, via `ONEDRIVE_SHARE_URL`): tabs **Approvals** (authoritative dedup source for A3), **Pipeline Guide**, **Pricing Rules** (user input → both deterministic override AND AI learning), **How to use Invoicing agent**.

**Full reset:** `python scripts/reset_all_state.py [--trigger]` — wipes OneDrive Approvals rows + xlsx `pipeline_state` + `pipeline_state.json`, restores the Action dropdown, preserves learnings/Pricing Rules.

---

## 4. CI/CD — `.github/workflows/` (all run `TZ=America/New_York`)

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `invoice_pipeline.yml` | `workflow_dispatch` (Power Automate, ~30 min) | Runs A0→A7; commits state; pushes dashboard. `INVOICE_BATCH_SIZE=10` |
| `excel_approval_watcher.yml` | schedule | Reads approvals, drives A4→A6 |
| `approval_poller.yml` | schedule | Polls approval replies |
| `approval_reminder.yml` / `set_excel_actions.yml` | schedule | Reminders / action helpers |
| `ar_followup.yml` | cron `0 11 * * *` (~7am ET) | AR follow-ups |
| `nightly_memory.yml` | cron `0 6 * * *` (~2am ET) | Memory loop |
| `monthly_statements.yml` | cron `0 12 1 * *` (~8am ET 1st) | Monthly statements |
| `pipeline_health.yml` | cron `0 13 * * *` (~9am ET) | Stuck-order sweep → emails a digest if any order is stuck >24h |

**Failure alerting:** `invoice_pipeline.yml` + `excel_approval_watcher.yml` have an `if: failure()` step that runs `scripts/notify_failure_email.py` → emails `NOTIFICATION_TO_EMAILS` so a failed run never goes unnoticed.

Secrets via GitHub repo Secrets (Anthropic, OpenAI, FTF, MySQL, Azure/Graph, SMTP, etc.). `.env` is gitignored — local mirror of those Secrets (prod values).

---

## 5. Other sprints (history / supporting)

`code/sprint_00…10` — foundation, monitor, classifier/pricing, human gate, writer, reviewer,
sender/reporter, AR follow-up, monthly statements, memory loop, staging test.
`sprint_11_limited_production`, `sprint_12_full_production` — rollout stages.
Active production path is **sprint_11_invoice_pipeline**.

---

## 6. Scripts (`scripts/`)

Key: `reset_all_state.py` (full reset), `repair_row_fills.py` (fix stale red row fills),
`pipeline_health_check.py` (stuck-order digest), `notify_failure_email.py` (workflow-failure
email), `diag_order.py` (dump prod FTF order JSON),
`retest_reset_order.py` (reset one order for retest), `export_pipeline_json.py`,
`export_pipeline_excel.py`, `update_build_timeline.py`, `test_connections.py`,
`train_pricing.py`, `fetch_historical_pricing.py`, plus demo/report/QA generators.

---

## 7. Docs & tracking

- `CLAUDE.md` — project rules (READ FIRST), then `memory.md`.
- `token_usage.txt` — mandatory token log (update each session + commit `[skip ci]`).
- `build_timeline.txt`, `compact_chat.txt`, `CHANGELOG.md`, `learnings.md`, `user_learnings.md`.
- `docs/` — architecture, decisions, transcripts, QA reports, demos.
- `code/RELEASE_RUNBOOK.md` — release steps.

---

## 8. INDEXING WORKFLOW — how to keep this file true

> A stale index is worse than none. Run this on **every git push and deployment.**

1. **Before you finish a task that adds/moves/deletes a file or changes a flow:** update the relevant table here in the same change.
2. **After each `git push`:** bump the `_Last updated_` line (date + new commit hash). One-liner to get the hash: `git rev-parse --short HEAD`.
3. **After each deployment / cutover** (env flip, secret change, schedule change): update §0 (environment), §4 (CI/CD), and note it in `CHANGELOG.md`.
4. **When adding a new agent / core module / workflow / data file:** add a row to §1–§4 with its file path and one-line responsibility.
5. **When adding a script:** add it to §6.
6. **Sanity check (quarterly or on big refactors):** diff this file against the live tree —
   `ls code/shared/core/`, `ls code/sprint_11_invoice_pipeline/agents/`, `ls .github/workflows/`, `ls data/`, `ls scripts/` — and reconcile any drift.
7. Keep entries **one line each**; this is a map, not documentation. Link to deeper docs in §7.
