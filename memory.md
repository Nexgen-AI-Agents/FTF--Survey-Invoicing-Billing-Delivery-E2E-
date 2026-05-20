# FTF Agentic AI OS — Project Memory

> **INSTRUCTION FOR AI:** Read `CLAUDE.md` FIRST → then `memory.md` → then `learnings.md` → then act. All three must be read before starting any task.
> **ALL files, notes, references, and changes for this project MUST be saved to this workspace folder (OneDrive).**
> **NEVER touch or use local machine space. NEVER save project files to `.claude/` system folders.**
> **Workspace:** `c:\Users\Prateek Chandra\OneDrive - NexGen Enterprises\Claude\Agentic AI\FTF- Survey Invoicing & Billing Delivery (E2E)\`

---

## Project Identity

| Field | Value |
|-------|-------|
| Project | FTF Agentic AI Operating System |
| Client | Field to Finish (FTF) |
| Phase | Phase 1: FTF only |
| Status | Pre-build — documentation complete, no code yet |
| Architect & CTO | Prateek |
| Date Started | May 2026 |

---

## What This System Does

Automates 3 workflows that are currently manual and 9-to-5:

| Loop | What It Does | Schedule | Agents |
|------|-------------|----------|--------|
| Estimate Generation | Monitor FTF CRM → classify → price → write → review → send | Every 60 min | 1–9 |
| AR Follow-Up | Scan unpaid invoices → schedule reminders → write → send → escalate | Daily | 10–14 |
| Monthly Statements | Compile B2B orders → generate Excel+PDF → deliver via MS Teams | 1st of month | 15–17 |

---

## Company Reference (Client)

- **Name:** NexGen Enterprises — operating as NexGen Land Surveying
- **Website:** https://nexgensurveying.com/
- **Address:** 1547 Prosperity Farms Road, Lake Park, Florida 33403
- **Phone:** (561) 508-6272
- **Email:** info@nexgensurveying.com
- **Hours:** Monday–Friday, 9 AM–5 PM (closed weekends)
- **Service Area:** Entire state of Florida — out-of-state orders flagged immediately
- **Key People:** Ryan (Decision Maker), Robert & Mark (SMEs), Jessica (AR Lead), Wyatt (Oversight/Leadership), Prateek (CTO)

---

## API Credentials (Staging)

| API | Base URL | Key |
|-----|----------|-----|
| FTF CRM + Books + Pricing | https://stage.fieldtofinish.jobs/ftf-ai-api/v1 | `9fK2#vQ8Lm@7XpR4` |
| FEMA Flood Map | https://msc.fema.gov/arcgis/rest | None — public, no auth |
| Anthropic Claude | https://api.anthropic.com/v1 | Prateek's key (in .env) |

**Rate limit:** 1 FTF API call per 60 minutes. Max 500 orders per call.

---

## 24 FTF Service Names (Exact — Case Sensitive)

| Service | Price | Flag? |
|---------|-------|-------|
| Acreage | $250 | — |
| ALTA Table A Survey | $1,500 | Always flag |
| B-II Title Review | $450 | Pending confirmation |
| Boundary Survey | $350 | — |
| Building Stake Out | $225 | — |
| Elevation Certificate | $225 | Auto-add if FEMA flood zone |
| Elevation Only | $250 | — |
| Final Survey | $300 | — |
| Form Board Survey | $225 | — |
| Foundation Tie-In | $225 | — |
| Legal Description | $300 | — |
| Lot Split | $450 | — |
| Other Services | $150 | Always flag |
| Pad Stake Out | $225 | — |
| Property Flagging | $150 | — |
| Site Plan | $150 | — |
| Sketch and Description | $300 | — |
| Specific Purpose Survey | $600 | — |
| Survey Re-draw | $150 | — |
| Surveyor's Affidavit | $100 | — |
| Topography Survey | $225 | — |
| Tree Location | $225 | — |
| Update Survey | $250 | — |
| Wetland Delineation | $300 | Pending confirmation |

---

## Agent 4 — 9 Flag Triggers

1. Service in ALWAYS_FLAG_SERVICES (ALTA Table A Survey, Other Services)
2. Service in NEVER_AUTO_QUOTE list (Robert/Mark to provide)
3. Company name matches competitor list (Robert/Mark to provide)
4. Email domain matches competitor domain list
5. Unusual property — large acreage, tidal, special site conditions
6. New customer — uncertain genuine vs. competitor classification
7. Reviewer failure after 3 correction loops
8. FEMA API unavailable — cannot determine flood zone
9. **Property outside Florida** — NGE is FL-only (confirmed via nexgensurveying.com)

---

## Confirmed Decisions (Locked)

