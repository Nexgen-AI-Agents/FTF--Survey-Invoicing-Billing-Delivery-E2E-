# Routing Guide — How Every Incoming Message Gets Dispatched

> **Used by:** Claude Code (meta-orchestrator), Orchestrator Agent 1, all leadership agents.
> **Purpose:** When anything comes in — a prompt, idea, message, transcript, request — this guide
> determines who handles it and what happens next.
> Last updated: 2026-05-29

---

## Step 1 — Classify the Input

Every incoming message falls into one of these categories:

| # | Category | Signal Words / Context |
|---|----------|----------------------|
| A | New business requirement | "there should be an agent", "we need", "Ryan said", "add a feature" |
| B | Bug / broken behavior | "not working", "wrong output", "edge case fails", "classifier misses" |
| C | Architecture decision | "should we use", "how should we structure", "which approach", "ADR needed" |
| D | Pricing / service classification | "how do we price", "what service type", "flag or not", "this job is like" |
| E | AR / refund / statement rule | "AR process", "overdue", "refund", "monthly statement", "Jessica" |
| F | Security concern | "exposed", "credentials", "vulnerability", "access control" |
| G | Competitor / market intelligence | "competitor", "Florida market", "who else does this" |
| H | Sprint planning | "what should Sprint N include", "backlog", "priority", "timeline" |
| I | Test / QA coverage | "test case", "scenario", "does this pass", "regression" |
| J | Demo / presentation | "update the demo", "video", "slide", "client presentation" |
| K | AI training / memory | "store this", "remember", "this is how I'd price it", "feed to AI" |
| L | Business data / analysis | "analyze", "report", "how many orders", "what's the AR aging" |
| M | Deployment / infra | "deploy", "GitHub Actions", "workflow", "production credentials" |
| N | Transcript / call notes | new .txt file provided, "here's the call", "take notes from this" |
| O | Learning / pattern | "note this", "add to memory", "don't forget", "future rule" |

---

## Step 2 — Route to the Right Agent

### A — New Business Requirement
```
Product Owner (backlog + sprint readiness)
    → Dev Manager (break into sprint tasks)
        → Senior Dev (build)
            → QA Manager (test)
                → Prateek CTO Agent (approve before production)
```
**Learning update:** Add to issues/issue.md with sprint assignment. Confirm in memory.md if it's a rule.

---

### B — Bug / Broken Behavior
```
Dev Manager (triage: how bad, which agent, which sprint)
    → Senior Dev (fix)
        → QA Manager (verify fix + regression test)
            → Prateek CTO Agent (approve if architecture-affecting)
```
**Learning update:** Add to learnings.md. If it's a recurring class of bug, add to developer_review.md.

---

### C — Architecture Decision
```
Enterprise Architect (design options, tradeoffs)
    → Prateek CTO Agent (approve if within documented patterns)
        → Real Prateek (if new pattern outside ADRs)
```
**Learning update:** Write an ADR in docs/decisions/. Add to memory.md if it's a confirmed decision.

---

### D — Pricing / Service Classification Rule
```
Robert AI (does this fit a known rule?)
    → If yes: Dev Manager (code it if not already coded)
    → If no: Real Robert/Ryan confirmation needed
        → After confirmation: Dev Manager → Senior Dev
```
**Learning update:** Add to memory.md service names table. Update flag_triggers.py or pricing engine.

---

### E — AR / Refund / Statement Rule
```
Jessica AI (AR + refund domain)
    or Wyatt AI (statement domain)
    → Dev Manager (if code change needed)
        → Senior Dev (build)
```
**Learning update:** Add to memory.md Confirmed Decisions. Update agent_10 or agent_11 or statements loop.

---

### F — Security Concern
```
Security Engineer (assess severity)
    → Prateek CTO Agent (if architecture change required)
        → Real Prateek IMMEDIATELY (no delay, no AI gate)
```
**Learning update:** Add to learnings.md. If a code fix: Dev Manager → Senior Dev immediately.

