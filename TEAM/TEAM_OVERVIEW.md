# FTF Agentic AI OS — Full Team Overview

> **22 roles across 6 tiers.** Every role has a dedicated role card with persona, responsibilities, model selection, escalation path, and reading protocol.
> This document is the single reference for who does what and how the team works together.

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
| 10 | Business Analyst | `TEAM/business/ba.md` | E2E project knowledge, requirements clarity, full document map |
| 11 | UI/UX Designer | `TEAM/design/ui_ux_designer.md` | Human-facing output design — emails, statements, alerts |
| 12 | Robert — SME | `TEAM/sme/robert.md` | NexGen operations validation, flag logic, missing data provision |
| 13 | Mark — SME | `TEAM/sme/mark.md` | Field/office edge case validation, workflow expertise |
| 14 | Jessica — AR Specialist | `TEAM/ar/jessica_ar_specialist.md` | AR loop ownership post-implementation, reminder + escalation |
| 15 | Dev Manager | `TEAM/dev/agents/dev_manager.md` | Dev team leadership, sprint coordination, PR approval |
| 16 | Senior Dev | `TEAM/dev/agents/senior_dev.md` | Complex logic, integration, code review |
| 17 | Junior Dev | `TEAM/dev/agents/junior_dev.md` | Well-defined tasks, unit tests, self-check before handoff |
| 18 | QA Manager | `TEAM/qa/agents/qa_manager.md` | Final release gate, spawns QA agents, sign-off authority |
| 19 | Senior QA | `TEAM/qa/agents/senior_qa.md` | Edge cases, integration testing, security checks, test case authoring |
| 20 | Junior QA | `TEAM/qa/agents/junior_qa.md` | Happy path testing, basic functional checks |
| 21 | QE Manual | `TEAM/qa/agents/qe_manual.md` | Exploratory testing, UX validation of all human-facing outputs |
| 22 | QE Automation | `TEAM/qa/agents/qe_automation.md` | Automated regression suite, CI/CD test coverage |

---

## Team Structure by Tier

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1 — LEADERSHIP & BUSINESS                                  │
│  Prateek (CTO) · Ryan & Wyatt · Product Owner · Project Manager │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2 — ARCHITECTURE & TECHNICAL SPECIALISTS                   │
│  Enterprise Architect · IT Infrastructure · DevOps Engineer      │
│  Prompt Engineer · Security Engineer                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3 — BUSINESS & DESIGN                                      │
│  Business Analyst · UI/UX Designer                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  TIER 4 — SUBJECT MATTER EXPERTS & SPECIALISTS                   │
│  Robert (SME) · Mark (SME) · Jessica (AR Specialist)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
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
        ↓ (blockers, failures)
Senior Dev / Senior QA
        ↓ (unresolvable issues, systemic problems)
Dev Manager / QA Manager
        ↓ (BLOCKER, CRITICAL, architecture conflict)
Prateek — CTO
        ↓ (business rule conflict, go-live decision)
Ryan & Wyatt
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

| Decision | Owner |
|----------|-------|
| Architecture choice | Enterprise Architect → Prateek approval |
| Prompt design | Prompt Engineer |
| Business rule | Ryan (final) |
| Sprint scope change | Product Owner → Prateek approval |
| Production deployment | Prateek sign-off required |
| Security incident | Security Engineer → Prateek immediately |
| AR escalation threshold | Jessica |
| Statement format | Wyatt |
| Flag trigger changes | Robert/Mark → Ryan confirmation |

---

## Model Selection Rule (All Roles)

| Model | When to Use |
|-------|------------|
| **Haiku** | Simple tasks — reading files, running predefined tests, formatting, lookups |
| **Sonnet** | Complex tasks — design decisions, code generation, architecture, analysis, reasoning |
| **Opus** | **NEVER. Blocked at org level.** |

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
