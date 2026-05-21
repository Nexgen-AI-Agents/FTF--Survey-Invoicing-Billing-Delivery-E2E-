# ADR-005 — FTF API Response Envelope Unwrapping

## Date
2026-05-21

## Status
`Accepted`

## Context

The FTF CRM API `GET /orders` endpoint does not return a raw JSON array. It returns a wrapper object:
```json
{"count": 42, "data": [...orders...]}
```

This was discovered during Sprint 0 testing when `get_orders()` returned a dict and the test assertion `isinstance(orders, list)` failed. Agent code that calls `get_orders()` expects a clean list — iterating over a dict would silently yield dict keys ("count", "data") instead of orders.

## Decision

`ftf_client.get_orders()` unwraps the envelope before returning. Callers always receive `list[dict]`:

```python
body = r.json()
return body.get("data", body) if isinstance(body, dict) else body
```

The unwrapping is defensive: if the API ever returns a raw list, it passes through unchanged.

## Consequences

### Positive
- All 9 estimate-loop agents receive a clean `list[dict]` — no envelope handling needed in agent code
- Defensive unwrap handles both old and new API response formats
- Discovered and fixed in Sprint 0 before any agent code was written

### Negative / Trade-offs
- `count` field is discarded — if pagination is added later, this needs revisiting
- If FTF changes the envelope key from "data" to something else, the fallback returns the raw dict (agents would break silently)

### Neutral
- Pricing API (`GET /pricing`) uses `?service=X&tier=Y` query params — no envelope; returns single price dict

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Let agents unwrap themselves | Every agent that calls get_orders() must remember to unwrap — error-prone |
| Assert response is a list | Would crash on valid API responses |

## Related
- `code/shared/core/ftf_client.py` — `get_orders()` implementation
- `sprints/sprint_00_foundation.md` — Sprint 0 Completion Brief (carry-forward note)
- `learnings.md` — FTF API envelope noted as confirmed learning
