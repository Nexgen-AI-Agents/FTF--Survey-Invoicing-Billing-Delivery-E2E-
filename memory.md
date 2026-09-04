# FTF Agentic AI OS â€” Project Memory

> **INSTRUCTION FOR AI:** Read in this exact order before any task:
> 1. `CLAUDE.md` â€” operating rules
> 2. `memory.md` â€” project brain (this file)
> 3. `TEAM/hierarchy.md` â€” who you are, who you report to, who you guide
> 4. `TEAM/orchestrator/routing_guide.md` â€” how to classify and route incoming work
> 5. `TEAM/leadership/prateek_thinking_patterns.md` â€” how Prateek actually thinks
> 6. `expert_identity.md` â€” FL PSM + survey business expertise
> 7. `learnings.md` â€” known patterns and mistakes
> 8. Then act.
>
> The hierarchy file and routing guide are new (2026-05-29). Every agent has a place. Every message has a route.
> `expert_identity.md` defines your domain expertise as a Florida PSM and survey business expert â€” read it and internalize it, do not skip it.
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
| Status | Pre-build â€” documentation complete, no code yet |
| Architect & CTO | Prateek |
| Date Started | May 2026 |

---

## What This System Does

Automates 3 workflows that are currently manual and 9-to-5:

| Loop | What It Does | Schedule | Agents |
|------|-------------|----------|---------|
| Estimate Generation | Monitor FTF CRM â†’ classify â†’ price â†’ write â†’ review â†’ send | Every 60 min | 1â€“9 |
| AR Follow-Up | Scan unpaid invoices â†’ schedule reminders â†’ write â†’ send â†’ escalate | Daily | 10â€“14 |
| Monthly Statements | Compile B2B orders â†’ generate Excel+PDF â†’ deliver via MS Teams | 1st of month | 15â€“17 |

---

## Company Reference (Client)

- **Name:** NexGen Enterprises â€” operating as NexGen Land Surveying
- **Website:** https://nexgensurveying.com/
- **Address:** 1547 Prosperity Farms Road, Lake Park, Florida 33403
- **Phone:** (561) 508-6272
- **Email:** nesa@nexgenlogix.com
- **Hours:** Mondayâ€“Friday, 9 AMâ€“5 PM (closed weekends)
- **Service Area:** Entire state of Florida â€” out-of-state orders flagged immediately
- **Key People:** Ryan (Decision Maker), Robert & Mark (SMEs), Jessica (AR Lead), Wyatt (Oversight/Leadership), Prateek (CTO)

---

## API Credentials (Staging)

| API | Base URL | Key |
|-----|----------|-----|
| FTF CRM + Books + Pricing | https://stage.fieldtofinish.jobs/ftf-ai-api/v1 | `9fK2#vQ8Lm@7XpR4` |
| FEMA Flood Map | https://msc.fema.gov/arcgis/rest | None â€” public, no auth |
| Anthropic Claude | https://api.anthropic.com/v1 | Prateek's key (in .env) |

**Rate limit:** 1 FTF API call per 60 minutes. Max 500 orders per call.

---

## 24 FTF Service Names (Exact â€” Case Sensitive)

| Service | Price | Flag? |
|---------|-------|-------|
| Acreage | $250 | â€” |
| ALTA Table A Survey | $1,500 | Always flag |
| B-II Title Review | $450 | ALWAYS FLAG (I-055) |
| Boundary Survey | $350 | â€” |
| Building Stake Out | $225 | ALWAYS FLAG until Robert confirms (I-042) |
| Elevation Certificate | $225 | Auto-add if FEMA flood zone |
| Elevation Only | $250 | â€” |
| Final Survey | $300 | â€” |
| Form Board Survey | $225 | â€” |
| Foundation Tie-In | $225 | â€” |
| Legal Description | $300 | â€” |
| Lot Split | $450 | â€” |
| Other Services | $150 | Always flag |
| Pad Stake Out | $225 | â€” |
| Property Flagging | $150 | â€” |
| Site Plan | $150 | â€” |
| Sketch and Description | $300 | â€” |
| Specific Purpose Survey | $600 | â€” |
| Survey Re-draw | $150 | â€” |
| Surveyor's Affidavit | $100 | â€” |
| Topography Survey | $225 | â€” |
| Tree Location | $225 | â€” |
| Update Survey | $250 | â€” |
| Wetland Delineation | $300 | NEVER AUTO-QUOTE (I-005 confirmed, Robert) |

---

## Agent 4 â€” Flag Triggers (Current â€” Production Code)

1. Service in ALWAYS_FLAG_SERVICES: ALTA Table A Survey, Other Services, B-II Title Review, Building Stake Out, Table Survey
2. Service in NEVER_AUTO_QUOTE: Specific Purpose Survey, Lot Split, Wetland Delineation, Topography Survey
3. Company name matches competitor list (30 names confirmed)
4. Email domain matches competitor domain list (14 domains confirmed)
5. Monroe County order â€” always flag
6. VE coastal flood zone â€” always flag
7. Missing county â€” cannot price without it
8. property_lat outside FL bounds when state=FL â€” data entry error flag
9. **Property outside Florida** â€” NGE is FL-only
10. Reviewer failure after 3 correction loops
11. FEMA API unavailable â€” cannot determine flood zone
12. Refund keyword detected â€” stop, alert Jessica immediately (I-063)

---

## Teams Approval Flow

Full rules, commands, edge cases, and state machine documented in:
**`docs/teams_approval_flow.md`** â€” read this file whenever working on approval/rejection logic.

---

## Confirmed Decisions (Locked)

| Decision | Answer |
|----------|--------|
| Estimate delay | Random 6â€“13 minutes per send |
| FEMA flood zone | AI auto-adds Elevation Certificate ($225) â€” no flag required |
| Monthly statement trigger | 1st of every calendar month |
| Statement format | Excel + PDF via MS Teams + email to billing contact |
| Refunds | Manual only â€” Jessica / Robert. AI never touches. |
| AR reminder schedule | FTF platform sends automated reminder emails to clients at Day 30, 60, 90. We do NOT build this â€” it is handled by FTF itself. Post-90: Jessica manual follow-up. |
| AR exclusion list | Managed via `AR_EXCLUSION_LIST` env var (comma-separated emails). Empty by default. Jessica to provide before AR loop goes live. |
| DEFER command | `DEFER <order_id> [reason]` â€” holds approval for 24h without rejecting. Order reappears in next digest. For use when awaiting client callback. |
| Overdue approval alert | Batch digest marks orders aged â‰¥4h with `*** OVERDUE ***`. No separate alert sent â€” just the visual flag. |
| Dynamic pricing complexity | PRICING_COMPLEXITY_ENABLED=false (default). Factors defined in settings.py. Enable only after Robert confirms weights. |
| Workflow failure alerts | Both poll_approval_monitor.yml and approval_reminder.yml post a Teams alert when the workflow itself fails. |
| AR internal escalation | Day 60 â†’ alert Jessica (internal). Day 90 â†’ alert Jessica + all stakeholders (internal). These internal alerts ARE our responsibility to build. |
| AR exclusion list | Empty on launch. System supports additions without rebuild. |
| New customer | AI classifies; flags if unsure |
| Alert channel | MS Teams + email to relevant stakeholders |
| Post-approval send | AI sends automatically â€” no manual click needed |
| B2B billing contact | Master email; fallback to most recent order email |
| Other Services | Always flag |
| ALTA Table A Survey | Always flag |
| Change order clause | On all estimates â€” no exceptions |
| Geographic scope Phase 1 | Florida only |
| Change order clause source | Draft in-house â€” Ryan reviews before go-live, not before build |
| Estimate OS goal | Hunt the missing-invoice flag across ALL order statuses â€” not just Quote. Any uninvoiced order in any status = action required. Agent 2 must be refactored. (Ryan 2026-05-29) |
| Post-invoice: estimate agent stops | Once the invoice is delivered and the flag is gone, the estimate agent stops caring. No post-invoice tracking. Any modification after delivery = manual by staff. (Ryan 2026-05-29) |
| Approval flow: price adjustment | Human reviewer can ADJUST $X before approving. AI updates invoice price to adjusted amount before sending. AI stores adjustment as learning for future similar jobs. (Ryan 2026-05-29) |
| Parallel/shadow mode | Launch in shadow mode first â€” AI suggests but does not send. End-of-day comparison report: AI estimate totals vs actual. Ryan/Bobby evaluate accuracy before enabling auto-send. (Ryan 2026-05-29) |
| Small agents philosophy | Many small single-purpose agents managed by a high-level manager agent. NOT one big agent doing everything. If one breaks, manager keeps running with remaining agents. (Ryan 2026-05-29) |

