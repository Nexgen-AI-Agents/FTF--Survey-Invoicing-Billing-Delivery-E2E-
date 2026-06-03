# Architecture Index — FTF Invoice Pipeline

**Project:** FTF Invoice Pipeline (Sprint 11)
**Last Updated:** 2026-06-03

---

## Overview

The FTF Invoice Pipeline is a multi-agent agentic AI system that automates the end-to-end invoicing workflow for NexGen Surveying: detecting completed survey orders in FTF, collecting data, drafting invoices via Claude, routing for human approval via Microsoft Teams, and finalizing/sending invoices through the FTF platform. State is persisted in an Excel file (`data/invoice_pipeline_state.xlsx`) committed to the repo after each run; the canonical order source is the FTF API + MySQL database (`nexgen_ftf_db`).

---

## Architecture Documents

| Document | Audience | Description |
|----------|----------|-------------|
| [Client View](client_view.md) | Robert, Ryan, Prateek | Plain English — what the system does, how the team interacts with it, business impact |
| [Technical Architecture](technical.md) | Developers / AI engineers | Agent map, state machine, data flows, env vars, infrastructure, known gaps |

---

## Agent Roster (Sprint 11 Invoice Pipeline)

| Agent | File | Purpose | Integrations |
|-------|------|---------|--------------|
| A0 — Orchestrator | `agents/agent_a0_orchestrator.py` | Entry point; runs all agents A1–A7 in sequence | Excel state store |
| A1 — Flag Hunter | `agents/agent_a1_flag_hunter.py` | Queries FTF API for orders with `invoice_needed` flag; writes new rows to Excel | FTF API, MySQL |
| A2 — Data Collector | `agents/agent_a2_data_collector.py` | Collects all data needed to price an order: FTF API details, email replies, county lookups, aerial imagery | FTF API, IMAP, Google Maps API, county URL list |
| A3 — Invoice Compiler | `agents/agent_a3_invoice_compiler.py` | Uses Claude to generate invoice line items, total, and reasoning; posts draft to Teams for approval. Retries up to 2× on parse failure (`max_tokens=2000`) | Claude (Anthropic API), Microsoft Teams |
| A4 — Human Gate v2 | `agents/agent_a4_human_gate_v2.py` | Polls Teams thread replies for APPROVE/REJECT/HOLD from authorized senders; supports natural-language modifications | Microsoft Teams Graph API |
| A5 — Invoice Finalizer | `agents/agent_a5_invoice_finalizer.py` | Creates the approved invoice in FTF; captures invoice ID | FTF API |
| A6 — Sender v2 | `agents/agent_a6_sender_v2.py` | Sends finalized invoice email to client via SMTP; supports `EMAIL_OVERRIDE_ALL` test mode | SMTP |
| A7 — Feedback Learner | `agents/agent_a7_feedback_learner.py` | Extracts pricing rules from Teams feedback; saves to `learned_rules.json` | MS Teams Graph API, Claude Haiku |

---

## GitHub Actions Workflows

| Workflow File | Schedule | Agents | Purpose |
|---------------|----------|--------|---------|
| `invoice_pipeline.yml` | Every 30 min | A0 → A1–A7 | Full cycle: discover + research + price + check replies + send + learn |
| `approval_poller.yml` | Every 2 min | A4 → A5 → A6 | Fast reply check only — no discovery overhead |

Both share concurrency group `invoice-state-write` to prevent concurrent Excel writes.

---

## State Store

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Primary pipeline state | Excel (`data/invoice_pipeline_state.xlsx`) | Per-order status, invoice drafts, approval decisions, timestamps. Committed to repo by Actions bot after each run. |
| Order source (read-only) | MySQL `nexgen_ftf_db` + FTF API | Canonical FTF order data. A1 queries to detect new orders. |
| Learned rules | `data/learned_rules.json` | A7 writes; A3 reads. Pricing rules extracted from team feedback. |

---

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `FTF_API_KEY` | FTF platform API authentication |
| `FTF_API_BASE_URL` | Base URL for FTF REST API |
| `ANTHROPIC_API_KEY` | Claude API key (A3 pricing, A4 NL parse, A7 rule extraction) |
| `MYSQL_HOST/PORT/USER/PASSWORD/DB` | Direct MySQL access for order status reads |
| `TEAMS_TENANT_ID/APP_ID/CLIENT_SECRET` | Azure AD app credentials for MS Graph API |
| `TEAMS_TEAM_ID/CHANNEL_ID` | Target Teams team and channel |
| `TEAMS_INCOMING_WEBHOOK_URL` | Logic App webhook for posting cards to Teams |
| `IMAP_HOST/USER/PASSWORD` | IMAP inbox for reading order-related email replies |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM` | SMTP for sending invoice emails (not yet configured — **BLOCKER**) |
| `APPROVED_SENDERS` | Comma-separated name:email pairs — who can approve/reject |
| `EMAIL_OVERRIDE_ALL` | Test mode: redirect all emails to this address; client never notified |
| `GOOGLE_MAPS_API_KEY` | Aerial imagery for property analysis (A2) |
| `SKIP_SEND_DELAY` | Set to `"1"` by approval_poller.yml to bypass A6 random delay |

---

## Further Reading

- [Client View](client_view.md)
- [Technical Architecture](technical.md)
- [Agent Data Contracts](AGENT_CONTRACTS.md)
- [Invoice Pipeline Workflow](workflows/invoice_pipeline.md)
- [Approval Reminder Workflow](workflows/approval_reminder.md)
- [ADR-001: PostgreSQL State Store (superseded)](../decisions/ADR_001_postgresql_state_store.md)
