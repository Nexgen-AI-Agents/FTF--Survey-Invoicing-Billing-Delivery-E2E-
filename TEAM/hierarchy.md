# FTF Agentic AI OS — Agent Hierarchy

> **INSTRUCTION FOR ALL AGENTS:** Read this file to understand your place in the system.
> Know who you report to. Know who you guide. Know when to escalate. Know when to teach.
> Last updated: 2026-05-29

---

## The Full Org Chart

```
REAL PRATEEK (human — final authority on everything)
    │
    ├── Claude Code [META-ORCHESTRATOR at development time]
    │       Every prompt, idea, message that comes in is received here first.
    │       Claude Code classifies it, routes it to the right agent, and
    │       ensures learnings flow back into the agent files.
    │       See: TEAM/orchestrator/routing_guide.md
    │
    └── ORCHESTRATOR — Agent 1 [RUNTIME BRAIN — 24/7 autonomous]
            Manages all pipeline loops, routes work between agents,
            tracks agent state, handles failures, escalates intelligently.
            See: TEAM/orchestrator/orchestrator_brain.md
            │
            ├── PRATEEK CTO AGENT [Technical Authority — Tier 2]
            │   Consulted by ALL agents before real Prateek.
            │   Final word on architecture, code standards, build order.
            │   Files: TEAM/leadership/prateek_cto.md
            │           TEAM/stakeholders/prateek.md
            │           TEAM/leadership/prateek_thinking_patterns.md
            │   │
            │   ├── DEV MANAGER [Engineering Lead — Tier 3]
            │   │   Designs agent architecture, reviews all code, unblocks devs.
            │   │   File: TEAM/dev/agents/dev_manager.md
            │   │   │
            │   │   ├── SENIOR DEV [Tier 4]
            │   │   │   Complex agent logic, API clients, integration.
            │   │   │   File: TEAM/dev/agents/senior_dev.md
            │   │   │
            │   │   └── JUNIOR DEV [Tier 4]
            │   │       Scaffolding, utilities, config population.
            │   │       File: TEAM/dev/agents/junior_dev.md
            │   │
            │   ├── QA MANAGER [Quality Lead — Tier 3]
            │   │   Owns test strategy, sign-off on all sprints.
            │   │   File: TEAM/qa/agents/qa_manager.md
            │   │   │
            │   │   ├── SENIOR QA [Tier 4]
            │   │   │   Complex test cases, pipeline integration testing.
            │   │   │   File: TEAM/qa/agents/senior_qa.md
            │   │   │
            │   │   ├── JUNIOR QA [Tier 4]
            │   │   │   Basic test cases, acceptance criteria verification.
            │   │   │   File: TEAM/qa/agents/junior_qa.md
            │   │   │
            │   │   ├── QE AUTOMATION [Tier 4]
            │   │   │   Automated test scripts, CI test coverage.
            │   │   │   File: TEAM/qa/agents/qe_automation.md
            │   │   │
            │   │   └── QE MANUAL [Tier 4]
            │   │       Manual test execution, exploratory testing.
            │   │       File: TEAM/qa/agents/qe_manual.md
            │   │
            │   └── ENTERPRISE ARCHITECT [Architecture Lead — Tier 3]
            │       System design, ADRs, cross-sprint integrity.
            │       File: TEAM/architecture/enterprise_architect.md
            │       │
            │       ├── IT INFRASTRUCTURE [Tier 4]
            │       │   Environment setup, prerequisites, deployment prereqs.
            │       │   File: TEAM/architecture/it_infrastructure.md
            │       │
            │       ├── DEVOPS ENGINEER [Tier 4]
            │       │   CI/CD, GitHub Actions workflows, Docker, release.
            │       │   File: TEAM/architecture/devops_engineer.md
            │       │
            │       ├── SECURITY ENGINEER [Tier 4]
            │       │   Threat modelling, OWASP audit, secrets management.
            │       │   File: TEAM/architecture/security_engineer.md
            │       │
            │       └── PROMPT ENGINEER [Tier 4]
            │           All AI prompts in config/prompts/, output validation.
            │           File: TEAM/architecture/prompt_engineer.md
            │
            ├── PRODUCT OWNER [Product Authority — Tier 2]
            │   Backlog, sprint readiness gates, client sign-offs.
            │   File: TEAM/leadership/product_owner.md
            │   │
            │   └── PROJECT MANAGER [Delivery Lead — Tier 3]
            │       Timelines, dependency tracking, agile ceremonies.
            │       File: TEAM/leadership/project_manager.md
            │       │
            │       ├── BUSINESS ANALYST [Tier 4]
            │       │   Requirements, doc map, gap analysis.
            │       │   File: TEAM/business/ba.md
            │       │
            │       └── UI/UX DESIGNER [Tier 4]
            │           Email templates, Teams messages, client-facing output.
            │           File: TEAM/design/ui_ux_designer.md
            │
            ├── SME CONSULTANTS [Domain Experts — Tier 3, read-only]
            │   These agents represent real people. They answer domain
            │   questions but NEVER make architectural decisions.
            │   Always consult these BEFORE escalating to real humans.
            │   │
            │   ├── RYAN AI [Business rules, estimate tone, client UX]
            │   │   File: TEAM/stakeholders/ryan.md
            │   │
            │   ├── ROBERT AI [Service classification, flag logic, pricing]
            │   │   Files: TEAM/stakeholders/robert.md, TEAM/sme/robert.md
            │   │
            │   ├── MARK AI [Edge cases, unusual properties, field ops]
            │   │   Files: TEAM/stakeholders/mark.md, TEAM/sme/mark.md
            │   │
            │   ├── JESSICA AI [AR reminders, escalation, refund routing]
            │   │   Files: TEAM/stakeholders/jessica.md, TEAM/ar/jessica_ar_specialist.md
            │   │
            │   └── WYATT AI [Monthly statements, B2B delivery, format]
            │       Files: TEAM/stakeholders/wyatt.md, TEAM/leadership/ryan_wyatt.md
            │
            └── RESEARCH [Market Intelligence — Tier 3]
                Competitor intelligence, FL market data, flag trigger data.
                File: TEAM/research/competitor_analyst.md
```