---

## Sprint Rules

| Rule | Detail |
|------|--------|
| **Pre-sprint dependency check (MANDATORY â€” every sprint, no exceptions)** | Before writing a single line of code for any sprint: (1) List everything the sprint needs. (2) Split into two columns: "buildable now without external input" vs. "blocked by external dependency." (3) Build ALL independent items first â€” never idle-wait on a blocker when independent work exists. (4) Log every blocker as an issue. (5) Stubs are acceptable for blocked items â€” build the interface now, fill the implementation when the dependency arrives. This rule applies to every sprint, every team member, every time. |
| **Dependency check before every sprint** | Before starting any sprint, identify all blocking dependencies. If a major dependency could halt work mid-sprint, highlight it explicitly before the sprint begins. For each blocker: state what's missing, what it blocks, and whether demo/mock data can substitute. Only proceed once the user has acknowledged or resolved the blockers. |

---

## Open Dependencies

| Priority | Item | Owner | Status |
|----------|------|-------|--------|
| CRITICAL | 15 recording sessions (Recordings 1â€“15) | Robert/Mark/Jessica/Wyatt | Not started |
| CRITICAL | Competitor company names + domains list | Competitor Analyst AI | **Bootstrapped 2026-05-25** â€” 25 names + 16 domains in `flag_triggers.py`. Robert/Mark to validate before Sprint 3. |
| CRITICAL | Never-auto-quote service list | Competitor Analyst AI | **Bootstrapped 2026-05-25** â€” 3 FTF service types in `flag_triggers.py`. Robert/Mark to validate before Sprint 3. |
| CRITICAL | Exact FTF names for Construction + Permitting surveys | Robert/Mark | Pending |
| CRITICAL | FTF Books footer supports change order clause | Dev Team | Pending |
| HIGH | B-II Title Review â€” always flag? | Robert/Mark | Pending |
| HIGH | Wetland Delineation â€” NGE performs? | Robert/Mark | Pending |
| HIGH | Confirm reminder schedule + escalation threshold (90 days?) | Jessica | Pending |
| HIGH | Client exclusion list for AR reminders | Jessica | Pending |
| HIGH | Monthly statement format confirmation | Wyatt | Pending |
| RESOLVED | Geographic scope | nexgensurveying.com | Florida only âœ“ |
| RESOLVED | Change order clause source | In-house draft | No Ryan dependency âœ“ |
| RESOLVED | Geocoding for FEMA lat/lng | API probe 2026-05-25 | `GET /orders/{id}` returns `property_lat`/`property_lng` directly â€” no geocoding service needed âœ“ |
| RESOLVED | GET /orders/{id} schema | API probe 2026-05-25 | 26 fields confirmed. `service_type` = actual name or "Quote". `flood_zone` pre-populated by FTF for most orders âœ“ |
| RESOLVED | GET /customers/{id} schema | API probe 2026-05-25 | 12 fields confirmed. `customer_type`, `email`, `pricing_type`, `custom_rate` âœ“ |

---

## Workspace Files Index

