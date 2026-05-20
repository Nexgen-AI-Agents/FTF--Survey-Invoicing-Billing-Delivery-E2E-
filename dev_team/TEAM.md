# Developer Team — FTF Agentic AI OS

## Team Structure

| Role | Agent File | Model | Primary Responsibility |
|------|-----------|-------|----------------------|
| Dev Manager | `agents/dev_manager.md` | Sonnet | Architecture decisions, final code approval, spawns agents |
| Senior Developer | `agents/senior_dev.md` | Sonnet | Complex logic, integration, first-pass code review |
| Junior Developer | `agents/junior_dev.md` | Haiku or Sonnet | Well-defined single-module tasks |

---

## Model Selection Rule

| Model | When to Use |
|-------|------------|
| **Haiku** | Simple tasks — reading files, formatting, minor edits, boilerplate scaffolding, lookups |
| **Sonnet** | Complex tasks — writing agent logic, multi-step reasoning, architecture, code review, debugging |
| **Opus** | NEVER. Blocked at org level. |

---

## Review Flow

```
Junior Developer writes code
        ↓
Senior Developer reviews (logic, style, standards, edge cases)
        ↓
Dev Manager approves (architecture fit, cross-sprint impact, security)
        ↓
QA Team (Junior QA → Senior QA → Manager QA)
```

No code reaches QA without Manager Dev approval.
No code is shipped without Manager QA sign-off.

---

## Spawn Rules (Manager Dev only)

- **Spawn additional Senior Dev** when: 2+ sprints active in parallel, or a Senior is blocked and needs relief.
- **Spawn additional Junior Dev** when: a sprint has 3+ independent well-defined tasks, or a Senior needs to delegate isolated sub-tasks.
- **Max concurrent agents per sprint:** Manager + 2 Senior, OR 1 Senior + 2 Junior. Never more.
- Spawned agents inherit the same reading protocol and code standards.

---

## Reading Protocol (every agent, every task)

Read in this order before starting any work:

1. `CLAUDE.md` — project rules and role
2. `memory.md` — project brain (context, APIs, decisions)
3. `learnings.md` — known AI mistakes and confirmed patterns
4. `dev_team/TEAM.md` — this file (team rules)
5. `dev_team/developer_review.md` — shared dev learnings
6. Active sprint file (check `sprints/index.md` first)
7. `issues/issue.md` — open issues affecting current sprint

---

## Learnings Protocol

Append to `dev_team/developer_review.md` when:
- A non-obvious bug is found and fixed
- A coding pattern is confirmed as correct for this project
- A decision is made that affects future sprints
- A code review catches a standard violation

Format: `## [YYYY-MM-DD] — Short title` then bullet points.