| Decision | Answer |
|----------|--------|
| Estimate delay | Random 6–13 minutes per send |
| FEMA flood zone | AI auto-adds Elevation Certificate ($225) — no flag required |
| Monthly statement trigger | 1st of every calendar month |
| Statement format | Excel + PDF via MS Teams + email to billing contact |
| Refunds | Manual only — Jessica / Bobby |
| New customer | AI classifies; flags if unsure |
| Alert channel | MS Teams + email to relevant stakeholders |
| Post-approval send | AI sends automatically — no manual click needed |
| B2B billing contact | Master email; fallback to most recent order email |
| Other Services | Always flag |
| ALTA Table A Survey | Always flag |
| Change order clause | On all estimates — no exceptions |
| Geographic scope Phase 1 | Florida only |
| Change order clause source | Draft in-house — Ryan reviews before go-live, not before build |

---

## Sprint Rules

| Rule | Detail |
|------|--------|
| **Dependency check before every sprint** | Before starting any sprint, identify all blocking dependencies. If a major dependency could halt work mid-sprint, highlight it explicitly before the sprint begins. For each blocker: state what's missing, what it blocks, and whether demo/mock data can substitute. Only proceed once the user has acknowledged or resolved the blockers. |

---

## Open Dependencies

| Priority | Item | Owner | Status |
|----------|------|-------|--------|
| CRITICAL | 15 recording sessions (Recordings 1–15) | Robert/Mark/Jessica/Wyatt | Not started |
| CRITICAL | Competitor company names + domains list | Robert/Mark | Pending |
| CRITICAL | Never-auto-quote service list | Robert/Mark | Pending |
| CRITICAL | Exact FTF names for Construction + Permitting surveys | Robert/Mark | Pending |
| CRITICAL | FTF Books footer supports change order clause | Dev Team | Pending |
| HIGH | B-II Title Review — always flag? | Robert/Mark | Pending |
| HIGH | Wetland Delineation — NGE performs? | Robert/Mark | Pending |
| HIGH | Confirm reminder schedule + escalation threshold (90 days?) | Jessica | Pending |
| HIGH | Client exclusion list for AR reminders | Jessica | Pending |
| HIGH | Monthly statement format confirmation | Wyatt | Pending |
| RESOLVED | Geographic scope | nexgensurveying.com | Florida only ✓ |
| RESOLVED | Change order clause source | In-house draft | No Ryan dependency ✓ |

---

## Workspace Files Index

| File | Purpose |
|------|---------|
| `CLAUDE.md` | **Read first** — AI role, main flow, operating rules. DO NOT EDIT. |
| `memory.md` | **Read second** — project brain, context, dependencies, build order |
| `learnings.md` | **Read third** — AI learnings log: mistakes caught, patterns confirmed, non-obvious decisions |
| `user_learnings.md` | User-facing learnings — bullet points updated on every git push |
| `feedback_sprint_dependencies.md` | Sprint dependency rule — moved from .claude/ system folder to workspace |
| `sprint_log.md` | Redirect only — points to `sprints/` folder |
| `sprints/index.md` | **Sprint master index** — all 13 sprint files, status, dependencies. Read this to find active sprint. |
| `sprints/sprint_NN_name.md` | Individual sprint files — isolated tasks, tests, blockers, completion brief per sprint |
| `client_progress_tracker.md` | Client-facing progress table — sprint status, pending actions, sign-offs |
| `reference_nexgen_surveying_website.md` | NexGen website data — company, services, contacts, geographic coverage |
| `Resources/FTF_Agentic_AI_BRD_v2.docx` | Full business requirements document v2 |
| `Resources/Agentic_AI_Folder_Structure_v2.docx` | Codebase folder structure blueprint |
| `Resources/FTF_Technical_Architecture.html` | 17-agent system diagram (dev view) |
| `Resources/FTF_Client_Architecture.html` | Business workflow diagram (client view) |
| `Resources/FTF_API_Documentation.xlsx` | All 12 API endpoints, pricing, auth |
| `Resources/FTF_Agile_Delivery_Plan.xlsx` | 14-sprint delivery timeline (Weeks 1–14) |
| `Resources/FTF_Dependencies_For_Stakeholders.docx` | 38 dependency items + stakeholder answers |
| `Dependencies/Questions_Jessica.docx` | AR + statement questions for Jessica |
| `Dependencies/Questions_Robert_Mark.docx` | Operations + service questions for Robert & Mark |
| `Dependencies/Questions_Wyatt.docx` | Statement format questions for Wyatt |
| `TEAM/dev/TEAM.md` | Dev team overview — roles, model rules, review flow, spawn rules |
| `TEAM/dev/CODE_STANDARDS.md` | Python coding standards — naming, imports, security, testing rules |
| `TEAM/dev/PR_CHECKLIST.md` | Pre-merge checklist — all code must pass before Senior Dev review |
| `TEAM/dev/ONBOARDING.md` | New dev onboarding — get up to speed in <10 minutes |
| `TEAM/dev/developer_review.md` | Shared dev learnings log — all 3 devs read and append |
| `TEAM/dev/agents/dev_manager.md` | Manager Dev role card — persona, responsibilities, spawn rules |
| `TEAM/dev/agents/senior_dev.md` | Senior Dev role card — complex logic, integration, first-pass review |
| `TEAM/dev/agents/junior_dev.md` | Junior Dev role card — well-defined tasks, self-check before handoff |
| `TEAM/qa/QA_TEAM.md` | QA team overview — roles, QA flow, spawn rules, entry/exit criteria |
| `TEAM/qa/QA_CHECKLIST.md` | Master QA checklist — functional, edge cases, security, performance, release gate |
| `TEAM/qa/DEFINITION_OF_DONE.md` | Explicit DoD — sprint is DONE only when all boxes checked |
| `TEAM/qa/QA_learning.md` | Shared QA learnings log — all 3 QA agents read and append |
| `TEAM/qa/agents/qa_manager.md` | Manager QA role card — final sign-off, release gate, spawn rules |
| `TEAM/qa/agents/senior_qa.md` | Senior QA role card — edge cases, integration, security, test case authoring |
| `TEAM/qa/agents/junior_qa.md` | Junior QA role card — happy path, basic functional, issue logging |
| `TEAM/qa/test_cases/sprint_NN_test_cases.md` | Test case template — copy per sprint, written by Senior QA before dev starts |
| `code/shared/` | Shared infrastructure — `core/`, `config/`, `models/` used by all sprints |
| `code/sprint_NN_name/` | Per-sprint code folder — isolated agents/, tests/, README.md (13 total) |
| `code/RELEASE_RUNBOOK.md` | Step-by-step deploy procedure for staging and production |
| `issues/issue.md` | Issue tracker — all bugs logged here, status flows OPEN→IN DEV→QA→RELEASED |
| `CHANGELOG.md` | Release log — one entry per sprint, updated after every sprint release |
| `docs/decisions/ADR_template.md` | Architecture Decision Record template — copy per major tech decision |

