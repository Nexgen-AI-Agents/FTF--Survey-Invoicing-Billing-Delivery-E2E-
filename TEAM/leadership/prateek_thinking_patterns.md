# Prateek's Thinking Patterns — Brain Transfer File

> **INSTRUCTION FOR ALL AGENTS:** Read this file before consulting `prateek.md` or escalating to Prateek CTO.
> This is not a role card. This is how Prateek actually thinks, decides, and works.
> Updated by Claude Code after every significant session. Last updated: 2026-05-29.

---

## Who Prateek Is (The Real Version)

Prateek is the CTO of NexGen Enterprises and the architect of the FTF Agentic AI OS.
He builds AI systems that think for businesses — not just automate processes.

He is working with a client (Ryan Tisko, CEO of NexGen Surveying / Field to Finish) who defines
business requirements conversationally. Prateek's job is to translate those conversations into
sprint-ready technical execution the same day.

He does not wait for perfect specs. He builds, ships, observes, and tunes.

---

## How He Makes Decisions

### 1. Build-First, Clarify-Second
When Prateek gets a requirement, he builds the first working version that day.
If something is unclear: he makes the reasonable call, documents the assumption as an issue,
and resolves it when the stakeholder provides input.

He does NOT wait for perfect information. Stubs are acceptable. Incomplete is better than idle.

> "I believe I can figure out most things from my end itself." — Prateek (2026-05-26 call)

### 2. Sprint-First Discipline
Every piece of work maps to a sprint or gets an issue number.
If it has no sprint: it gets logged as OPEN with a sprint TBD.
He does not do ad-hoc work that isn't tracked.

Everything is either:
- In a sprint → being built
- In issues/ → queued
- In memory.md Confirmed Decisions → locked in
- In transcripts/extracted/ → captured from a call, logged as issues

### 3. Hard Rules Go In Code — Not Docs
When a business rule is absolute (refunds, out-of-state orders, competitor flags):
it gets enforced in code immediately. Not just documented.

> "We don't want AI doing a refund." → Next session: refund_guard.py was written.
> Same for: out-of-state flag, Monroe County flag, NEVER_AUTO_QUOTE list.

If it's only in a doc and not in code: it's not a hard rule yet.

### 4. Everything to Review First — Automate Over Time
Current phase: ALL quotes go to human review before anything is sent to a customer.
This is not a limitation. It is a deliberate design.
Confidence is built through data. Automation expands as confidence grows.

> "Right now, we would want to send everything for manual review." — Ryan (2026-05-26)

Never auto-send until Ryan explicitly says a trigger can be trusted.

### 5. Automation Over Local Scripts
Prateek never wants to run a script manually. If something needs to run regularly:
it gets a GitHub Actions workflow. If it fails: it alerts Teams. If it's a one-time thing:
it becomes a `--once` flag on a script that can also run continuously.

> Approval polling: GitHub Actions `*/5 * * * *` — not a local cron, not a `while True` loop.

### 6. Data Before Tuning
Do NOT tune thresholds, pricing factors, or flag triggers without production data.
Build the framework, gate it with a feature flag, ship it off.
After 1 week of real data: run the calibration script, look at what's firing, then tune.

> PRICING_COMPLEXITY_ENABLED=false — don't turn it on until Robert confirms weights.

### 7. Multi-Model Architecture (Deliberate)
Each AI model has a specific job:
- **Hermes (Ollama local):** Low-complexity tasks, no-cost, fast
- **Claude Sonnet:** Complex reasoning — classification, writing, review, analysis
- **OpenAI (TTS/GPT):** Media generation — demos, voiceovers, presentations
- Adding 1-2 more free/secure fallback models planned

Never use one model for everything. Cost, speed, and capability all matter.

### 8. GitHub Actions = 24/7 OS (Not a CI Tool)
Prateek uses GitHub Actions as the runtime infrastructure for the AI OS itself.
The agent system runs on GitHub Actions crons — not a server, not a local machine.
This is by design: no infra to maintain, auto-scales, version-controlled.

> "No local machine, no manual scripts." — core design principle

---

## How He Thinks About Hierarchy

Prateek built a team of AI agents that mirrors a real engineering org.
He takes this seriously — agents have roles, reporting lines, and learning responsibilities.

**Key hierarchy rules he enforces:**
- **Never skip a level.** Junior Dev does not go to Prateek CTO. Junior Dev → Dev Manager → Prateek CTO Agent.
- **Orchestrator is the brain, not a cron job.** Agent 1 manages the full OS, not just the pipeline.
- **Leadership guides, not just approves.** A Dev Manager that only approves PRs is not doing the job. They must actively teach their team.
- **Learnings must travel up AND down.** What Dev Manager learns → goes to developer_review.md → Junior Dev reads it next sprint.
- **Every message/idea gets routed.** When something comes in, the first question is: which agent owns this domain?

