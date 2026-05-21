# ADR-002 — Python 3.11+ Minimum Version

## Date
2026-05-21

## Status
`Accepted`

## Context

The system is developed on Windows 11 with Python 3.14 installed. GitHub Actions CI must match. Python 3.14 introduced a TLS regression that causes `UNEXPECTED_EOF_WHILE_READING` against FEMA's ArcGIS REST API (US government servers using legacy TLS). Corporate network also blocks hazards.fema.gov. The CI environment uses Python 3.11 in the workflow YAML.

## Decision

Require Python 3.11 as the minimum version. Development may use 3.11–3.14. GitHub Actions CI uses Python 3.11 explicitly.

Key version-specific features used:
- `match/case` — reserved for future classifier logic (Sprint 2)
- `tomllib` — not used
- Type hint union syntax (`X | Y`) — used throughout

## Consequences

### Positive
- Python 3.11 is stable, widely available, fully supported until Oct 2027
- GitHub Actions `python-version: "3.11"` is reliable
- Avoids Python 3.14 TLS regression with FEMA API

### Negative / Trade-offs
- 3.14 performance improvements not available in CI
- Windows dev on 3.14 may expose edge cases not caught in CI (as seen with FEMA)

### Neutral
- psycopg2-binary, httpx, anthropic SDK all support 3.11+
- Windows cp1252 encoding issue (Unicode in terminal) is a 3.14 display issue, not a code bug

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Python 3.14 everywhere | TLS regression breaks FEMA client in CI |
| Python 3.10 | No match/case; older type hint syntax |

## Related
- `requirements.txt` — all pinned versions compatible with 3.11+
- `.github/workflows/` — all 3 workflows pin `python-version: "3.11"`
- `code/shared/core/fema_client.py` — SSL workaround for 3.14
- `learnings.md` — FEMA SSL issue documented
