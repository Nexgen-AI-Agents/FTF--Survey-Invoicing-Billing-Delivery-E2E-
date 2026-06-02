# Architecture Index — FTF Invoice Pipeline

**Project:** FTF Invoice Pipeline (Sprint 11)
**Last Updated:** 2026-06-02

---

## Overview

The FTF Invoice Pipeline is a multi-agent agentic AI system that automates the end-to-end invoicing workflow for NexGen Surveying: detecting completed survey orders in MySQL, collecting data, drafting invoices via Claude, routing for human approval via Microsoft Teams, and finalizing/sending invoices through the FTF platform. State is persisted in an Excel file (`data/invoice_pipeline_state.xlsx`) committed to the repo after each run; the canonical order source is the FTF MySQL database (`nexgen_ftf_db`).

---

## Agent Roster (Sprint 11 Invoice Pipeline)

| Agent | File | Purpose | Integrations |
|-------|------|---------|--------------|
| A0 — Orchestrator | `code/sprint_11_invoice_pipeline/agents/agent_a0_orchestrator.py` | Entry point; runs all agents in sequence; loads Excel state | Excel state store |
| A1 — Flag Hunter | `code/sprint_11_invoice_pipeline/agents/agent_a1_flag_hunter.py` | Queries MySQL for completed FTF orders that need invoicing; writes new rows to Excel | MySQL (`nexgen_ftf_db`) |
| A2 — Data Collector | `code/sprint_11_invoice_pipeline/agents/agent_a2_data_collector.py` | Collects all data needed to price an order: FTF API details, email replies, county lookups, aerial imagery | FTF API, IMAP, Google Maps API, county URL list |
| A3 — Invoice Compiler | `code/sprint_11_invoice_pipeline/agents/agent_a3_invoice_compiler.py` | Uses Claude to generate invoice line items, total, and reasoning; posts draft to Teams for approval | Claude (Anthropic API), Microsoft Teams |
| A4 — Human Gate | `code/sprint_11_invoice_pipeline/agents/agent_a4_human_gate_v2.py` | Polls Teams thread replies for APPROVE/REJECT/HOLD from authorized senders; supports natural-language modifications | Microsoft Teams Graph API |
| A5 — Invoice Finalizer | `code/sprint_11_invoice_pipeline/agents/agent_a5_invoice_finalizer.py` | Creates the approved invoice in FTF Books; captures invoice ID and URL | FTF Books API |
| A6 — Sender v2 | `code/sprint_11_invoice_pipeline/agents/agent_a6_sender_v2.py` | Sends finalized invoice email to client via SMTP; enforces ET business-hours gate; records sent timestamp | SMTP |

---

## GitHub Actions Workflows

| Workflow File | Name | Trigger | Purpose | Status |
|---------------|------|---------|---------|--------|
| `invoice_pipeline.yml` | Invoice Pipeline (Sprint 11) | Every 5 min | Runs the full A0–A6 agent pipeline; commits updated Excel state | Active |
| `poll_approval_monitor.yml` | Teams Approval Monitor | Every 5 min | Polls Teams for APPROVE/REJECT commands on pending invoices | Active |
| `approval_reminder.yml` | Daily Approval Reminder | Weekdays 2 PM UTC | Sends Teams reminder of invoices still awaiting approval | Active |
| `ar_followup.yml` | AR Follow-Up Loop | Daily 7 AM UTC | Sprint 7 AR scanner and escalation alerts | Active (PostgreSQL) |
| `monthly_statements.yml` | Monthly Statements Loop | 1st of month, 8 AM UTC | Generate, review, and send monthly statements | Active (PostgreSQL) |
| `estimate_generation.yml` | Estimate Generation Loop | Hourly | Sprint 9 estimate orchestrator | Warning: DATABASE_URL orphan |
| `nightly_memory.yml` | Nightly Memory Loop | Daily 4 AM UTC | Sprint 9 memory manager and dream processor | Warning: DATABASE_URL orphan |
| `order_listener.yml` | Order State Listener | Every 6 hours | Sprint 9 long-running order state listener | Warning: DATABASE_URL orphan |

---

## State Store

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Primary pipeline state | Excel (`data/invoice_pipeline_state.xlsx`) | Per-order status, invoice drafts, approval decisions, timestamps. Committed to repo by `invoice_pipeline.yml` after each run. Managed via `code/shared/core/excel_db.py`. |
| Order source (read-only) | MySQL `nexgen_ftf_db` | Canonical FTF order data. A1 queries this to detect new orders. Managed via `code/shared/core/ftf_mysql.py`. |

