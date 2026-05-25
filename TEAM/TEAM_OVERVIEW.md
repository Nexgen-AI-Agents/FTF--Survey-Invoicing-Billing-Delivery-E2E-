# FTF Agentic AI OS — Full Team Overview

> **23 AI roles across 6 tiers + 6 human principals with parallel AI agent representations.**
> Every role has a dedicated role card with persona, responsibilities, model selection, escalation path, and reading protocol.
> This document is the single reference for who does what and how the team works together.

---

## Human Principals (Tier 0) — Real Humans, Milestone Sign-Offs Only

| Person | Role | Human Role Card | AI Agent Card |
|--------|------|-----------------|---------------|
| Prateek | CTO | `TEAM/leadership/prateek_cto.md` | `TEAM/stakeholders/prateek.md` |
| Ryan | Decision Maker (FTF) | `TEAM/leadership/ryan_wyatt.md` | `TEAM/stakeholders/ryan.md` |
| Wyatt | Oversight & Leadership | `TEAM/leadership/ryan_wyatt.md` | `TEAM/stakeholders/wyatt.md` |
| Robert | Operations SME | `TEAM/sme/robert.md` | `TEAM/stakeholders/robert.md` |
| Mark | Field Ops SME | `TEAM/sme/mark.md` | `TEAM/stakeholders/mark.md` |
| Jessica | AR Lead | `TEAM/ar/jessica_ar_specialist.md` | `TEAM/stakeholders/jessica.md` |

> Human role cards describe their business role. AI agent cards (`TEAM/stakeholders/`) are the always-available consultation layer. **Always consult the AI agent first — only ping the real human if the AI agent cannot answer.**

---

## Stakeholder AI Agents (Tier 0.5) — Always Available

| Agent | Status | Consulted For | Enriched From |
|-------|--------|---------------|---------------|
| Prateek AI | **ACTIVE** | Architecture, code standards, ADR decisions, model selection | CLAUDE.md, memory.md, learnings.md, ADRs |
| Ryan AI | STUB | Estimate tone, business rules, output quality | Sprint 6 demo feedback |
| Robert AI | STUB | Service classification, flag trigger logic, estimate correctness | Recordings 1–8 |
| Mark AI | STUB | Edge case classification, unusual properties, out-of-state | Recordings 1–8 |
| Jessica AI | STUB | Reminder tiers, escalation threshold, exclusion list | Recording 10 |
| Wyatt AI | STUB | Statement format, B2B delivery, Teams notification content | Recording 11 |

> See `TEAM/stakeholders/STAKEHOLDERS_OVERVIEW.md` for consultation rules, STUB vs. ACTIVE explanation, and enrichment process.

---

## Complete Team Roster

| # | Name / Role | Folder | One-Line Responsibility |
|---|-------------|--------|------------------------|
| 1 | Prateek — CTO | `TEAM/leadership/prateek_cto.md` | Final technical authority — architecture, escalations, production sign-off |
| 2 | Ryan & Wyatt — Leadership | `TEAM/leadership/ryan_wyatt.md` | Business approval authority — estimates, statements, go-live sign-off |
| 3 | Product Owner | `TEAM/leadership/product_owner.md` | Product vision, backlog priority, sprint readiness gates |
| 4 | Project Manager | `TEAM/leadership/project_manager.md` | Timelines, dependency tracking, agile ceremonies |
| 5 | Enterprise Architect | `TEAM/architecture/enterprise_architect.md` | System design, tech stack selection, ADR ownership |
| 6 | IT Infrastructure | `TEAM/architecture/it_infrastructure.md` | Dev environment setup, prerequisites, secrets config |
| 7 | DevOps Engineer | `TEAM/architecture/devops_engineer.md` | CI/CD pipeline, Docker, staging + production deployment |
| 8 | Prompt Engineer | `TEAM/architecture/prompt_engineer.md` | All AI prompts in `config/prompts/` — design, iteration, output validation |
| 9 | Security Engineer | `TEAM/architecture/security_engineer.md` | Threat modelling, OWASP audit, secrets management, pen testing |
| 10 | Competitor Analyst | `TEAM/research/competitor_analyst.md` | Tier 2 Research — Florida competitor intelligence, flag trigger data, market gap analysis |
| 11 | Business Analyst | `TEAM/business/ba.md` | E2E project knowledge, requirements clarity, full document map |
| 12 | UI/UX Designer | `TEAM/design/ui_ux_designer.md` | Human-facing output design — emails, statements, alerts |
| 13 | Robert — SME | `TEAM/sme/robert.md` | NexGen operations validation, flag logic, missing data provision |
| 14 | Mark — SME | `TEAM/sme/mark.md` | Field/office edge case validation, workflow expertise |
| 15 | Jessica — AR Specialist | `TEAM/ar/jessica_ar_specialist.md` | AR loop ownership post-implementation, reminder + escalation |
| 16 | Dev Manager | `TEAM/dev/agents/dev_manager.md` | Dev team leadership, sprint coordination, PR approval |
| 17 | Senior Dev | `TEAM/dev/agents/senior_dev.md` | Complex logic, integration, code review |
| 18 | Junior Dev | `TEAM/dev/agents/junior_dev.md` | Well-defined tasks, unit tests, self-check before handoff |
| 19 | QA Manager | `TEAM/qa/agents/qa_manager.md` | Final release gate, spawns QA agents, sign-off authority |
| 20 | Senior QA | `TEAM/qa/agents/senior_qa.md` | Edge cases, integration testing, security checks, test case authoring |
| 21 | Junior QA | `TEAM/qa/agents/junior_qa.md` | Happy path testing, basic functional checks |
| 22 | QE Manual | `TEAM/qa/agents/qe_manual.md` | Exploratory testing, UX validation of all human-facing outputs |
| 23 | QE Automation | `TEAM/qa/agents/qe_automation.md` | Automated regression suite, CI/CD test coverage |

