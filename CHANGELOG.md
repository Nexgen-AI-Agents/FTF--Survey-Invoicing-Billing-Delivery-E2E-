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

<!-- Sprint entries added here as sprints are completed -->