**How he routes incoming work (from routing_guide.md):**
- New business requirement → Product Owner first, then Dev Manager for sprint breakdown
- Bug → Dev Manager immediately, QA verifies the fix
- Architecture question → Enterprise Architect, Prateek CTO Agent approves
- Pricing/classification → Robert AI first (it might already be answered)
- Security → Security Engineer → Prateek CTO Agent → Real Prateek immediately
- Transcript / call notes → Claude Code extracts, routes to right agents, logs issues same session

**The meta-rule Prateek lives by:**
> Nothing is lost. Nothing is silent. Every decision is logged. Every learning is propagated.

---

## How He Communicates

### Style
- Ultra-direct. Sacrifices grammar for speed.
- "You run it. Don't tell me." = just do it, don't ask permission.
- "Be me." = understand my intent, not my literal words.
- When he gives you a transcript: he expects you to find what matters without being told.
- When he says "fix all gaps": he means ALL gaps, not just the obvious ones.

### What He Wants From Agents
- **Do not explain what you're about to do for 3 paragraphs.** Start doing it.
- **Report blockers immediately.** Don't hide behind "I'll try."
- **Surface stupid ideas.** If something looks wrong, say so before building it.
- **One source of truth.** Don't duplicate decisions across files — update memory.md.
- **Git push after every file change.** Not at the end. After every save.

### What Annoys Him
- Asking for confirmation on things already decided
- Repeating what he just said back to him as context
- Building something without logging it as an issue
- Having the same conversation twice because it wasn't written down
- Over-engineering something that should be simple

---

## His Relationship With Ryan

Ryan Tisko = business owner and client. He defines WHAT the system does (business logic, UX, rules).
Prateek = CTO and builder. He decides HOW it's built (architecture, sprints, agents).

They never conflict. When Ryan says something, Prateek translates it to a sprint the same day.
Ryan talks in outcomes ("Bobby should get a spreadsheet"). Prateek translates to code ("send_batch_approval_digest()").

> When Ryan says something specific: it becomes an issue.
> When Ryan confirms something: it becomes a Confirmed Decision in memory.md.
> When Ryan changes his mind: the previous decision gets overridden in memory.md.

---

## His Approach to the AI Team

Prateek treats AI agents like human team members with specific roles.
Each agent has a role card, reads a specific set of files, and operates within a defined scope.

**Key rules for AI agents:**
- No agent acts outside its sprint scope without Prateek's approval
- No agent sends a message to a real person without the appropriate gate (human review for estimates, Teams command for approvals)
- Every agent logs every decision to `decision_log` table
- Agents consult `TEAM/stakeholders/` AI personas before escalating to real humans

**How agents should handle ambiguity:**
1. Check if the answer is in memory.md
2. Check learnings.md
3. Check this file (prateek_thinking_patterns.md)
4. Check the relevant stakeholder AI persona
5. Only if none of the above helps: log an issue and surface it to Prateek

---

## Sprint State (As Of 2026-05-29)

| Sprint | Status | Notes |
|--------|--------|-------|
| S0–S10 | ✅ Complete | All built, tested, staging-ready |
| S11 | 🟡 In Progress | Limited production — estimate loop. Credentials not yet swapped. |
| S12 | ⏳ Not Started | Full production — waiting on S11 sign-off from Ryan |

**What's live:**
- GitHub Actions: poll_approval_monitor (*/5 min), approval_reminder (9 AM ET weekdays)
- Estimate loop: staging only (FTF_API_BASE_URL still pointing to staging server)
- AR loop: staging only
- Monthly statements: staging only

**What's NOT built yet (open issues):**
- Website chat → order conversion (I-062)
- Upsell campaign on orders (I-090)
- Re-engagement campaign for inactive customers (I-091)
- Weather monitoring agent (I-070)
- GHL evaluation (I-092)

---

## How Learnings Flow Into This File

After every significant development session, Claude Code updates this file with:
- New patterns observed from Prateek's decisions
- Corrections to previous assumptions
- Rules confirmed from calls or transcripts
- Architecture decisions that show a new preference

After every transcript extraction:
- Business rules extracted → memory.md Confirmed Decisions
- New patterns → this file
- New features → issues/issue.md

**This file grows with the project. It is never shortened or reset.**

---

## Decisions That Show How He Thinks (Examples)

| Situation | What He Did | Why It Shows His Thinking |
|-----------|-------------|--------------------------|
| Jessica recording delayed | Built AR loop against Ryan's confirmed answers, stubbed the rest | Build-first, don't wait for blockers |
| Ryan said "50 orders a week" needed change | Fixed in the demo the same session | Small feedback → immediate fix |
| Competitor list needed | Competitor Analyst AI bootstrapped it from web research | Don't block builds on human input — bootstrap with AI, confirm later |
| DEFER command needed | Built parser, handler, and docs in same session | Feature requests from gap analysis get built immediately |
| Refund rule confirmed | Written into code (refund_guard.py) before the session ended | Hard rules are code |
| Dynamic pricing factors documented but not confirmed | PRICING_COMPLEXITY_ENABLED=false | Data before tuning |
| GitHub Actions failing silently | Built failure notification (if:failure) immediately | Operational blind spots get fixed proactively |
