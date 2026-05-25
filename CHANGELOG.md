# Changelog — FTF Agentic AI OS

All notable changes are documented here. Updated after every sprint release.

Format: `## [Sprint N] — Sprint Name — YYYY-MM-DD`

---

## [Pre-Build] — Team Framework & Documentation — 2026-05-20

### Added
- `TEAM/dev/` — Developer team structure (Manager, Senior, Junior personas, CODE_STANDARDS, PR_CHECKLIST, ONBOARDING, developer_review log)
- `TEAM/qa/` — QA team structure (Manager, Senior, Junior personas, QA_CHECKLIST, DEFINITION_OF_DONE, QA_learning log, test case template)
- `code/` — Sprint code isolation skeleton (13 sprint folders + shared/ infrastructure)
- `issues/issue.md` — Issue tracker with full status lifecycle
- `docs/decisions/ADR_template.md` — Architecture Decision Record template
- `CHANGELOG.md` — This file

### Documentation Complete (pre-build)
- Business Requirements Document v2
- Technical Architecture (17-agent diagram)
- 14-sprint delivery plan
- All dependency questions distributed to stakeholders

---

## [Sprint 0] — Foundation — 2026-05-21

### Added
- `code/shared/core/` — 5 core clients: ftf_client, claude_client, fema_client, db, logger
- `code/shared/config/settings.py`, `models.py`, `flag_triggers.py`
- `db/schema.sql` — full PostgreSQL schema applied to `ftf_agentic_ai` database
- `scripts/test_connections.py` — Sprint 0 verification script (6 checks, 6 PASS)
- `.github/workflows/` — CI/CD pipeline with all 6 secrets configured at repo level
- `sprints/sprint_00_foundation.md` — Sprint 0 complete with Stakeholder Testing section

### Architecture
- Stakeholder AI Agent layer added to team architecture (Tier 0.5)
- `TEAM/stakeholders/` — 7 new files: STAKEHOLDERS_OVERVIEW.md + 6 AI agent role cards
- `TEAM/TEAM_OVERVIEW.md` — Updated with Tier 0 (Human Principals) and Tier 0.5 (Stakeholder AI Agents)
- `TEAM/dev/agents/dev_manager.md` — Added Stakeholder AI Consultation Rule
- `TEAM/qa/agents/qa_manager.md` — Added Stakeholder AI check to release gate
- `docs/stakeholder_testing.md` — Added AI Agent First rule at top
- Escalation chain updated: Junior → Senior → Manager → Prateek AI → Real Prateek → Ryan AI/Wyatt AI → Real Ryan/Wyatt

### Fixed
- FTF API `get_orders()` — unwraps `{"count","data"}` envelope correctly
- FTF API `get_pricing()` — requires `service` param, valid tier default (`individual`)
- FEMA flood zone check — downgraded to WARN (corporate firewall blocks hazards.fema.gov; passes on GitHub Actions)
- Windows cp1252 encoding — replaced all Unicode symbols with ASCII in test script

## [Research] — Competitor Analyst + I-001/I-002 Resolution — 2026-05-25

### Added
- `TEAM/research/competitor_analyst.md` — Competitor Analyst AI agent (Tier 2 research specialist, ACTIVE). WebSearch + WebFetch enabled. Consulted by Dev Manager, Prompt Engineer, QA Manager, Senior Dev, BA for competitor detection and flag trigger questions.
- `TEAM/research/competitive_analysis.md` — Full Florida competitive analysis: NexGen vs. 8 Florida surveying competitors (GT Surveys, Apex Surveying, Land Surveying Palm Beach, Accurate Land Surveyors, Suarez Surveying, Stoner & Associates, SurvTech Solutions, No Flood Florida). Includes service comparison matrix, pricing benchmarks, 16 improvement suggestions (P1/P2/P3).
- `TEAM/TEAM_OVERVIEW.md` — Competitor Analyst added as role #10 in Tier 2; team count updated to 23 AI roles.