| File | Purpose |
|------|---------|
| `CLAUDE.md` | **Read first** â€” AI role, main flow, operating rules. DO NOT EDIT. |
| `memory.md` | **Read second** â€” project brain, context, dependencies, build order |
| `expert_identity.md` | **Read third** â€” FL PSM + survey business expert identity. Defines how AI reasons about NexGen's domain. |
| `learnings.md` | **Read fourth** â€” AI learnings log: mistakes caught, patterns confirmed, non-obvious decisions |
| `clarifications.md` | Q&A log â€” every clarification Prateek asks, answered and saved in table format for future reference |
| `user_learnings.md` | User-facing learnings â€” bullet points updated on every git push |
| `README.md` | GitHub repo readme |
| `CHANGELOG.md` | Release log â€” one entry per sprint, updated after every sprint release |
| `sprints/index.md` | **Sprint master index** â€” all 13 sprint files, status, dependencies. Read this to find active sprint. |
| `sprints/sprint_NN_name.md` | Individual sprint files â€” isolated tasks, tests, blockers, completion brief per sprint |
| `docs/stakeholder_testing.md` | **Master stakeholder testing table** â€” who tests what per sprint, per-person summary, AI team vs. human stakeholders |
| `docs/client_progress_tracker.md` | Client-facing progress table â€” sprint status, pending actions, sign-offs |
| `docs/reference_nexgen_surveying_website.md` | NexGen website data â€” company, services, contacts, geographic coverage |
| `docs/feedback_sprint_dependencies.md` | Sprint dependency rule â€” before every sprint, surface all blockers |
| `Resources/FTF_Agentic_AI_BRD_v2.docx` | Full business requirements document v2 |
| `Resources/Agentic_AI_Folder_Structure_v2.docx` | Codebase folder structure blueprint |
| `architecture/tech architecture/FTF_Technical_Architecture_v1.html` | Technical architecture v1 (Sprint 0-6 era â€” original) |
| `architecture/tech architecture/FTF_Technical_Architecture_v2.html` | **Technical architecture v2 (Sprint 0-11 â€” current)** â€” 19 agents, GitHub Actions 24/7, Agent 12, DEFER, sprint status bar |
| `architecture/client architecture/FTF_Client_Architecture_v1.html` | Client architecture v1 (Sprint 0-6 era â€” original) |
| `architecture/client architecture/FTF_Client_Architecture_v2.html` | **Client architecture v2 (Sprint 0-11 â€” current)** â€” dual entry paths, DEFER branch, 24/7 badge, hard rules panel |
| `Resources/FTF_API_Documentation.xlsx` | All 12 API endpoints, pricing, auth |
| `Resources/FTF_Agile_Delivery_Plan.xlsx` | 14-sprint delivery timeline (Weeks 1â€“14) |
| `Resources/FTF_Dependencies_For_Stakeholders.docx` | 38 dependency items + stakeholder answers |
| `Dependencies/Questions_Jessica.docx` | AR + statement questions for Jessica |
| `Dependencies/Questions_Robert_Mark.docx` | Operations + service questions for Robert & Mark |
| `Dependencies/Questions_Wyatt.docx` | Statement format questions for Wyatt |
| `TEAM/research/competitor_analyst.md` | **Competitor Analyst AI** â€” ACTIVE research agent; Florida market competitor intelligence, flag trigger data, market gap analysis. Tools: WebSearch + WebFetch. |
| `TEAM/research/competitive_analysis.md` | **Florida competitive analysis** â€” NexGen vs. 8 Florida competitors; service gaps, 16 improvement suggestions (P1/P2/P3); competitor names + domains for flag_triggers.py. Updated 2026-05-25. |
| `TEAM/stakeholders/STAKEHOLDERS_OVERVIEW.md` | **Stakeholder AI layer rules** â€” distinction table, org chart, Tier 0/0.5, escalation chain, STUB/ACTIVE rules, enrichment process |
| `TEAM/stakeholders/prateek.md` | Prateek CTO AI agent â€” ACTIVE â€” architecture, code standards, ADR decisions (consulted by ALL team members) |
| `TEAM/stakeholders/ryan.md` | Ryan AI agent â€” STUB â€” estimate tone, business rules, output quality (enriched after Sprint 6) |
| `TEAM/stakeholders/robert.md` | Robert AI agent â€” STUB â€” service classification, flag logic, estimate correctness (enriched after Recordings 1â€“8) |
| `TEAM/stakeholders/mark.md` | Mark AI agent â€” STUB â€” edge cases, unusual properties, out-of-state (enriched after Recordings 1â€“8) |
| `TEAM/stakeholders/jessica.md` | Jessica AI agent â€” STUB â€” reminder tiers, escalation, exclusion list (enriched after Recording 10) |
| `TEAM/stakeholders/wyatt.md` | Wyatt AI agent â€” STUB â€” statement format, B2B delivery, Teams notification (enriched after Recording 11) |
| `TEAM/TEAM_OVERVIEW.md` | **Master team reference** â€” all 22 roles, Tier 0/0.5, escalation chain, decision authority |
| `TEAM/leadership/prateek_cto.md` | Prateek â€” CTO role card â€” technical authority, escalation endpoint, ADR approvals |
| `TEAM/leadership/product_owner.md` | Product Owner role card â€” product vision, backlog, sprint readiness gates |
| `TEAM/leadership/project_manager.md` | Project Manager role card â€” timelines, dependency tracking, agile ceremonies |
| `TEAM/leadership/ryan_wyatt.md` | Ryan & Wyatt combined role card â€” business approval authority, monthly statement oversight |
| `TEAM/architecture/enterprise_architect.md` | Enterprise Architect role card â€” system design, tech stack, ADR ownership |
| `TEAM/architecture/it_infrastructure.md` | IT Infrastructure role card â€” environment setup, prerequisites, deployment runbook |
| `TEAM/architecture/devops_engineer.md` | DevOps Engineer role card â€” CI/CD pipeline, Docker, staging + production deployment |
| `TEAM/architecture/prompt_engineer.md` | Prompt Engineer role card â€” all AI prompts in config/prompts/, output validation |
| `TEAM/architecture/security_engineer.md` | Security Engineer role card â€” threat modelling, OWASP audit, secrets management, pen testing |
| `TEAM/business/ba.md` | Business Analyst role card â€” E2E project knowledge, doc map, requirements clarity |
| `TEAM/design/ui_ux_designer.md` | UI/UX Designer role card â€” human-facing output design (emails, statements, alerts) |
| `TEAM/sme/robert.md` | Robert SME role card â€” operational validation, flag logic, missing data provision |
| `TEAM/sme/mark.md` | Mark SME role card â€” edge case validation, field/office workflow expertise |
| `TEAM/ar/jessica_ar_specialist.md` | Jessica â€” AR Specialist role card â€” AR loop ownership post-implementation, reminder + escalation |
| `TEAM/dev/TEAM.md` | Dev team overview â€” roles, model rules, review flow, spawn rules |
| `TEAM/dev/CODE_STANDARDS.md` | Python coding standards â€” naming, imports, security, testing rules |
| `scripts/notify_workflow_failure.py` | Posts Teams alert on GitHub Actions workflow failure â€” called by `if: failure()` in both monitoring workflows |
| `scripts/run_email_monitor.py` | Continuous runner for Agent 12 (email monitor) â€” IMAP polling, configurable interval, deployment instructions inside |
| `scripts/build_approval_dashboard.py` | Generates `docs/approval_dashboard.html` â€” live approval queue, KPIs, flag trigger stats |
| `scripts/export_flag_stats.py` | Flag calibration report â€” trigger breakdown, approval rates, instant-approval candidates, avg decision time |
| `TEAM/dev/PR_CHECKLIST.md` | Pre-merge checklist â€” all code must pass before Senior Dev review |
| `TEAM/dev/ONBOARDING.md` | New dev onboarding â€” get up to speed in <10 minutes |
| `TEAM/dev/developer_review.md` | Shared dev learnings log â€” all 3 devs read and append |
| `TEAM/dev/agents/dev_manager.md` | Manager Dev role card â€” persona, responsibilities, spawn rules |
| `TEAM/dev/agents/senior_dev.md` | Senior Dev role card â€” complex logic, integration, first-pass review |
| `TEAM/dev/agents/junior_dev.md` | Junior Dev role card â€” well-defined tasks, self-check before handoff |
| `TEAM/qa/QA_TEAM.md` | QA team overview â€” roles, QA flow, spawn rules, entry/exit criteria |
| `TEAM/qa/QA_CHECKLIST.md` | Master QA checklist â€” functional, edge cases, security, performance, release gate |
| `TEAM/qa/DEFINITION_OF_DONE.md` | Explicit DoD â€” sprint is DONE only when all boxes checked |
| `TEAM/qa/QA_learning.md` | Shared QA learnings log â€” all QA agents read and append |
| `TEAM/qa/agents/qa_manager.md` | Manager QA role card â€” final sign-off, release gate, spawn rules |
| `TEAM/qa/agents/senior_qa.md` | Senior QA role card â€” edge cases, integration, security, test case authoring |
| `TEAM/qa/agents/junior_qa.md` | Junior QA role card â€” happy path, basic functional, issue logging |
| `TEAM/qa/agents/qe_manual.md` | QE Manual role card â€” exploratory testing, UX validation of human-facing outputs |
| `TEAM/qa/agents/qe_automation.md` | QE Automation role card â€” automated regression suite, CI/CD coverage, mock management |
| `TEAM/qa/test_cases/sprint_NN_test_cases.md` | Test case template â€” copy per sprint, written by Senior QA before dev starts |
| `code/shared/` | Shared infrastructure â€” `core/`, `config/`, `models/` used by all sprints |
| `code/sprint_NN_name/` | Per-sprint code folder â€” isolated agents/, tests/, README.md (13 total) |
| `code/RELEASE_RUNBOOK.md` | Step-by-step deploy procedure for staging and production |
| `issues/issue.md` | Issue tracker â€” all bugs logged here, status flows OPENâ†’IN DEVâ†’QAâ†’RELEASED |
| `CHANGELOG.md` | Release log â€” one entry per sprint, updated after every sprint release |
| `docs/decisions/ADR_template.md` | Architecture Decision Record template â€” copy per major tech decision |
| `docs/decisions/ADR_001_postgresql_state_store.md` | ADR-001 â€” PostgreSQL chosen as primary state store (ACID, concurrent writes, audit trail) |
| `docs/decisions/ADR_002_python_version.md` | ADR-002 â€” Python 3.11+ minimum (FEMA TLS regression on 3.14; CI uses 3.11) |
| `docs/decisions/ADR_003_model_selection_haiku_sonnet.md` | ADR-003 â€” Haiku for orchestration agents, Sonnet for all reasoning agents; Opus blocked |
| `docs/decisions/ADR_004_shared_core_architecture.md` | ADR-004 â€” All external calls go through `code/shared/core/`; never in agent files |
| `docs/decisions/ADR_005_ftf_api_envelope.md` | ADR-005 â€” `get_orders()` unwraps `{"count","data"}` envelope; callers always get clean list |
| `docs/decisions/ADR_006_fema_graceful_degradation.md` | ADR-006 â€” FEMA unavailable â†’ flag for human review; WARN not FAIL in CI |
| `docs/decisions/ADR_007_estimate_send_delay.md` | ADR-007 â€” 6â€“13 min random delay before sending estimates; confirmed by Ryan |
| `TEAM/qa/test_cases/sprint_01_test_cases.md` | Sprint 1 QA test cases â€” 6 unit tests, 5 integration tests, 4 edge cases, acceptance criteria |
| `code/sprint_01_monitor/agents/agent_02_monitor.py` | Agent 2 â€” CRM Monitor â€” polls FTF API, detects new orders, writes to state DB |
| `code/sprint_01_monitor/tests/conftest.py` | Sprint 1 test path setup â€” adds shared/ and sprint root to sys.path |
| `code/sprint_01_monitor/tests/test_monitor.py` | Sprint 1 unit tests â€” 8 tests covering all monitor scenarios including FTF status filter |
| `config/knowledge_base/ftf_order_statuses.md` | **FTF order status hierarchy** â€” all 16 statuses, core pipeline, per-agent usage rules. Confirmed 2026-05-22. |
| `config/knowledge_base/ftf_api_schemas.md` | **FTF API confirmed schemas** â€” GET /orders (7 fields), GET /orders/{id} (26 fields incl. lat/lng, flood_zone, customer_type), GET /customers/{id} (12 fields). Probed 2026-05-25. Resolves I-014, I-015, I-016. |