---

## Key Environment Variables

| Variable | Purpose | Workflows That Use It |
|----------|---------|----------------------|
| `FTF_API_KEY` | FTF platform API authentication | `invoice_pipeline`, `ar_followup`, `estimate_generation`, `order_listener` |
| `FTF_API_BASE_URL` | Base URL for FTF REST API | `invoice_pipeline`, `estimate_generation`, `order_listener` |
| `ANTHROPIC_API_KEY` | Claude API key for invoice drafting (A3) | `invoice_pipeline`, `estimate_generation`, `order_listener` |
| `MYSQL_HOST` | MySQL server hostname | `invoice_pipeline` |
| `MYSQL_PORT` | MySQL server port | `invoice_pipeline` |
| `MYSQL_USER` | MySQL username | `invoice_pipeline` |
| `MYSQL_PASSWORD` | MySQL password | `invoice_pipeline` |
| `MYSQL_DB` | MySQL database name (`nexgen_ftf_db`) | `invoice_pipeline` |
| `TEAMS_TENANT_ID` | Azure AD tenant for Teams Graph API | `invoice_pipeline`, `poll_approval_monitor`, `approval_reminder` |
| `TEAMS_APP_ID` | Azure AD app (client) ID | `invoice_pipeline`, `poll_approval_monitor`, `approval_reminder` |
| `TEAMS_CLIENT_SECRET` | Azure AD app secret | `invoice_pipeline`, `poll_approval_monitor`, `approval_reminder` |
| `TEAMS_TEAM_ID` | Target Teams team ID | `invoice_pipeline`, `poll_approval_monitor`, `approval_reminder` |
| `TEAMS_CHANNEL_ID` | Target Teams channel ID | `invoice_pipeline`, `poll_approval_monitor`, `approval_reminder` |
| `TEAMS_INCOMING_WEBHOOK_URL` | Webhook for posting cards to Teams | `invoice_pipeline`, `poll_approval_monitor`, `approval_reminder` |
| `TEAMS_WEBHOOK_URL` | Alternate webhook (legacy agents) | `invoice_pipeline`, `ar_followup`, `monthly_statements`, `estimate_generation`, `order_listener` |
| `IMAP_HOST` | IMAP server for reading email replies | `invoice_pipeline` |
| `IMAP_USER` | IMAP username | `invoice_pipeline` |
| `IMAP_PASSWORD` | IMAP password | `invoice_pipeline` |
| `SMTP_HOST` | SMTP server for sending invoices/notifications | `invoice_pipeline`, `monthly_statements` |
| `SMTP_PORT` | SMTP port | `invoice_pipeline`, `monthly_statements` |
| `SMTP_USER` | SMTP username | `invoice_pipeline`, `monthly_statements` |
| `SMTP_PASSWORD` | SMTP password | `invoice_pipeline`, `monthly_statements` |
| `SMTP_FROM` | From address for outbound emails | `invoice_pipeline`, `monthly_statements` |
| `FTF_ORDER_URL` | Base URL for linking to orders in Teams messages | `invoice_pipeline`, `poll_approval_monitor`, `approval_reminder` |
| `GOOGLE_MAPS_API_KEY` | Google Maps API for distance/location lookups in A2 | `invoice_pipeline` |
| `GOOGLE_REVIEW_URL` | Google review link included in sent invoices | `invoice_pipeline` |
| `NOTIFICATION_FROM_EMAIL` | From address for failure notifications | `poll_approval_monitor`, `approval_reminder` |
| `NOTIFICATION_TO_EMAILS` | Recipients for failure notifications | `poll_approval_monitor`, `approval_reminder` |
| `APPROVED_SENDERS` | Comma-separated list of Teams users allowed to approve | `poll_approval_monitor` |
| `DATABASE_URL` | PostgreSQL DSN (legacy — Sprint 7/8/9 only) | `ar_followup`, `monthly_statements`, `estimate_generation`, `nightly_memory`, `order_listener` |

---

## Further Reading

- [Invoice Pipeline Workflow](workflows/invoice_pipeline.md)
- [Poll Approval Monitor Workflow](workflows/poll_approval_monitor.md)
- [Approval Reminder Workflow](workflows/approval_reminder.md)
- [Supporting Workflows (AR, Statements, Memory, Listener)](workflows/supporting_workflows.md)
- [Agent Data Contracts](AGENT_CONTRACTS.md)
- [ADR-001: PostgreSQL State Store (superseded)](../decisions/ADR_001_postgresql_state_store.md)
