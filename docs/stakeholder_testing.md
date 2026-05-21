# Stakeholder Testing — FTF Agentic AI OS

> Who tests what, and when. Updated as sprints complete.
> Human stakeholders only — AI agents (Dev, QA team) test internally before any human sees output.

## AI Agent First — Rule

Before contacting any real human stakeholder, the team must consult the corresponding Stakeholder AI agent:

| Real Human | AI Agent Card | Consult For |
|------------|---------------|-------------|
| Prateek | `TEAM/stakeholders/prateek.md` | Architecture, code standards, ADR, model selection |
| Ryan | `TEAM/stakeholders/ryan.md` | Estimate tone, business rule, output quality |
| Robert | `TEAM/stakeholders/robert.md` | Service classification, flag logic, estimate correctness |
| Mark | `TEAM/stakeholders/mark.md` | Edge cases, unusual property, out-of-state orders |
| Jessica | `TEAM/stakeholders/jessica.md` | Reminder tiers, escalation threshold, exclusion list |
| Wyatt | `TEAM/stakeholders/wyatt.md` | Statement format, B2B delivery, Teams notification |

**Rule:** The real human is only contacted when the AI agent cannot answer confidently, or for explicit milestone sign-offs listed in this document. See `TEAM/stakeholders/STAKEHOLDERS_OVERVIEW.md` for full consultation rules.

---

---

## Quick Reference — Who Tests Which Sprint

| Sprint | What Gets Built | Prateek | Ryan | Robert / Mark | Jessica | Wyatt |
|--------|----------------|---------|------|---------------|---------|-------|
| Sprint 0 — Foundation | Infrastructure, DB, API connections | YES | — | — | — | — |
| Sprint 1 — Monitor | Agent 2: detects new FTF orders | YES | — | YES | — | — |
| Sprint 2 — Classifier + Pricing | Agent 3 + 5: classify service, price order | YES | — | YES | — | — |
| Sprint 3 — Human Gate | Agent 4: 9 flag triggers, Teams alerts | YES | YES | YES | — | — |
| Sprint 4 — Writer | Agent 6: estimate email + change order clause | YES | YES | Optional | — | — |
| Sprint 5 — Reviewer | Agent 7: self-correction loop | YES | — | — | — | — |
| Sprint 6 — Sender + Reporter ⭐ | Agents 8+9: first full estimate sent | YES | YES ⭐ | YES | Optional | — |
| Sprint 7 — AR Follow-Up | Agents 10–14: payment reminders | YES | YES | — | YES | — |
| Sprint 8 — Monthly Statements | Agents 15–17: Excel + PDF delivery | YES | YES | — | YES | YES |
| Sprint 9 — Memory Loop | Internal AI memory system | YES | — | — | — | — |
| Sprint 10 — Full Staging ⭐ | All 3 loops on staging, cost report | YES | YES ⭐ | YES ⭐ | YES ⭐ | YES ⭐ |
| Sprint 11 — Limited Production ⭐ | First 5 real estimates live | YES | YES ⭐ | YES ⭐ | — | — |
| Sprint 12 — Full Production ⭐ | All 3 loops 24/7, 30-day monitor | YES | YES ⭐ | YES | YES | YES |

⭐ = Required milestone sign-off — sprint cannot advance without this person's approval.

---

## Per-Person Summary

### Prateek — CTO
Involved in every sprint. Technical owner. Signs off on all builds before business stakeholders see anything.

| Sprint | What Prateek Tests |
|--------|--------------------|
| 0 | All 7 connection checks, DB schema, CI YAML |
| 1 | Unit tests, DB rows, integration test |
| 2 | Unit tests, FEMA integration, pricing accuracy |
| 3 | All 9 flag triggers, Teams webhook delivery |
| 4 | Unit tests, clause present and unmodified |
| 5 | Retry loop, ReviewerFailError escalation |
| 6 | Full chain integration test, delay, FTF CRM sync |
| 7 | All 5 reminder tiers, exclusion list, DB logging |
| 8 | Excel/PDF output, completeness, delivery |
| 9 | Nightly log, correction patterns, reflection.md |
| 10 | All 3 loops simultaneous, cost benchmark |
| 11 | System health monitoring, first 5 estimates |
| 12 | All 3 loops live, UptimeRobot, 30-day monitoring |