---

## Build Order (What to Build First â€” No Blockers)

| # | Task | Blocked By |
|---|------|----------|
| 1 | GitHub repo + full folder structure | Nothing |
| 2 | `db/schema.sql` + provision PostgreSQL | Nothing |
| 3 | All `core/` files (ftf_client, claude_client, fema_client, db, logger) | Nothing |
| 4 | `config/settings.py`, `models.py`, `flag_triggers.py` | Nothing |
| 5 | Agent 2 Monitor | Nothing |
| 6 | Agent 5 Pricing Engine | Nothing |
| 7 | Agent 3 Classifier (FEMA + customer type logic) | Nothing |
| 8 | Draft change order clause â†’ `config/knowledge_base/change_order_clause.txt` | Nothing |
| 9 | Agent 6 Writer | Step 8 done |
| 10 | Agent 4 Human Gate framework | Competitor list (plug in later) |
| 11 | Agents 7, 8, 9 | Agent 6 done |
| 12 | Send recording guide to all stakeholders | Nothing (Prateek action) |
| 13 | Agents 10â€“14 AR Loop | Jessica recording |
| 14 | Agents 15â€“17 Statement Loop | Wyatt + Jessica recording |

---

## Rules for AI Working on This Project

1. **Read order every session** â€” `CLAUDE.md` first â†’ `memory.md` second â†’ `learnings.md` third â†’ `sprints/index.md` â†’ active sprint file â†’ `issues/issue.md` â†’ then act. All must be read before starting any task.
2. **Workspace only** â€” all files, notes, references, and outputs go into this OneDrive folder. Never use local machine space or `.claude/` system folders for project files.
3. **Git push after every save â€” NO CONFIRMATION NEEDED** â€” after creating or updating any workspace file, immediately run `git add . && git commit -m "..." && git push`. Do not ask. Do not wait. Just push.
4. **Model selection** â€” Haiku for simple/fast tasks (file reads, lookups, minor edits, formatting). Sonnet for complex tasks (multi-step reasoning, code generation, architecture, analysis). NEVER use Opus under any circumstances.
5. **Pre-sprint independence check (MANDATORY â€” every sprint, no exceptions)** â€” before writing any code: split the sprint scope into "buildable now" vs. "blocked." Build ALL independent items first. Never wait idle on a blocker when independent work exists. Stub blocked interfaces; fill them when dependencies arrive. Log every blocker as an issue. This rule applies to every sprint, everywhere, always.
6. **Sprint tracking** â€” open `sprints/index.md` to find active sprint file. Update that sprint file's task checkboxes in real time. On sprint complete: fill Completion Brief in the sprint file â†’ add one-liner link to Sprint Briefs below â†’ update `sprints/index.md` status â†’ update `docs/client_progress_tracker.md`.
7. **One agent, one job** â€” each agent `.py` file does exactly one thing.
8. **No raw calls** â€” all API, DB, and LLM calls go through `core/`. Never inside agent files.
9. **No hardcoding** â€” model names in `config/models.py`, prices via API, prompts in `config/prompts/`, business rules in `config/flag_triggers.py`.
10. **Learnings update** â€” append to `learnings.md` any time a mistake is caught, a pattern is confirmed, or a non-obvious decision is made. Update `user_learnings.md` on every git push if new learnings exist.
11. **Skills** â€” invoke and create autonomously. See `skills/INDEX.md` for the full registry, operating rules, and how to add new skills.

---

## Sprint Briefs

_Written here when each sprint is marked âœ… Complete in sprint_log.md._

### Sprint 0 â€” Foundation & Connections âœ…
- **Built:** `core/` (7 files), `config/` (4 files), `db/schema.sql` (5 tables), 3 CI stubs, test_connections.py, conftest.py, 7 unit test files, QA test cases
- **Tests:** 6/6 PASS â€” FTF health/orders/pricing, Claude Haiku, PostgreSQL DB, YAML valid. FEMA = WARN (firewall on local; passes on GitHub Actions).
- **Decisions:** `get_orders()` unwraps `{"count","data"}` envelope; `get_pricing()` is per-service lookup with `?service=X&tier=Y`; FEMA client uses `OP_LEGACY_SERVER_CONNECT`; test script uses ASCII arrows for Windows cp1252 compat.
- **Carry forward:** FTF pricing is per-service â€” Pricing Engine calls once per service name. Monitor agent reads from `data` key of orders response.
- **Post-sprint fixes (2026-05-21):** Added `order_exists()` to `db.py`; fixed `test_get_pricing` missing arg; fixed `state.py` `utcnow()` â†’ `now(UTC)`. 7 ADRs written. 42/42 tests pass.
- **Full brief:** [sprints/sprint_00_foundation.md](sprints/sprint_00_foundation.md)