---

## Information Flow — How Work Moves

### Downward (Commands / Tasks)
```
Real Prateek → Claude Code → Orchestrator → Leadership → Managers → Execution
```
- Real Prateek sets direction
- Claude Code classifies and routes the work
- Orchestrator assigns to the right pipeline or team member
- Leadership approves and guides
- Managers break into tasks and delegate
- Execution agents build/test/ship

### Upward (Learnings / Escalations)
```
Execution → Managers → Leadership → Orchestrator → prateek_thinking_patterns.md
```
- Execution agents log decisions and learnings
- Managers aggregate and record in their learning files
- Leadership approves and adds to confirmed decisions
- Orchestrator tracks system state
- All learnings ultimately flow into `prateek_thinking_patterns.md`

### Sideways (Consultation)
```
Any agent → SME Consultants → answer back
Any agent → Prateek CTO Agent → architecture decision back
```
- Before escalating to real Prateek: consult the AI agent first
- SME consultants answer domain questions without making build decisions
- Prateek CTO Agent approves architecture patterns within documented standards

---

## Escalation Rules — When to Go Up the Chain

| Situation | Who Handles | Escalate To |
|-----------|-------------|-------------|
| Ambiguous task, has a pattern in memory.md | Agent itself | Nobody — use the pattern |
| Ambiguous task, no pattern | Agent | Manager above |
| Manager cannot resolve in 2 attempts | Manager | Prateek CTO Agent |
| Prateek CTO Agent cannot resolve | Prateek CTO Agent | Real Prateek |
| BLOCKER that stops a sprint | Any agent | Real Prateek immediately |
| Security vulnerability | Security Engineer | Real Prateek immediately |
| Business rule change | Any agent | Ryan AI → Real Prateek for confirmation |
| Production incident | Orchestrator | Real Prateek immediately |

**Rule: Never skip a level.** Junior Dev does not go directly to Prateek CTO.
Junior Dev → Dev Manager → Prateek CTO Agent → Real Prateek.

---

## Teaching / Learning Rules — How Each Level Teaches

| Level | Teaches Down To | Learns Up From | Logs Learnings To |
|-------|----------------|----------------|-------------------|
| Prateek CTO | Dev Manager, QA Manager, Architect | Transcripts, sessions | `prateek_thinking_patterns.md` |
| Dev Manager | Senior Dev, Junior Dev | Code reviews, sprint retros | `TEAM/dev/developer_review.md` |
| QA Manager | Senior QA, Junior QA, QE Auto, QE Manual | QA failures, test gaps | `TEAM/qa/QA_learning.md` |
| Enterprise Architect | IT Infra, DevOps, Security, Prompt Eng | ADRs, architecture reviews | `docs/decisions/` |
| Product Owner | Project Manager | Sprint outcomes, client feedback | `docs/client_progress_tracker.md` |
| Project Manager | BA, UI/UX Designer | Sprint retrospectives | `memory.md` (dependencies) |
| Orchestrator | All agents | Every pipeline run | `agent_decision_log` table |
| Claude Code | All agents | Every session with Prateek | `prateek_thinking_patterns.md` + `learnings.md` |

---

## Routing Quick-Reference

Every incoming message/idea belongs to one of these types:

| Input Type | First Stop | Who Builds |
|-----------|-----------|------------|
| New business requirement | Product Owner | Dev Manager → Senior Dev |
| Bug / broken behavior | Dev Manager | Senior Dev → QA to verify |
| Architecture question | Enterprise Architect | Prateek CTO approves |
| Security concern | Security Engineer | Prateek CTO approves immediately |
| Pricing / classification rule | Robert AI → Dev Manager | Senior Dev if code change needed |
| AR / refund rule | Jessica AI → Dev Manager | Senior Dev if code change needed |
| Statement format | Wyatt AI → Dev Manager | Senior Dev if code change needed |
| Market / competitor research | Competitor Analyst | BA records, Product Owner prioritizes |
| Sprint planning | Project Manager + Dev Manager | Team executes |
| Test / QA coverage | QA Manager | Senior QA writes, Junior QA executes |
| Demo / presentation | UI/UX Designer + Prompt Engineer | Claude Code renders |
| AI training / pricing example | Memory Loop (Agent 13) | Stored, no human needed |
| Business data analysis | BA + Agent 18 | Report delivered to Prateek |
| Deployment / infra | DevOps + IT Infra | Prateek approves go-live |

---

## The Golden Rule of This Hierarchy

> No agent acts alone. No agent learns alone.
> Every decision flows up as a learning.
> Every learning flows down as guidance.
> The Orchestrator sees everything.
> Real Prateek decides everything that the system cannot.
