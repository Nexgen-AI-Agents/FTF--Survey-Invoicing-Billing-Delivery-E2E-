# Nesa Repo — Single Authoritative Index & Indexing Workflow

> **This is the single authoritative index for the Nesa repo. Always load/refer to this file.**
> **Keep it updated every time something is added (Prateek's standing rule — a stale index is the bug it solves).**

**Keep this file updated after each git push and deployment.**

_Last updated: 2026-06-18 (f09bd17f) — Approvals schema 13→15 cols: "Amount ($)"→"Amount ($) by AI", new "Amount ($) by User" (G, AI-filled actual human amount) + "AI Learning" (O); all column indices DERIVED from APPROVAL_HEADERS (no hardcoding), dropdown J→K, end col M→O, guide v9 / how-to v2 (auto-applies on next run once the OneDrive file is unlocked). New AI pricing-learning loop: A3's already-invoiced path now emits a LEARNING row (AI shadow price vs actual `due_amount`) + `pricing_learning.py` (bounds, clamp-or-flag, delta/verdict, negotiated-discount tagging, ±5%/cycle limiter, condo-EC graduation, learned_rules persistence). `ftf_client.get_user_invoiced_amount()` (REST due_amount; not in MySQL). Plus earlier: A4 names invoice generator, reliability hardening, A5 idempotency. Update the date + latest commit hash (`git rev-parse --short HEAD`) on every push._

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
| — | `pricing_learning.py` | Pure helpers for the AI pricing-learning loop: price floors/ceilings, clamp-or-flag, AI-vs-human delta + verdict, negotiated-discount tagging, ±5%/cycle movement limiter, condo-EC graduation, and `record_observation()` → `learned_rules.json`. Used by A3's already-invoiced learning row. |

**Run scripts / maintenance** (`code/sprint_11_invoice_pipeline/`):
`run_excel_watcher.py`, `run_approval_poller.py`, `backfill_excel_rows.py`,
`cleanup_stale_excel_rows.py`, `delete_duplicate_rows.py`, `fix_unknown_rows.py`,
`reset_stuck_orders.py`, `release_test_orders.py`, `set_excel_actions.py`.

---

## 2. Shared core (`code/shared/core/`)

| File | Responsibility |
|------|----------------|
| `claude_client.py` | LLM call wrapper. FTF-dedicated Anthropic key → 3 retries → **OpenAI gpt-4o fallback** |
| `ftf_client.py` | FTF REST API. **`get_order()` unwraps the `{"data":…,"success":…}` envelope** — read fields directly. `get_user_invoiced_amount()` = the human-set amount (REST `due_amount`; the MySQL invoice tables do NOT hold it) for the learning loop |
| `ftf_mysql.py` | FTF MySQL (AWS RDS). `get_invoice_needed_orders(min_ng_id)` (the `$`-flag intake, watermark-gated), `get_max_ng_id()` (intake high-water mark), `get_order_details()`, `get_company_info()`, `find_duplicate_orders()`, `get_invoice_generator()` (who generated an existing invoice, from `ng_log_trackflow`) |
| `intake_watermark.py` | 'Process from today onward' high-water mark (`data/intake_watermark.json`). A1 sets it once (MAX(ng_id)) on first run; later runs only queue `ng_id > watermark` so the historical backlog is permanently skipped |
| `xlsx_shared_strings.py` | `to_shared_strings()` — converts openpyxl's inline-string xlsx into a shared-string xlsx. **openpyxl files Graph rejects with 501 UnsupportedWorkbook until this runs**; wired into `_upload_workbook_bytes()` |
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
| `intake_watermark.json` | 'From today onward' MAX(ng_id) cutoff; A1 self-inits, only `ng_id >` it is queued | committed |

**OneDrive workbook** (`FTF-Invoicing Agent.xlsx`, via `ONEDRIVE_SHARE_URL`): tabs **Approvals** (authoritative dedup source for A3), **Pipeline Guide**, **Pricing Rules** (user input → both deterministic override AND AI learning), **How to use Invoicing agent**.

**Full reset:** `python scripts/reset_all_state.py [--trigger]` — wipes OneDrive Approvals rows + xlsx `pipeline_state` + `pipeline_state.json`, restores the Action dropdown, preserves learnings/Pricing Rules.

---

## 4. Production runtime — PROD SERVER (since 2026-06-26) + CI/CD `.github/workflows/`

**The invoice pipeline now runs on the prod server `FTF-NEAdmin-HA-01` (52.23.128.232), NOT GitHub Actions** — it is the only host that reaches the private RDS (intake A1). Single-runner model: deploy dir `~/FTF Invoicing Agent`, venv `.venv`, `.env` (`DEPLOY_ENV=prod`). Two cron jobs share one `flock` lock; state is kept LOCAL on the server (not pushed to git):
- `*/30 * * * *` → `scripts/run_server_pipeline.sh` → A0 orchestrator (intake A1→A3 + backstop A5/A6/A7), 10 orders/run.
- `5,10,…,55 * * * *` → `scripts/run_server_watcher.sh` → `run_excel_watcher.py` (A4 approval → A5 invoice → A6 send). REQUIRED because A0's `run_a4()` is a no-op stub — it does not action sheet approvals.
- `0 10,11 * * *` (06:00-ET guard in the wrapper) → `scripts/run_server_daily_report.sh` → `daily_report.py`: posts the morning report (sheet link + precise what-to-do + AI-written learnings) to the 'AI - Invoicing Agent' Teams chat. App-only Graph can't post chat messages, so it POSTs `{"message": html}` to a Power Automate HTTP flow (`TEAMS_FLOW_URL` in `.env`); the flow posts into the chat.

Both wrappers email via `notify_failure_email.py` on non-zero rc. **A redeploy must NOT overwrite the server's `data/` (live state).**

**DISABLED on GitHub (replaced by the server):** `invoice_pipeline.yml`, `excel_approval_watcher.yml`, `approval_poller.yml`. Their Power Automate triggers should be turned OFF to stop 403 noise. The still-active workflows below are unrelated to the invoice runner.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `invoice_pipeline.yml` | DISABLED (moved to server cron) | was A0→A7 every ~30 min |
| `excel_approval_watcher.yml` | DISABLED (moved to server cron) | was A4→A6 approval watcher |
| `approval_poller.yml` | DISABLED (moved to server cron) | was approval-reply poller |
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

**Server runtime (prod cron):** `run_server_pipeline.sh` (A0 intake every 30 min), `run_server_watcher.sh` (approve→invoice→send every 5 min) — see §4. `make_rds_runbook.py` (DevOps secure-DB-access options PDF).

Key: `reset_all_state.py` (full reset), `repair_row_fills.py` (fix stale red row fills),
`pipeline_health_check.py` (stuck-order digest), `notify_failure_email.py` (workflow-failure
email), `diag_order.py` (dump prod FTF order JSON), `probe_trackflow.py` (read-only
ng_log_trackflow schema/diagnostic — used to build the invoice-generator lookup),
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
