# Developer Onboarding — FTF Agentic AI OS

Read this file to get up to speed in under 10 minutes. Applies to any new developer agent or human joining the project.

---

## Step 1 — Read Mandatory Files (in order)

1. `CLAUDE.md` — your role and the operating rules
2. `memory.md` — project brain: context, APIs, pricing, decisions, dependencies
3. `learnings.md` — AI mistake log and confirmed patterns
4. `dev_team/TEAM.md` — team structure, review flow, spawn rules
5. `dev_team/CODE_STANDARDS.md` — coding rules (read every line)
6. `dev_team/developer_review.md` — shared dev learnings to date
7. `sprints/index.md` — sprint map and active sprint
8. `issues/issue.md` — current open issues

---

## Step 2 — Understand the System

Three automation loops:

| Loop | Agents | Trigger |
|------|--------|---------|
| Estimate Generation | Agents 2–9 | Every 60 min — monitor CRM → classify → price → write → review → send |
| AR Follow-Up | Agents 10–14 | Daily — scan unpaid invoices → remind → escalate |
| Monthly Statements | Agents 15–17 | 1st of month — compile B2B orders → Excel+PDF → deliver |

All agents are isolated Python files. All shared code lives in `code/shared/`.

---

## Step 3 — Understand the Code Layout

```
code/
  shared/              ← read/write by ALL agents
    core/              ← ftf_client, claude_client, fema_client, db, logger
    config/            ← models.py, flag_triggers.py, prompts/, settings.py
    models/            ← data models (dataclasses/pydantic)
  sprint_00_foundation/   ← Sprint 0 code only
  sprint_01_monitor/      ← Sprint 1 code only
  ...                     ← never import across sprint folders
```

---

## Step 4 — API Access (Staging)

| API | Base URL | Auth |
|-----|----------|------|
| FTF CRM/Books/Pricing | `https://stage.fieldtofinish.jobs/ftf-ai-api/v1` | Key: `9fK2#vQ8Lm@7XpR4` |
| FEMA Flood Map | `https://msc.fema.gov/arcgis/rest` | None (public) |
| Claude API | `https://api.anthropic.com/v1` | Key in `.env` |

All API keys must come from environment variables — never hardcode.

---

## Step 5 — Start Working

1. Check `sprints/index.md` — find active sprint
2. Open active sprint file — read tasks, blockers, status
3. Check `issues/issue.md` — any open issues for your sprint
4. Pick a task, mark it `in_progress` in the sprint file
5. Write code following `CODE_STANDARDS.md`
6. Self-check against `PR_CHECKLIST.md`
7. Hand to Senior Dev for review

---

## Key Rules (No Exceptions)

- Raw API/DB/LLM calls: **never** in agent files — always `core/`
- Hardcoded credentials: **never**
- Hardcoded prices or model names: **never**
- Tests: **required** before code review
- Git push: **after every file created or updated** — no exceptions
