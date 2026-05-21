# ADR-006 — FEMA Flood Zone Check: Graceful Degradation

## Date
2026-05-21

## Status
`Accepted`

## Context

Agent 3 (Classifier) must check whether a property is in a FEMA Special Flood Hazard Area to determine if an Elevation Certificate must be auto-added. The FEMA National Flood Hazard Layer is a public REST API at `hazards.fema.gov`.

Two blockers discovered in Sprint 0:
1. **Corporate network blocks hazards.fema.gov** — the domain is filtered at the office firewall
2. **Python 3.14 TLS regression** — `ssl.OP_LEGACY_SERVER_CONNECT` workaround does not fully resolve `UNEXPECTED_EOF_WHILE_READING` against US government servers running legacy TLS

The FEMA check passes on GitHub Actions (unrestricted internet, Python 3.11).

## Decision

FEMA API unavailability is treated as a WARN, not a FAIL:

- If FEMA returns a zone → Agent 3 uses it (auto-add Elevation Certificate if zone starts with A or V)
- If FEMA returns "UNAVAILABLE" → Agent 4 (Human Gate) flags the order for manual review (trigger 8: "FEMA API unavailable")
- `scripts/test_connections.py` marks the FEMA check as WARN (yellow) — does not block CI

The pipeline does NOT auto-add the Elevation Certificate when FEMA is unavailable. A human reviewer makes the flood zone determination.

## Consequences

### Positive
- Pipeline never blocked by network/TLS issues on a US government API
- Correct behavior: uncertain data → human review (not guessed auto-add)
- CI passes locally and on GitHub Actions regardless of network access

### Negative / Trade-offs
- Orders in flood zones that trigger FEMA failure go to human review (slower path)
- Legacy SSL context (`OP_LEGACY_SERVER_CONNECT`) in fema_client.py may need updating when Python/OpenSSL deprecates the flag

### Neutral
- FEMA API still called on every order — "UNAVAILABLE" is only returned on network errors
- Flood zone result stored in `processed_orders.is_flood_zone` column

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Block pipeline on FEMA failure | Corporate network would halt all local development |
| Cache flood zone results by lat/lng | Adds complexity; FEMA data updates periodically |
| Always flag if FEMA unavailable | Already the decision — this ADR documents it explicitly |

## Related
- `code/shared/core/fema_client.py` — SSL context + UNAVAILABLE return
- `code/shared/config/flag_triggers.py` — trigger 8 (FEMA unavailable)
- `memory.md` → Agent 4 flag trigger #8
- `scripts/test_connections.py` — FEMA check uses `check_warn()`