---

### G — Competitor / Market Intelligence
```
Competitor Analyst (research + analysis)
    → Business Analyst (record findings)
        → Product Owner (prioritize if action needed)
```
**Learning update:** Update TEAM/research/competitive_analysis.md. Update flag_triggers.py if new competitor found.

---

### H — Sprint Planning
```
Project Manager (timeline + dependencies)
    + Dev Manager (task breakdown)
    + QA Manager (test scope)
    → Prateek CTO Agent (final sprint approval)
        → Real Prateek (if scope change or new external dependency)
```
**Learning update:** Update sprints/index.md. Create sprint file. Update memory.md blockers.

---

### I — Test / QA Coverage
```
QA Manager (test strategy + scope)
    → Senior QA (complex test cases)
    → Junior QA (basic scenarios)
    → QE Automation (automated scripts)
    → QE Manual (execution)
```
**Learning update:** Update TEAM/qa/QA_learning.md. Update sprint test case file.

---

### J — Demo / Presentation
```
UI/UX Designer (design + tone)
    + Prompt Engineer (narration + AI prompt content)
    → Claude Code (render the video/slides via generate_client_demo_vN.py)
```
**Learning update:** Update CHANGELOG.md. Version the demo (vN+1).

---

### K — AI Training / Memory
```
Agent 13 Pricing Trainer (store pricing example with rationale)
    or Memory Manager (store general learning)
    → Dream Processor (nightly: integrate into knowledge base)
```
**Learning update:** Store to pricing_examples table. No escalation needed unless governance check fails.

---

### L — Business Data / Analysis
```
Agent 18 Business Analyst (query DB, Claude analysis, deliver report)
    → Business Analyst agent (format + insights)
        → Real Prateek (review findings)
```
**Learning update:** Add key findings to memory.md if they change how we operate.

---

### M — Deployment / Infra
```
DevOps Engineer (workflow design)
    + IT Infrastructure (environment prereqs)
    → Prateek CTO Agent (approve deployment plan)
        → Real Prateek (production go-live approval)
```
**Learning update:** Update RELEASE_RUNBOOK.md. Update memory.md sprint status.

---

### N — Transcript / Call Notes
```
Claude Code (extract FTF-relevant points only)
    → Save raw file to transcripts/raw/YYYY-MM-DD_[people]_[topic].txt
    → Create extracted file: transcripts/extracted/YYYY-MM-DD_extracted.md
    → New requirements → Product Owner route (A above)
    → New rules → memory.md + agent files
    → New patterns → prateek_thinking_patterns.md
```
**Learning update:** Log new issues. Update memory.md. Update relevant agent files same session.

---

### O — Learning / Pattern
```
Claude Code (categorize: is it a Prateek pattern? a business rule? a technical note?)
    → prateek_thinking_patterns.md (if Prateek's decision-making pattern)
    → memory.md Confirmed Decisions (if a locked business rule)
    → learnings.md (if a technical or behavioral note)
    → relevant agent file (if specific to a domain)
```
**Learning update:** This IS the learning update.

---

## The Meta-Rule

When you receive something and you're not sure which category:
1. Ask: **Is this about HOW to build something?** → Dev Manager route
2. Ask: **Is this about WHAT to build?** → Product Owner route
3. Ask: **Is this about WHETHER to build it?** → Prateek CTO Agent route
4. Ask: **Is something broken right now?** → Dev Manager + QA Manager immediately
5. Ask: **Does a real person need to be informed?** → Teams notification + escalate

---

## After Every Dispatch

Whatever route the work takes, TWO things always happen:
1. **The agent that handled it logs what it learned** — to its learning file
2. **Claude Code propagates new patterns** — to `prateek_thinking_patterns.md` and `learnings.md`

Nothing is lost. Nothing is silent. Every dispatch is a learning opportunity.