### Fixed
- `code/shared/config/flag_triggers.py` — `COMPETITOR_NAMES` populated (25 entries), `COMPETITOR_DOMAINS` populated (16 entries), `NEVER_AUTO_QUOTE` populated (3 entries: Specific Purpose Survey, Lot Split, Wetland Delineation). All bootstrapped from web research — Robert/Mark to validate before Sprint 3.
- `issues/issue.md` — I-001 and I-002 moved from OPEN to CLOSED (bootstrapped resolution; validation pending from Robert/Mark).
- `memory.md` — Open Dependencies updated; 2 new files added to Workspace Files Index.

---

## [Sprint 1] — CRM Monitor — 2026-05-21 (In Progress)

### Added
- `code/sprint_01_monitor/agents/agent_02_monitor.py` — Agent 2: polls FTF API, detects new orders, saves to `processed_orders` with `status="pending"`
- `code/sprint_01_monitor/tests/conftest.py` — test path setup
- `code/sprint_01_monitor/tests/test_monitor.py` — 7 unit tests (all pass)
- `TEAM/qa/test_cases/sprint_01_test_cases.md` — full QA test case suite (unit + integration + edge cases)
- `docs/decisions/ADR_001` through `ADR_007` — 7 Architecture Decision Records documenting all Sprint 0 foundational decisions

### Fixed (post Sprint 0 review)
- `code/shared/core/db.py` — added `order_exists(order_id: str) -> bool` (sprint plan had wrong function reference)
- `code/shared/core/state.py` — replaced deprecated `datetime.utcnow()` with `datetime.now(UTC)` (4 occurrences)
- `code/sprint_00_foundation/tests/test_ftf_client.py` — fixed `get_pricing()` called without required `service` arg
- `issues/issue.md` — logged 8 open dependency issues (I-001 through I-008) + 3 closed fixes (I-009 through I-011)

---

## [Sprint 2] — Classifier + Pricing Engine — 2026-05-25

### Added
- `code/sprint_02_classifier_pricing/agents/agent_03_classifier.py` — Agent 3: classify_order() with 11 flag triggers (ALWAYS_FLAG, NEVER_AUTO_QUOTE, competitor name/domain, unresolved Quote, out-of-state, Monroe County, missing county I-036, false FL lat I-037, VE coastal zone I-035, FEMA unavailable)
- `code/sprint_02_classifier_pricing/agents/agent_05_pricing_engine.py` — Agent 5: price_order() with FTF API pricing, b2b/individual tier, special_pricing overrides, elevation cert add-on
- `code/shared/config/prompts/classifier.txt` — LLM prompt stub (disabled Sprint 2; enriched after Robert/Mark recordings Sprint 3)
- `code/sprint_02_classifier_pricing/tests/` — 43 unit tests (27 classifier + 16 pricing engine)

### Fixed
- `code/shared/core/db.py` — I-029: append-only guard for agent_decision_log (dedup within 30s window)
- `code/sprint_00_foundation/tests/test_db.py` — updated test_log_decision_inserts_row to expect SELECT+INSERT (I-029 guard)

---

## [Sprint 3] — Human Gate — 2026-05-25

### Added
- `code/sprint_03_human_gate/agents/agent_04_human_gate.py` — Agent 4: notify_human() (Teams POST + DB state), check_approval() (DB-polling stub pending I-025), run()
- `code/sprint_03_human_gate/tests/` — 13 unit tests covering Teams notification, approval polling, error handling, payload structure
- `code/shared/core/db.py` — get_flagged_order(), get_order_by_id() helpers

### Fixed (Agent 3 enhancements)
- `code/sprint_02_classifier_pricing/agents/agent_03_classifier.py` — 4 new flag triggers: competitor company name (Trigger 3), competitor email domain (Trigger 4), out-of-state property (Trigger 9), Monroe County I-034
- `code/sprint_02_classifier_pricing/tests/test_classifier.py` — 12 new tests for new triggers; I-037 test updated to reflect Trigger 9 coexistence
- `db/schema.sql` — status values expanded: awaiting_approval, approved, rejected

### Process
- `memory.md` + `TEAM/dev/CODE_STANDARDS.md` — permanent pre-sprint independence check rule added (mandatory for every sprint, everywhere, always)

### Blocked (carry to Sprint 4)
- I-025: approval inbound mechanism undefined (Teams button? webhook callback? manual DB?)
- I-038: Robert/Mark competitor list validation pending

<!-- Sprint entries added here as sprints are completed -->