### Sprint 1 â€” CRM Monitor âœ… (Complete â€” 2026-05-22)
- **Built:** `agent_02_monitor.py` â€” calls `get_orders(status="Quote")` with full pagination (207,622 total orders, 500/page hard cap), skips `estimate_sent=True` and existing DB rows, saves new as `status="pending"`. `ftf_client.get_orders()` updated with `status` param + offset pagination.
- **Tests:** 16/16 Sprint 1 pass. 51/51 combined (Sprint 0 + 1). Sprint 0 conftest.py fix included.
- **Key decisions:** server-side `?status=Quote` filter + pagination replaces client-side filter; `estimate_sent=False` guard prevents duplicate estimates; `order_exists()` prevents status reset
- **Open:** I-013 â€” FTF API `status` field staging mismatch (order 1000276072: API=Quote, CRM=Checking). FTF developer to verify.
- **Carry forward:** FTF `service_type` returns `"Quote"` for all quote-stage orders â€” classifier cannot use this field. Must determine service from other order data.
- **Full brief:** [sprints/sprint_01_monitor.md](sprints/sprint_01_monitor.md)

---

## Business Rules â€” Confirmed by Robert (2026-05-25)

**Source:** Robert verbal Q&A sessions, Recordings 1 & 2, transcribed 2026-05-25.

### Service Type Name Mappings (Canonical)

| Informal / Customer Name | Canonical FTF Name | Notes |
|--------------------------|-------------------|-------|
| Topographic Survey (brand new, from scratch) | Topographic Boundary Survey | Full new survey |
| Topographic Survey (update / topo only) | Topo Survey / Topographic Survey / Update/Topographic Survey | Any of these three names |
| Construction Survey (design phase) | Topo Survey | Maps to Topo; stakeout/form board/foundation tie-in = during-construction sub-services |
| Permitting Survey | Boundary Survey (+ digital signature) | "Permitting" = 3rd-party digital signature requirement for county portal uploads |
| Special Purpose Survey | Specific Purpose Survey | Interchangeable; use "Specific Purpose Survey" as canonical |
| Land Survey Only | Boundary Survey ($350) | Staff nickname; confirmed as Boundary Survey |

### Services NGE DOES Perform

- Boundary Survey
- Topographic Survey / Topographic Boundary Survey
- Form Board Survey
- Spot Survey
- Foundation Tie-In Survey (aka Spot/Foundation)
- As-Built Survey
- Specific Purpose Survey / Special Purpose Survey
- Elevation Certificate
- Plot Plan
- Acreage, Elevation Only, Final Survey, Legal Description, Sketch and Description, Survey Re-draw, Surveyor's Affidavit, Tree Location, Update Survey (all in 24-service FTF list)

### Services NGE does NOT Do (Never Auto-Quote)

| Service | Reason |
|---------|--------|
| Engineering services / drainage design | NGE is a surveying company only â€” no engineers |
| Site Plans | Should be architects or engineers |
| Wetland Delineation | Needs specialist engineer; too complex for NGE |
| Building Stakeout | Ambiguous â€” NGE "dabbling" in it again; flag for human review (I-042) |

### Geographic Coverage Rules

- **Florida only** â€” all 67 FL counties can be quoted
- **Monroe County (Florida Keys):** flag for extra review, charge more, limited crew availability (I-034 already built)
- **Panhandle / northwest FL:** NGE struggles with crew coverage but still quotes â€” do not auto-reject
- **Vero Beach:** having issues but manageable â€” do not auto-reject
- **Strong coverage:** Jacksonville, St. Augustine, Orlando, South/Southeast/Southwest FL
- **Out-of-state:** flag immediately â€” NGE FL-only for Phase 1

### Pricing Decision Factors (How Robert Prices)

Robert (and Alan/Mark) weighs these factors when confirming a quoted price:

1. **Client sales history** â€” what price range that client has accepted before (e.g., Jean Cascio: $400â€“$700, mostly $400, last accepted $475)
2. **Property features** â€” pool, seawall, canal, right-of-ways; reviewed on GIS map before confirming
3. **Area / county / market** â€” geographic location affects competitive pricing
4. **Platted vs. unplatted** â€” affects survey complexity
5. **Scope of work** â€” exactly what the survey entails
6. **Competitive positioning** â€” where NGE sits vs. competitors for this client

Robert's summary: "Most of the time we're just looking at features, area, if we've done work with that client in the past and then what's the scope."

### Quoting Workflow (Summit's Role)

- Summit (internal) handles initial quotes: posts suggested prices in Teams â€” "Blue Invoicing" (standard) and "Yellow Invoicing" channels
- Robert / Alan / Mark review Summit's suggested price, confirm or adjust, THEN the quote is sent
- Robert checks GIS map visually before confirming every price
- Robert is NOT normally the one creating or importing orders in FTF

### Quote Expiry Rule (Confirmed Recording 02 â€” frame 0640)

- FTF portal auto-cancels any quote older than 60 days ("Quotes older than 60 days will be automatically moved to Cancelled")
- AI pipeline must prioritise sending within this window; Orchestrator (Sprint 9) must track quote age
- Tracked as I-049 for Sprint 6 Sender edge case logging

---

### Orders NGE Will NOT Quote (Hard Boundaries)

- Engineering or drainage design requests â€” auto-reject / flag (Naya Rodriguez example: rejected because she needed drainage/engineering, not surveying)
- Out-of-state properties
- Wetland Delineation

### Customer Approval Workflow (Most to Least Common)

1. Client pays invoice via payment link â†’ order auto-advances to "pending"
2. Client emails confirmation ("please proceed" / "we accept")
3. Client accepts via FTF portal
4. Phone call â€” Robert then asks for email follow-up

### Change Order Clause

- Currently NO change order language exists in estimates â€” this is entirely new (BRD Amendment 001)
- Communication process when scope changes: call/contact client first â†’ explain the scope change â†’ get verbal or email OK â†’ THEN add to invoice
- Change order additions must NEVER be auto-added without explicit client confirmation
- Ryan to draft the clause text (I-043); staging placeholder in `config/knowledge_base/change_order_clause.txt` exists but needs production sign-off

### Always-Human-Review Services (Management Level)

Robert confirmed ALL of the following always require human review before sending:
- ALTA Table A Survey
- B-II Title Review
- Wetland Delineation
- Lot Split
- Building Stakeout (until confirmed back in service â€” I-042)

### Pipeline Design Note â€” Suggest-Then-Approve (CRITICAL)

Robert stated he ALWAYS personally reviews every estimate before it goes to the client â€” even routine ones. The AI pipeline must be designed as:

> **AI suggests price + generates draft estimate â†’ routes to Robert/Mark for review â†’ they approve and send**

Auto-send (even for routine orders) is NOT acceptable per Robert's explicit instruction. This overrides any prior assumption that routine orders could bypass human review. Impact: Agents 4, 6, 7, 8, 9 design may need revision. Tracked as I-044. Discuss with Prateek and Ryan before Sprint 6.

---

## Business Rules â€” Confirmed by Ryan (2026-05-26 Call)

