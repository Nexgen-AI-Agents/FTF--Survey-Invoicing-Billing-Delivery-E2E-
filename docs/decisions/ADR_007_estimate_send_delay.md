# ADR-007 — Estimate Send Delay: Random 6–13 Minutes

## Date
2026-05-21

## Status
`Accepted`

## Context

When the AI system generates an estimate, it could technically send it within seconds of receiving the order. Sending an estimate within seconds of a customer submitting a request looks robotic and unnatural. It may also cause customer confusion ("did a real person look at this?") and undermine trust in the quality of the estimate.

## Decision

Agent 8 (Sender) waits a random delay between **6 and 13 minutes** before sending each estimate. This simulates the realistic response time of a human reviewer. Decision confirmed by Ryan.

Constants in `code/shared/config/settings.py`:
```python
ESTIMATE_DELAY_MIN = 360   # 6 minutes in seconds
ESTIMATE_DELAY_MAX = 780   # 13 minutes in seconds
```

Agent 8 uses: `time.sleep(random.randint(ESTIMATE_DELAY_MIN, ESTIMATE_DELAY_MAX))`

## Consequences

### Positive
- Estimates arrive in a timeframe consistent with human review
- Builds customer trust in the quality and care put into estimates
- Randomness prevents a predictable pattern customers could detect

### Negative / Trade-offs
- Adds 6–13 minutes to estimate delivery time per order
- In high-volume scenarios (many simultaneous orders), delays stack if agents are sequential

### Neutral
- The hourly GitHub Actions schedule already means some delay exists regardless
- Delay applies per estimate, not per batch — if 5 orders are processed in one run, each gets its own random delay

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| No delay (send immediately) | Looks robotic; customer trust concern raised by Ryan |
| Fixed 10-minute delay | Predictable; a pattern customers could notice |
| Longer delay (30+ min) | Defeats the "faster than manual" benefit of the system |

## Related
- `code/shared/config/settings.py` — `ESTIMATE_DELAY_MIN`, `ESTIMATE_DELAY_MAX`
- `memory.md` → Confirmed Decisions (Estimate delay)
- Sprint 6: `sprints/sprint_06_sender_reporter.md` — Agent 8 Sender implements this