---

### Ryan — Decision Maker
First sees output at Sprint 3 (alert format). Required sign-off at Sprints 6, 10, 11, 12.

| Sprint | What Ryan Tests / Approves |
|--------|---------------------------|
| 3 | Teams alert format — contains enough info to make a decision |
| 4 | Sample estimate tone, professionalism, change order clause wording |
| 6 ⭐ | Opens test estimate in inbox — confirms professional and correct → GO for Sprint 7 |
| 7 | 90-day escalation alert format on Teams |
| 8 | Teams notification format for statement delivery |
| 10 ⭐ | Attends full system demo; approves monthly AI cost; signs GO/NO-GO for Sprint 11 |
| 11 ⭐ | Receives Robert/Mark sign-off on first 5 real estimates → signs GO/NO-GO for Sprint 12 |
| 12 ⭐ | Monitors daily digest for 30 days → final Phase 1 sign-off |

---

### Robert / Mark — Operations SMEs
First involved at Sprint 1. Provide ground-truth on what correct FTF operations look like.

| Sprint | What Robert / Mark Test |
|--------|------------------------|
| 1 | Correct orders detected — no missed orders, no false positives |
| 2 | Service classification correct; pricing amounts match expectations |
| 3 | Flag logic correct — normal orders not flagged; ALTA/Other Services/competitors always flagged |
| 4 | Estimate content matches FTF standards (optional — if Ryan requests) |
| 6 ⭐ | Confirm estimate content and format match FTF standards |
| 10 ⭐ | Test all 10+ order types; validate classification, pricing, flagging |
| 11 ⭐ | Read first 5 real estimates sent to real customers — report issues within 24 hours |
| 12 | Continue monitoring estimates as normal operations; flag edge cases |

**Pending from Robert / Mark (blocks Sprints 2–3):**
- Competitor company names + domains list
- Never-auto-quote service list
- Exact FTF names for Construction + Permitting surveys
- Recordings 1–8 (estimate generation process)

---

### Jessica — AR Lead
First involved at Sprint 7. Owns the AR reminder process.

| Sprint | What Jessica Tests |
|--------|--------------------|
| 6 | Reviews daily Teams digest format (optional) |
| 7 | Reads all 5 reminder tones — confirms language matches her manual process; approves escalation format; approves exclusion list logic |
| 8 | Confirms statement content matches what she manually prepares; verifies all B2B clients included |
| 10 ⭐ | Tests AR reminders on staging — correct tones, correct timing |
| 12 | Confirms AR reminders are replacing her manual process correctly |

**Pending from Jessica (blocks Sprint 7):**
- Recording 10: AR follow-up process walkthrough
- Reminder schedule confirmation + escalation threshold (90 days?)
- Client exclusion list for AR reminders

---

### Wyatt — Oversight / Leadership
First involved at Sprint 8. Approves monthly statement format.

| Sprint | What Wyatt Tests / Approves |
|--------|-----------------------------|
| 8 | Approves statement format and delivery method — confirms it meets B2B client expectations |
| 10 ⭐ | Tests monthly statement on staging — confirms format and delivery |
| 12 | Monitors monthly statement delivery for 30 days |

**Pending from Wyatt (blocks Sprint 8):**
- Recording 11: monthly statement process walkthrough
- Monthly statement format confirmation

---

## AI Agent Team (Not Human Stakeholders)

The following are AI agent roles — not humans. They test internally before any human reviews output:

| Role | Agent | When Active |
|------|-------|-------------|
| Dev Manager | AI | Every sprint — spawns Senior Dev / Junior Dev |
| Senior Dev | AI | Every sprint — complex logic, integration, first-pass review |
| Junior Dev | AI | Every sprint — well-defined tasks |
| QA Manager | AI | Every sprint — final sign-off, release gate |
| Senior QA | AI | Every sprint — edge cases, security, test case authoring |
| Junior QA | AI | Every sprint — happy path, basic functional |
| QE Manual | AI | Every sprint — exploratory testing, UX of human-facing outputs |
| QE Automation | AI | Every sprint — automated regression suite |

Human stakeholders only see output **after** the full AI dev + QA cycle has passed.
