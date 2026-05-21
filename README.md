# FTF Agentic AI Operating System

Automated survey invoicing, AR follow-up, and monthly billing for NexGen Land Surveying (Field to Finish client).

---

## What This System Does

| Loop | Trigger | Agents |
|------|---------|--------|
| Estimate Generation | Every 60 min — monitors FTF CRM for new orders | Agents 1–9 |
| AR Follow-Up | Daily — scans unpaid invoices, sends escalating reminders | Agents 10–14 |
| Monthly Statements | 1st of every month — generates Excel + PDF, delivers via MS Teams | Agents 15–17 |

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| PostgreSQL | 15+ |
| Git | Any recent |

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/Nexgen-AI-Agents/FTF--Survey-Invoicing-Billing-Delivery-E2E-.git
cd FTF--Survey-Invoicing-Billing-Delivery-E2E-
```

**2. Create and activate virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**
```bash
cp .env.example .env
# Edit .env and fill in all values — see comments in .env.example
```

**5. Provision the database**
```bash
psql -U $DB_USER -d $DB_NAME -f db/schema.sql
```

---

## Running Tests

```bash
# Run all tests
pytest code/ -v

# Run a specific sprint's tests
pytest code/sprint_00_foundation/tests/ -v

# Run with coverage
pytest code/ --cov=code/shared --cov-report=term-missing
```

---

## Project Structure

```
FTF-Agentic-AI/
├── code/
│   ├── shared/                  # Shared infrastructure (ALL sprints depend on this)
│   │   ├── core/                # ftf_client, claude_client, fema_client, db, logger
│   │   ├── config/              # settings, models, flag_triggers, prompts/, knowledge_base/
│   │   └── models/              # Order, Estimate, ARReminder data models
│   └── sprint_NN_name/          # Per-sprint agent code + tests
├── db/
│   └── schema.sql               # PostgreSQL schema (5 tables)
├── scripts/
│   └── test_connections.py      # Verify all 5 API connections are live
├── .github/workflows/           # CI/CD — 3 cron-triggered workflows
├── sprints/                     # Sprint planning files
├── TEAM/                        # All 22 team role cards
├── docs/                        # Project tracking, ADRs, reference docs
├── Resources/                   # BRD, architecture diagrams, API docs
├── Dependencies/                # Stakeholder question files
├── issues/issue.md              # Issue tracker
└── CHANGELOG.md                 # Release log
```

---

## Key Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | AI operating rules — read first every session |
| `memory.md` | Project brain — context, decisions, dependencies |
| `learnings.md` | AI mistake log — patterns and confirmed decisions |
| `sprints/index.md` | Sprint master index — find active sprint here |
| `docs/client_progress_tracker.md` | Client-facing status tracker |
| `TEAM/TEAM_OVERVIEW.md` | All 22 roles — who does what |
| `code/RELEASE_RUNBOOK.md` | Step-by-step deploy procedure |

---

## Environment Variables

See `.env.example` for all required variables with descriptions.
Never commit `.env` — it is gitignored.

---

## CI/CD

Three GitHub Actions workflows (created in Sprint 0):
- `estimate_generation.yml` — runs every 60 minutes
- `ar_followup.yml` — runs daily at 7 AM
- `monthly_statements.yml` — runs on the 1st of every month at 8 AM

Required GitHub Secrets: `FTF_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `TEAMS_WEBHOOK_URL`

---

## Current Status

See `sprints/index.md` for sprint-by-sprint status.
See `docs/client_progress_tracker.md` for client-facing milestone status.