---

## Team Structure by Tier

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 0 — HUMAN PRINCIPALS (Real Humans — milestone sign-offs)   │
│  Prateek · Ryan · Wyatt · Robert · Mark · Jessica                │
└─────────────────────────────────────────────────────────────────┘
                              |
                  consult AI agent first
                              |
                              v
┌─────────────────────────────────────────────────────────────────┐
│  TIER 0.5 — STAKEHOLDER AI AGENTS (Always Available)             │
│  Prateek AI · Ryan AI · Robert AI · Mark AI · Jessica AI         │
│  Wyatt AI                                                        │
│  Rule: consult before pinging real human                         │
└─────────────────────────────────────────────────────────────────┘
                              |
                              v
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1 — LEADERSHIP & BUSINESS                                  │
│  Product Owner · Project Manager                                 │
└─────────────────────────────────────────────────────────────────┘
                              |
                              v
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2 — ARCHITECTURE & TECHNICAL SPECIALISTS                   │
│  Enterprise Architect · IT Infrastructure · DevOps Engineer      │
│  Prompt Engineer · Security Engineer · Competitor Analyst        │
└─────────────────────────────────────────────────────────────────┘
                              |
                              v
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3 — BUSINESS & DESIGN                                      │
│  Business Analyst · UI/UX Designer                               │
└─────────────────────────────────────────────────────────────────┘
                              |
                              v
┌─────────────────────────────────────────────────────────────────┐
│  TIER 4 — SUBJECT MATTER EXPERTS (Human Role Cards)              │
│  Robert (SME) · Mark (SME) · Jessica (AR Specialist)             │
└─────────────────────────────────────────────────────────────────┘
                              |
                              v
┌──────────────────────────────┐  ┌──────────────────────────────┐
│  TIER 5 — DEVELOPMENT        │  │  TIER 6 — QA & ENGINEERING   │
│  Dev Manager                 │  │  QA Manager                  │
│  Senior Dev · Junior Dev     │  │  Senior QA · Junior QA       │
│                              │  │  QE Manual · QE Automation   │
└──────────────────────────────┘  └──────────────────────────────┘
```

---

## Escalation Chain

```
Junior Dev / Junior QA / QE Manual / QE Automation
        | (blockers, failures)
        v
Senior Dev / Senior QA
        | (unresolvable issues, systemic problems)
        v
Dev Manager / QA Manager
        | (BLOCKER, CRITICAL, architecture conflict)
        v
Prateek AI  <-- consult first (ACTIVE, always available)
        | (cannot answer, or decision outside documented standards)
        v
Real Prateek — CTO
        | (business rule conflict, go-live decision)
        v
Ryan AI / Wyatt AI  <-- consult first (STUB — answer from BRD)
        | (milestone sign-off, production approval)
        v