**Source:** Ryan-Prateek 45-minute call transcript, 2026-05-26.

### Refund Rule (Hard Stop â€” AI Never Touches)

- If any customer message or request contains refund intent â†’ **notify Jessica immediately â†’ AI stops, no further action**
- AI never processes, approves, or initiates any refund under any circumstances
- Same class of rule as NEVER_AUTO_QUOTE â€” codify in all AR-facing agent logic
- Tracked: I-063

### Human Review Phase Rule (Current Deployment)

Ryan: *"Right now, we would want to send everything for manual review...in that process we need to be able to teach it."*
- **Current phase**: ALL quotes go to Robert for review before anything is sent to client
- Not just flagged orders â€” every single order in the current phase
- Relaxes over time as confidence in AI accuracy builds
- This aligns with and reinforces I-044 / Robert's suggest-then-approve rule

### Robert Approval Flow â€” Hourly Batch Digest

Ryan: *"Send Robert a list every hour â€” links, job size, brief description, estimate total with Approve/Deny column â€” he can bulk-approve or pick specific ones."*
- Agent 4 (Human Gate) must output a **batched hourly digest**, not one Teams ping per order
- Each row: clickable FTF order link, job size/type, brief lot description, estimate reason, total, Approve/Deny
- Robert bulk-approves everything OR picks individual rows to deny/handle manually
- Note: "Bobby" appearing in prior docs was incorrect â€” reviewer is **Robert**
- Tracked: I-064

### Dynamic Pricing Complexity Factors (Ryan-Confirmed)

Ryan: *"Same half-acre with a pool, 30 walls, shed, two driveways = $700. Same half-acre plain house = $350."*

| Factor | Direction |
|--------|-----------|
| Swimming pool | Significant upcharge |
| Wall/corner count >8 | Proportional upcharge |
| Back patio | Moderate upcharge |
| Shed(s) | Per-shed upcharge |
| Multiple / looping driveways | Upcharge |
| Distance from nearest crew | Travel cost â†’ higher price |
| Remote area / no crew nearby | Charge more |

Near-future: crew schedule availability + job location relative to available crews â†’ pricing factor.
Robert to confirm factor weights before Sprint 4/5. Tracked: I-065.

### Quote â†’ Pending: Email Monitoring (New Agent)

