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

---

## [Sprint 4] — Estimate Writer — 2026-05-26

### Added
- `code/sprint_04_writer/agents/agent_06_writer.py` — Agent 6: write_estimate() generates personalized estimate email via Claude. Warm/friendly tone for individual clients; concise/professional for B2B. Injects change order clause as unmodifiable final section. `correction_note` param enables Reviewer retry loop.
- `code/shared/config/knowledge_base/change_order_clause.txt` — Change order clause draft (Ryan reviews before Sprint 6 go-live per I-043)
- `code/shared/config/prompts/estimate_writer.txt` — Writer system prompt with tone rules, structure requirements, clause append instruction
- `code/sprint_04_writer/tests/` — 13 unit tests (all passing)

### Fixed (shared infrastructure)
- `code/shared/core/db.py` — added `draft_estimate` to `_VALID_ORDER_COLUMNS`; added `get_ready_to_write_order()` (picks up 'priced' OR 'approved' orders); added `get_written_order()`
- `db/schema.sql` — added `draft_estimate TEXT` column to `processed_orders`

---

## [Sprint 5] — Estimate Reviewer — 2026-05-26

### Added
- `code/sprint_05_reviewer/agents/agent_07_reviewer.py` — Agent 7: review_estimate() runs 4 deterministic checks (price, customer name, property address, change order clause). On failure, calls write_estimate(correction_note=) for rewrite (up to MAX_REVIEWER_RETRIES=3). After 3 failures raises ReviewerFailError and re-flags order for Human Gate.
- `code/shared/config/prompts/estimate_reviewer.txt` — Reviewer LLM prompt (available for future LLM-based enrichment; Sprint 5 uses deterministic string checks)
- `code/sprint_05_reviewer/tests/` — 16 unit tests: 6 pure `_run_checks` tests + 10 integration tests (all passing)

### Architecture
- Sprints 4+5 built simultaneously (no mutual dependency — Sprint 4 output structure was known before build)
- Reviewer imports write_estimate at module level (required for pytest.patch to work correctly)
- Deterministic checks chosen over LLM validation for 4 factual accuracy checks — faster, cheaper, no hallucination risk

### Full Test Suite
- Sprints 1–5: **125 tests, 125 pass** (0 fail, 0 skip)

---

## [Sprint 6] — Sender + Reporter — 2026-05-26

### Added
- `code/sprint_06_sender_reporter/agents/agent_08_sender.py` — Agent 8: send_estimate() applies random 6–13 min delay, creates FTF invoice, sends it, marks estimate_sent on order, updates DB to `status='sent'`
- `code/sprint_06_sender_reporter/agents/agent_09_reporter.py` — Agent 9: queries daily stats, builds Teams MessageCard (5 facts), POSTs to TEAMS_WEBHOOK_URL. Fully deterministic — no LLM needed for stats digest
- `code/shared/config/prompts/reporter.txt` — Reporter prompt stub (available for future LLM narrative enrichment; Sprint 6 uses deterministic template)
- `code/sprint_06_sender_reporter/tests/` — 13 unit tests (8 sender + 5 reporter), all passing

### Fixed (shared infrastructure)
- `code/shared/core/db.py` — added `get_reviewed_order()` (picks up `status='reviewed'` orders for Sender); added `get_daily_summary()` (single-query daily stats using PostgreSQL FILTER aggregates)

### Architecture
- Split original combined `agent_09_sender_reporter.py` README design into two files per "one agent, one job" rule
- Sender uses `time.sleep()` at module level (patchable via `patch("agents.agent_08_sender.time.sleep")`)
- Reporter is deterministic — no REPORTER_MODEL LLM call this sprint; prompt stub reserved for Sprint 9+ enrichment

### Full Test Suite
- Sprints 1–6: **138 tests, 138 pass** (0 fail, 0 skip)

---

## [Sprint 6 — I-024 Fix] — Agent 8 Send Window + Retry Logic — 2026-05-26

### Fixed
- `code/sprint_06_sender_reporter/agents/agent_08_sender.py` — I-024: added `_in_send_window()` (8 AM–6 PM ET via `zoneinfo`); `_create_and_send_invoice()` retry wrapper with `MAX_SENDER_RETRIES` attempts; `status="error"` saved after exhausting all retries; `send_estimate()` returns `None` when called outside send window so Orchestrator reschedules
- `code/shared/config/settings.py` — added `MAX_SENDER_RETRIES` (default 3), `SEND_HOUR_START` (8), `SEND_HOUR_END` (18), all env-configurable

### Fixed (documentation)
- `docs/recording_01_ai_quoting_review_guidelines.md` — corrected issue ID references (I-040→I-041, I-041→I-042, I-042→I-043); updated item 14 to reflect I-044 closure
- `issues/issue.md` — logged I-045 through I-049 from Recording 02 open questions Q1–Q4, Q12 (service type list, order statuses, county pricing matrix, Smith Zone, 60-day SLA)
- `memory.md` — added 60-day quote auto-cancel rule (confirmed Recording 02, frame 0640)

### Tests
- `code/sprint_06_sender_reporter/tests/test_sender.py` — 3 new I-024 tests added (outside window → None; transient retry → success; max retries → error); all 8 existing tests updated with `_in_send_window=True` patch for time-independence
- Sprints 1–6: **141 tests, 141 pass** (0 fail, 0 skip)

## [Sprint 2 — I-050/I-051/I-052/I-053 Fixes] — Classifier Hardening — 2026-05-26

### Fixed
- `code/sprint_02_classifier_pricing/agents/agent_03_classifier.py` — I-050: `property_state` normalization — "FLORIDA"/"Florida" → "FL" before out-of-state and lat-bounds checks; I-053: `_normalize_service_type()` added — alias map (15 Robert-confirmed informal→canonical mappings) + `_llm_normalize_service_type()` LLM fallback for truly unrecognized types; `_UNRECOGNIZED` sentinel flags unclassifiable orders for human review
- `code/shared/config/prompts/classifier.txt` — I-053: rewritten from STUB to ACTIVE system prompt; 24 canonical names + Robert-confirmed mappings; used by `_llm_normalize_service_type()` as last-resort LLM call
- `code/shared/config/flag_triggers.py` — I-052: `"Building Stake Out"` added to `ALWAYS_FLAG_SERVICES` (I-042 mandated; remove when Robert confirms back in service)
- `code/sprint_02_classifier_pricing/tests/test_classifier.py` — 9 new tests: I-050 state normalization (3), I-053 alias + LLM fallback (6)

### Issues Closed
- I-050 (CRITICAL) — property_state FLORIDA/FL normalization bug
- I-051 (CRITICAL) — non-standard service types crashing Pricing Engine
- I-052 (MAJOR) — Building Stakeout not flagged
- I-053 (MAJOR) — LLM classifier never enabled
- I-056 (MAJOR) — Teams approval buttons (design decision: AI asks approve/reject in chat; no buttons needed)

### Full Test Suite
- Sprints 1–6: **150 tests, 150 pass** (0 fail, 0 skip)

<!-- Sprint entries added here as sprints are completed -->