Real Ryan / Real Wyatt
```

---

## Who Does What — By Workflow Loop

### Loop 1 — Estimate Generation (Agents 1–9)

| Phase | Role | What They Do |
|-------|------|-------------|
| Requirements | BA | Defines acceptance criteria per agent |
| Prompt design | Prompt Engineer | Writes classifier, writer, reviewer, rewriter prompts |
| Output design | UI/UX Designer | Defines estimate email layout and tone |
| Build | Senior Dev + Junior Dev | Implements Agents 1–9 |
| Validation | Robert + Mark (SME) | Confirm flag logic and estimate accuracy |
| QA | Senior QA + QE Manual | Edge cases + UX output validation |
| Release | QA Manager + Prateek | Sign-off gate |

### Loop 2 — AR Follow-Up (Agents 10–14)

| Phase | Role | What They Do |
|-------|------|-------------|
| Requirements | BA + Jessica | Defines reminder schedule, escalation thresholds |
| Prompt design | Prompt Engineer | Writes AR reminder and escalation prompts (stages 1–3) |
| Output design | UI/UX Designer | Defines reminder email tone per escalation stage |
| Build | Senior Dev + Junior Dev | Implements Agents 10–14 |
| Validation | Jessica | Confirms reminder logic matches collections policy |
| QA | Senior QA + QE Manual | Integration + UX validation |
| Release | QA Manager + Prateek | Sign-off gate |

### Loop 3 — Monthly Statements (Agents 15–17)

| Phase | Role | What They Do |
|-------|------|-------------|
| Requirements | BA + Wyatt | Defines statement format and delivery spec |
| Prompt design | Prompt Engineer | Writes statement narrative prompt |
| Output design | UI/UX Designer | Defines Excel + PDF layout |
| Build | Senior Dev + Junior Dev | Implements Agents 15–17 |
| Validation | Ryan + Wyatt | Business approval of statement format |
| QA | Senior QA + QE Manual | Integration + output accuracy |
| Release | QA Manager + Prateek | Sign-off gate |

---

## Decision Authority

| Decision | First Consult | Final Authority |
|----------|---------------|-----------------|
| Architecture choice | Prateek AI | Enterprise Architect → Real Prateek approval |
| Prompt design | Prateek AI (standards) | Prompt Engineer |
| Business rule | Ryan AI | Real Ryan (final) |
| Sprint scope change | Prateek AI | Product Owner → Real Prateek approval |
| Production deployment | Prateek AI | Real Prateek sign-off required |
| Security incident | Prateek AI | Security Engineer → Real Prateek immediately |
| AR escalation threshold | Jessica AI | Real Jessica |
| Statement format | Wyatt AI | Real Wyatt |
| Flag trigger changes | Robert AI / Mark AI | Real Robert/Mark → Ryan confirmation |
| Code standards / ADR | Prateek AI | Real Prateek (if new standard needed) |
| Reminder tone validation | Jessica AI | Real Jessica (Sprint 7) |
| Estimate tone validation | Ryan AI | Real Ryan (Sprint 6) |

---

## Model Selection Rule (All Roles)

| Model | When to Use |
|-------|------------|
| **Haiku** | Simple tasks — reading files, running predefined tests, formatting, lookups |
| **Sonnet** | Complex tasks — design decisions, code generation, architecture, analysis, reasoning |
| **Opus** | Reserved for highest-complexity reasoning tasks only. Use sparingly — cost is ~15× Haiku. |

---

## Sprint Lifecycle — Which Roles Are Active When

| Phase | Active Roles |
|-------|-------------|
| Sprint planning | PM, PO, BA, Dev Manager, QA Manager |
| Pre-sprint (test cases) | Senior QA, Prompt Engineer (if AI sprint) |
| Development | Dev Manager, Senior Dev, Junior Dev, Prompt Engineer, IT Infrastructure |
| Code review | Senior Dev → Dev Manager |
| QA | Junior QA, QE Manual, Senior QA, QE Automation, QA Manager |
| SME validation | Robert, Mark (Loop 1) / Jessica (Loop 2) / Ryan + Wyatt (Loop 3) |
| Security review | Security Engineer (Sprint 10+) |
| Staging deploy | DevOps Engineer |
| Production deploy | DevOps Engineer + Prateek sign-off |

---

## Key Files Every Team Member Must Read

| File | Why |
|------|-----|
| `CLAUDE.md` | AI operating rules — read first, every session |
| `memory.md` | Project brain — context, decisions, dependencies |
| `learnings.md` | Confirmed patterns and caught mistakes |
| `sprints/index.md` | Find the active sprint |
| `issues/issue.md` | Open bugs and blockers |