Ryan: *"An agent should monitor info emails â€” any email that says 'convert'/'approved'/'go ahead' â€” read it, figure out what's being approved, move to pending, notify team."*
- Monitor email: **nesa@nexgenlogix.com**
- Trigger keywords: "approved", "convert", "go ahead", "move forward", "please proceed"
- On match: identify order from email content (address or order# preferred), move quote â†’ pending, notify team
- Sprint 5 agent. Tracked: I-061

### Website Chat â†’ Order Conversion

Ryan: *"If they go on website chat and say 'I want to move forward' â€” AI asks for address or order# â€” one of those â†’ converts to pending."*
- Customer initiates chat â†’ states intent to proceed
- AI must ask: "What is the property address or your order number?"
- If either provided â†’ convert quote â†’ pending
- If neither â†’ politely restate requirement; cannot proceed without one
- Sprint 6+. Tracked: I-062

### AI Knowledge Enrichment (Ongoing)

Ryan: *"Feed it the Florida standards for licensed surveyors. Create a persona of a high-performing licensed Florida surveyor."*
- Load Florida PSM Chapter 5J-17 FAC (Professional Surveyor and Mapper rules) into AI knowledge base
- AI answers client technical questions from two angles: (1) FL PSM standard answer, (2) NexGen-specific perspective
- Robert can describe jobs â†’ AI stores pricing rationale permanently (builds on prior sessions)
- Role-based: Jessica trains AR/refund rules; Robert trains pricing/logistics. Cross-domain requires both. Tracked: I-068, I-067, I-069.



---

## STANDING RULE - Miro board is a living artifact (2026-08-20)

User: *"always update the miro board (same) if anything is updated here. always recheck"*

- The board **FTF-AI invoicing estimator** (`uXjVHwLvWsU=`, Space *Land Solutions*
  `3458764680746478006`) is the canonical diagram of this pipeline.
- **Whenever pipeline behaviour changes** (an agent's logic, a cron schedule, a model, a
  status, a guardrail, a new integration), UPDATE THE SAME BOARD in the same turn.
  Do NOT create a second board - use `--rebuild-tech`.
- Then **RECHECK**: re-read the board via API and confirm counts, no items outside the
  frame, no overlapping boxes, client side intact, board still in the Space.
- Tool: `python scripts/miro_build_estimator_board.py --rebuild-tech uXjVHwLvWsU=`
  (`clear_tech` deletes only x<0 items, so the client frame is never touched).
- Miro has **no** screenshot/preview API (`picture` is null; `/preview` and `/thumbnail`
  are 404) and a headless browser cannot log in - so "recheck" means the geometry audit,
  not an image.

---

## INCIDENT - the agent asked the team the same question 5 times (2026-08-19)

Sumit: *"yeah it's asking repetitive questions Prateek. Should I stop replying to it?"*
Prateek: *"stop repliying. I will modify."*  <- we burned a colleague's trust. Do not repeat.

**What happened.** 17:08 -> 19:37, every 30-min watcher tick asked essentially the same
clarification about the #1000288500 cutoff, re-worded. Sumit answered 5 times. 11
clarifications and 13 contradictory guidance notes were written.

**Root causes (all mine, in teams_learning.py):**
1. `_INTERPRET_SYSTEM` ordered a clarification whenever an instruction would SKIP/EXCLUDE/
   REJECT billing. Every answer Sumit gave was about exclusion -> guaranteed infinite loop.
2. The interpreter payload contained only the open questions + new messages. It was NEVER
   shown what it had already learned or already asked -> amnesia every cycle.
3. `clarifs.append(...)` had no dedup and no cap.
4. Topic-key dedup alone would NOT have caught it: the re-asks drifted in wording
   ("what is the cutoff" -> "confirm the cutoff" -> "confirm permanently"). A per-question
   CAP is the only reliable backstop. Keep both.

**Fixes:** context (`already_learned`, `already_asked_clarifications`) in the payload;
"ASK ONCE, THEN COMMIT" prompt rule that treats re-asking as worse than acting on an
imperfect rule; topic-key dedup on learnings and clarifications; `_MAX_CLARIFY_PER_Q = 2`.

**LESSON - generalise this.** A self-learning loop needs a *termination* condition as much
as a learning condition. Any prompt of the form "if X, ask for confirmation" is an infinite
loop when the answers are themselves about X. Always pair it with: what have I already
asked, and what is my hard cap?

**Also fixed:** `_esc("&mdash;")` double-escaped into literal "&mdash;" in the chat table.
Escape the value, not your own entity: `_esc(v) or "&mdash;"`.

**Report cutoff (what the team actually wanted).** Sumit: *"I am trying to teach it to ignore
orders below 1000288500 in it's report so it can give fresh updates that I can answer daily"*.
Implemented as `REPORT_MIN_ORDER_NUMBER` (prod .env = 1000288500), applied in
`daily_report._below_report_cutoff` -> hides pre-cutoff orders from the "needs a price" /
"flagged" question lists ONLY. Report-side; A1..A6 untouched; those orders stay billable on
human approval; hidden count is always disclosed. Effect: 128 nags -> 1, 125 disclosed.

## INCIDENT 2026-08-19 (16:xx ET) — new orders stopped reaching the Approvals sheet

**Symptom (reported by Sumit):** "AI is not picking orders from FTF. It is stuck at 288592 but
FTF fresh order is at 288606."

**What was actually happening:** the pipeline never stopped. Cron fired every 5 min, A1 kept
finding flagged orders, A2 collected them, A3 priced them. Only the *last step* failed — writing
the row to the sheet:

```
ERROR [agent_a3_invoice_compiler] failed to write Excel row order=1000288593:
  Client error '400 Bad Request' for .../tables/ApprovalTable/rows/add
INFO  [agent_a3_invoice_compiler] invoice_compiler complete: {'posted': 1, 'errors': 0}
```

**Root cause:** someone typed in column **U**, just right of the table. Excel silently widened
`ApprovalTable` to 21 columns, auto-naming the new one `Column1` (it was empty — purely
accidental). Graph's `tables/rows/add` rejects the **entire** request unless the values array
width matches the table's column count exactly, so every append 400'd. 8 orders sat priced but
invisible for ~90 min.

**The much worse thing this uncovered.** `ensure_approval_sheet()` treated any column-count
difference as "schema mismatch — will recreate", and the recreate path
(`_setup_full_sheet_via_openpyxl`) starts with `del wb["Approvals"]` — it **deletes every order
row** and rebuilds the sheet header-only. That was firing every 5 minutes against a sheet holding
1,534 live orders. The *only* reason production data still existed was an unrelated `423 Locked`
because the team happened to have the file open in Excel. Closing Excel would have wiped the sheet.

**Fixes (all in this commit):**
1. `_setup_full_sheet_via_openpyxl` — hard guard: **refuse to recreate a sheet that holds data
   rows**, whatever the caller thinks. Last line of defence, independent of any caller's logic.
   Tested both ways: refuses on 1,534 rows, still sets up a genuinely empty sheet.
2. `ensure_approval_sheet` — extra *trailing* columns are now tolerated with a warning (the 20
   real headers are still present and in order, so the sheet is fine), instead of triggering a
   recreate.
3. `append_approval_row` — pads the row to the table's **actual** width via `_table_col_count()`,
   so a stray keystroke beside the table can never stop orders again.
4. `agent_a3_invoice_compiler` — the run summary said `posted: 1, errors: 0` **while the write was
   failing**. Now returns `_excel_write_failed` and counts it under `errors` +
   `excel_write_failed`. Silent mis-counting is why this went unnoticed for 90 minutes.

**Lessons.**
- A schema difference is never worth deleting the operators' data. Self-healing code needs a
  "refuse to destroy" floor, not just a "make it match" goal.
- Counters must tell the truth. A logged ERROR that still reports `errors: 0` is worse than no
  log at all — it defeats every downstream alert.
- `rows/add` is all-or-nothing on width. Never assume our schema constant equals the live table.
- The sheet is shared with humans; assume they will click, type and drag next to the table.

**Note on the sheet:** column U / `Column1` was left in place deliberately — no sheet edits were
made. It is harmless now. Removing it is a human action (Table Design > Resize Table).

## SAME DAY — every Claude vision call was silently running on GPT-4o

`call_with_image()` still did `message.content[0].text`. On Opus 5 (thinking by default)
`content[0]` is a `ThinkingBlock`, which has no `.text` → `AttributeError` → all 3 retries burned
→ `"Claude exhausted — falling back to OpenAI gpt-4o"` on **every** aerial-image analysis since
the Opus 5 switch (commit e8f92450). The text path `call()` had already been fixed via
`_extract_text()`; this second path was missed.

Fixed: `call_with_image` now uses `_extract_text()` and floors `max_tokens` for
think-by-default models, same as `call()`. The model check is now one shared helper
`_thinks_by_default()` so the two paths cannot drift apart again.

**Lesson:** when a response-shape assumption changes, grep for *every* place that unpacks the
response — `.content[0]` was the fingerprint, and one caller was left behind.

---

## INCIDENT 2026-08-24 (17:0x ET) — approved quotes never went out (watcher starved by the pipeline)

**Symptom (Prateek, Teams):** orders 288760–288764 had prices approved in the sheet but no quote
sent, for ~1 hour.

**Not the pipeline.** A1/A2/A3 were fine: all five were priced and their rows appended
(16:05–16:26 EDT, $400–$774). What never ran was the **approval watcher**, i.e. A4→A5→A6.

**Real cause — lock starvation.** The pipeline (`*/5`) and the watcher (`5,10,…,55`) share
`.pipeline.lock`. They fire on the *same minute*, and the pipeline entry sits **first in the
crontab**, so it wins the race every single time (logs: `pipeline run START 16:10:01` /
`watcher SKIP 16:10:02`, over and over). The watcher used `flock -n` → it gave up instantly and
skipped the whole 5–8 min pipeline run. Once every tick had work, the watcher never got in:
**68 minutes, zero approvals actioned, nobody told.** 69 nominal watcher "runs" today, last real
one 15:55.

**Fixed** (`scripts/run_server_watcher.sh` → prod `/home/ubuntu/ftf-invoicing-watch.sh`):
- `flock -n` → **`flock -w 240`**: wait for the lock instead of skipping. 240s < the 5-min tick,
  so at most one waiter exists at a time — waiters cannot pile up. The two now alternate.
- **Starvation alert**: `touch` a stamp on every real start; if a tick times out *and* no run has
  started in 45 min, send the existing failure email (throttled to one per hour). A starved
  watcher is otherwise completely invisible — same blind spot as 2026-08-19.

**Recovery:** ran the watcher manually → all 6 pending decisions actioned; 288760 ($600), 288761
($400), 288762 ($625), 288763 ($425), 288764 ($425) invoiced in FTF and delivered with
`pay_link=yes`; 288759 recorded as rejected. Sheet: 1677 rows, 0 duplicates, all 6 stamped.

**Lesson:** two cron jobs on the same lock and the same minute is not a race — it is a fixed
priority order. `flock -n` on the *lower*-priority-by-accident job means it may never run at all.
Also: a job that logs "SKIP" 101 times is not healthy, and nothing was counting that.

### Same day — the learning loop was memorising the conversation, not the orders

Prateek: *"ai should only know about the orders and its related details. it's repeating every
single word what's spoken in the chat."* The interpreter was paraphrasing every message back as a
durable rule. `user_guidance` — which **A3 injects into its pricing prompt as
[OPERATOR GUIDANCE]** — had collected notes like *"When Prateek says to close the sheet, stop
reading and writing to the master sheet and pause updates"* and *"Orders 1000288760 through
1000288764 had approved prices with quotes not sent; keep them tracked as pending quote-send"*.

Fixed in `teams_learning.py`:
- Prompt now states **what may be learned** (a price, rate, discount, negotiated client rate,
  service type/tier, how to handle a specific order/client, billing scope) and what may **never**
  be (bug reports, status/list requests, transient state, anything about the agent's own
  operation, messages aimed at another person, chit-chat).
- Two deterministic backstops, because a prompt rule is not a guarantee:
  `_SELF_OP` (refuses self-operation instructions — chat is **not** a control channel) and
  `_TRANSIENT` (refuses time-bound state as a durable rule).
- **Scope gate**: only `pricing`/`queue` learnings reach `user_guidance`; `process`/`other` are
  remembered for the audit trail but stay out of the prompt that decides what a client is charged.
- `scripts/purge_nonorder_learnings.py` cleaned the existing pollution: `user_guidance`
  199→190 (9 of 10 chat notes dropped; the #1000288500 cutoff rule kept), `teams_learnings`
  22→12. Backed up first; rules/order_overrides/observations untouched.

**Lesson:** the first `_SELF_OP` I wrote used a 70-char window over loose words and flagged a
*real* billing rule (*"…should be rejected/skipped … so they stop appearing as flagged in future
runs"*). A filter that protects the pricing prompt can also silently delete the knowledge it
exists to keep — so both regexes are now tested in **both** directions (18 fixtures, must-drop and
must-keep) before deploying.

**Not a defect (checked):** col-A hyperlinks were missing on rows 1639+. Cause is the known
`423 Locked` — `ensure_action_dropdown` needs a whole-workbook upload and the team keeps the file
open in Excel. It self-heals the moment the file closes: the 17:20:33 upload restored 1677 of 1678.

---

## 2026-08-27 — the AI's invoice email had no amount and no "View Invoice" link

**Report:** *"client is not receiving the invoices through emails just like before when it's
getting approved from the excel sheet."*

**Ruled out first (all measured, not assumed):** every approval was actioned (only 286745 stuck,
known); FTF logged all 1,437 nesa emails as `delivered`; and **open rates matched humans exactly
— nesa 29% vs human 30%** over 3 days, so the mail was genuinely landing in real inboxes. A
systematic non-delivery was therefore ruled out before touching anything.

**What was actually wrong.** Diffing an AI email against a human email for the *same* order
(288880) showed the AI body was ~490 chars shorter and missing:
- **`Invoice Amount: $3350.00`** — the email never stated a price
- **`For more details, please find the invoice: View Invoice`** — no link to the PDF
- the CITY,STATE,ZIP line
- and the subject was wrong on Quote-stage orders: ours *"Your Quote is ready to review"* vs
  FTF's *"Your NexGen Quote is Ready"*.

Cause: `A6 → /order/deliver_invoice` passes `message=`, and FTF uses our text **verbatim** as the
body. `_build_invoice_message()` hand-rebuilt only part of FTF's block. Same root cause as the
Pay Now bug (23471565) — that fix restored one missing line and stopped there. A client opening
it saw a delivery email with no price and nothing to click: "I didn't get the invoice."

**Fixed** (`ftf_portal_client.py`): the order page already renders exactly what a human sends —
`<input id="mail_subject">` and `<textarea id="deliver-message">` (HTML-escaped, contains the
Pay Now token we were already scraping). `_scrape_delivery_extras()` now also returns FTF's
pre-filled **subject, body and address**, and the send uses them **verbatim**. Preference order:
FTF's pre-fill → the locally built block (Pay Now only) → `_DEFAULT_MSG`; `_prefill_usable()`
requires both "Pay Now" and "View Invoice" before trusting a scrape, and every step degrades
quietly so a scrape miss can never fail or delay a send.

**Lesson:** don't reconstruct another system's template — take it. Twice now we shipped a partial
copy of FTF's body and twice a client-visible piece went missing. The template lives on the
order page; scraping it means an FTF wording change follows automatically.

**Found, left for a human:** order 286745's FTF page pre-fills `dipat53889@aratrin.com` (a
disposable address, at NexGen's own office address) while `ng_email` is empty — it is a test
order. A6 has retried it ~1,900 times since 14 July. Deliberately did NOT add a
"fall back to FTF's pre-filled recipient" rule: that would have started mailing an address
nobody asked us to mail.

### Same day — Teams is now one-way

Prateek: *"stop learning from Sumit or anyone who posts on MS teams. Just keep sending the
reports."* `TEAMS_LEARNING_ENABLED` now defaults to **0** (plus an explicit `.env` entry), and the
`7,37` teams-watch cron entry is removed. The report no longer calls `_ingest_chat_answers()`,
`_build_chat_learning_html()` or `_build_questions_html()` — it never asks the team anything.
Report also simplified: dropped the "What I learned", "Questions for you" and "Numbers" blocks,
leaving title → TL;DR → my thinking → please help with → what I did → sheet link. 3,998 → 2,083
chars. The pipeline/watcher crons are untouched.

## 2026-09-04 — "Client received the quote email, no quote in order" (289283, 289284)

Kim reported both orders in Teams. The pipeline had done everything right — priced, posted,
Sumit approved at 17:14, invoices 365586/365585 created in FTF at 17:16, emails delivered at
17:19. What went wrong was the *body*: it had the Pay Now link but **no "Invoice Amount: $X"
line and no "View Invoice" link**, so the client got a quote email with no price and no
document. Sumit re-sent both by hand the next morning (13:01, 13:09).

**Real cause.** FTF pre-fills the delivery body on the order page and we send it verbatim (the
2026-08-27 fix). But FTF only includes the amount + View Invoice block once
`ng_orders.ng_due_amount` is populated, and that lags invoice creation by minutes-to-hours (it
was still 0 at send time for order 289161 two days later). A6 scrapes ~3s after generating the
PDF, so on **~55% of sends** `_prefill_usable()` was False and we fell back to
`_build_invoice_message()` — which only ever produced the Pay Now block. Measured from
`ng_email_delivered`: of 510 nesa emails since 08-20, **394 had no amount and no invoice link**
(100% before 08-27, ~55% after).

The 08-27 fix was right in direction and incomplete in fact: it made the *good* path perfect and
left the fallback shipping a priceless email, and nothing measured which path actually ran.

**Fixes.**
1. `_build_invoice_message()` now builds the full block itself — `Invoice Amount: $X` from the
   **human-approved total** (`invoice_draft.total_amount`, more authoritative than FTF's lagging
   `ng_due_amount`) plus the deterministic `repos/{order}/invoice/...pdf` View Invoice link. A6
   passes `invoice_total`. Both paths now always carry price + link.
2. FTF's scraped **subject and address are now adopted even when the body is unusable** (they
   come from separate, reliable inputs) so the fallback's subject matches a human send.
3. `scripts/audit_sent_invoices.py` — post-send audit. Reads FTF's own `ng_email_delivered` and
   flags any nesa email missing Pay Now / Invoice Amount / View Invoice. Wired into the watcher
   (`--hours 2 --alert`), read-only, never re-sends, exit code ignored so it can't fail a good run.

**Lessons.**
- A 200 from the deliver endpoint is not proof the email was worth sending. Verify the artefact
  that reached the client, not the call that produced it.
- When a fallback path exists, measure how often it runs. This one ran on half of all sends for
  eight days and the only signal was a WARNING nobody counted.
- Don't build content out of a field another system populates asynchronously. Use the number the
  human approved — we own it and it's correct at send time.
- Near-miss during this fix: `invoice_draft` is a JSON *string* in the state store; my first
  version called `.get()` on it, which would have crashed A6 on every order. A5 already had the
  `json.loads if isinstance(str)` guard — copy the proven pattern instead of assuming the type.