---

## Build Order (What to Build First — No Blockers)

| # | Task | Blocked By |
|---|------|-----------|
| 1 | GitHub repo + full folder structure | Nothing |
| 2 | `db/schema.sql` + provision PostgreSQL | Nothing |
| 3 | All `core/` files (ftf_client, claude_client, fema_client, db, logger) | Nothing |
| 4 | `config/settings.py`, `models.py`, `flag_triggers.py` | Nothing |
| 5 | Agent 2 Monitor | Nothing |
| 6 | Agent 5 Pricing Engine | Nothing |
| 7 | Agent 3 Classifier (FEMA + customer type logic) | Nothing |
| 8 | Draft change order clause → `config/knowledge_base/change_order_clause.txt` | Nothing |
| 9 | Agent 6 Writer | Step 8 done |
| 10 | Agent 4 Human Gate framework | Competitor list (plug in later) |
| 11 | Agents 7, 8, 9 | Agent 6 done |
| 12 | Send recording guide to all stakeholders | Nothing (Prateek action) |
| 13 | Agents 10–14 AR Loop | Jessica recording |
| 14 | Agents 15–17 Statement Loop | Wyatt + Jessica recording |

---

## Rules for AI Working on This Project

1. **Read order every session** — `CLAUDE.md` first → `memory.md` second → `learnings.md` third → `sprints/index.md` → active sprint file → `issues/issue.md` → then act. All must be read before starting any task.
2. **Workspace only** — all files, notes, references, and outputs go into this OneDrive folder. Never use local machine space or `.claude/` system folders for project files.
3. **Git push after every save — NO CONFIRMATION NEEDED** — after creating or updating any workspace file, immediately run `git add . && git commit -m "..." && git push`. Do not ask. Do not wait. Just push.
4. **Model selection** — Haiku for simple/fast tasks (file reads, lookups, minor edits, formatting). Sonnet for complex tasks (multi-step reasoning, code generation, architecture, analysis). NEVER use Opus under any circumstances.
5. **Sprint dependency check** — before starting any sprint, identify all blocking dependencies. Flag any that could halt work mid-sprint. For each blocker: state what's missing, what it blocks, and whether demo/mock data can substitute. Only proceed once user has acknowledged.
6. **Sprint tracking** — open `sprints/index.md` to find active sprint file. Update that sprint file's task checkboxes in real time. On sprint complete: fill Completion Brief in the sprint file → add one-liner link to Sprint Briefs below → update `sprints/index.md` status → update `client_progress_tracker.md`.
7. **One agent, one job** — each agent `.py` file does exactly one thing.
8. **No raw calls** — all API, DB, and LLM calls go through `core/`. Never inside agent files.
9. **No hardcoding** — model names in `config/models.py`, prices via API, prompts in `config/prompts/`, business rules in `config/flag_triggers.py`.
10. **Learnings update** — append to `learnings.md` any time a mistake is caught, a pattern is confirmed, or a non-obvious decision is made. Update `user_learnings.md` on every git push if new learnings exist.

---

## Sprint Briefs

_Written here when each sprint is marked ✅ Complete in sprint_log.md._

<!-- Template:
### Sprint N — Name ✅
- **Built:** list key files
- **Tests:** pass/fail summary
- **Decisions:** anything that changed from the plan
- **Carry forward:** what the next sprint needs to know
-->

