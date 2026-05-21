# ADR-003 — Claude Model Selection: Haiku / Sonnet Split

## Date
2026-05-21

## Status
`Accepted`

## Context

The system makes LLM calls across 17 agents. Cost and latency matter: the estimate loop runs every 60 minutes, the AR loop daily. Some agents need full reasoning (classifier, writer, reviewer, escalation); others just need fast execution with no reasoning (monitor, scanner, scheduler). Opus is blocked at the org level and must never be used.

## Decision

Two-tier model selection defined in `code/shared/config/models.py`:

- **Haiku (`claude-haiku-4-5-20251001`)** — agents that do NOT need reasoning: Monitor (Agent 2), AR Scanner (Agent 10), Scheduler (Agent 11). These are pure orchestration — no LLM call actually made.
- **Sonnet (`claude-sonnet-4-6`)** — all reasoning agents: Orchestrator (Agent 1), Classifier (Agent 3), Human Gate (Agent 4), Pricing Engine (Agent 5), Writer (Agent 6), Reviewer (Agent 7), Sender (Agent 8), Reporter (Agent 9), AR Writer (Agent 12), AR Escalator (Agent 13), Delivery Tracker (Agent 14), Statement agents (15–17).

Opus: **NEVER**. Blocked at org level. No exceptions.

## Consequences

### Positive
- Cost control: Haiku is 15× cheaper than Sonnet per token
- Latency: Haiku responses are faster for non-reasoning tasks
- Org policy compliant: Sonnet is the highest model the org allows in this project

### Negative / Trade-offs
- Sonnet may miss edge cases that Opus would catch (accepted risk — reviewed by human gate for flagged orders)
- Model IDs hardcoded in models.py — must update when Anthropic releases new versions

### Neutral
- Haiku agents (Monitor, Scanner) don't actually call the LLM — model assignment is reserved for potential future use
- All agents call LLM through `code/shared/core/claude_client.py` — single change point when model IDs update

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Sonnet for all agents | Higher cost; slow for simple orchestration tasks |
| Opus for classifier/writer | Blocked at org level |
| Dynamic model selection | Adds complexity; current split is sufficient |

## Related
- `code/shared/config/models.py` — model ID constants
- `code/shared/core/claude_client.py` — LLM call wrapper
- `CLAUDE.md` — org model policy
- `TEAM/TEAM_OVERVIEW.md` — Model Selection Rule table
