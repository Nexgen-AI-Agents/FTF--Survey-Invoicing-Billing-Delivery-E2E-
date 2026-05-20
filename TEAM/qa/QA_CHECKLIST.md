# QA Master Checklist — FTF Agentic AI OS

Run this checklist on every sprint before QA Manager sign-off.
Junior QA runs Section 1. Senior QA runs Sections 1–3. Manager QA runs all sections.

---

## Section 1 — Functional (Junior QA)

### Happy Path Tests
- [ ] All sprint acceptance criteria from sprint file are met
- [ ] Each agent produces the correct output for a standard valid input
- [ ] All API calls return expected data format (checked against FTF API docs)
- [ ] DB writes are persisted and readable
- [ ] Logs are written correctly via `core/logger.py`

### Basic Validation
- [ ] Agent rejects invalid input gracefully (no crash)
- [ ] Agent handles empty API response without crash
- [ ] Environment variables load correctly; missing vars raise clear error
- [ ] No hardcoded credentials, model names, or prices visible in code

---

## Section 2 — Edge Cases & Integration (Senior QA)

### Edge Cases
- [ ] API timeout / rate limit — agent retries correctly or fails gracefully
- [ ] FTF API returns 0 orders — agent handles empty list
- [ ] FTF API returns malformed JSON — agent raises clear error and logs
- [ ] DB connection failure — agent raises clear error, does not corrupt state
- [ ] FEMA API unavailable — Agent 3 flags the order (does not auto-add elevation cert)
- [ ] Order with out-of-state property — Agent 4 flags correctly
- [ ] Service in ALWAYS_FLAG list — Agent 4 flags regardless of other logic
- [ ] Reviewer fails 3 correction loops — Agent 4 escalates to human

### Integration
- [ ] Agent N output format matches Agent N+1 input format
- [ ] Shared `core/` modules behave identically for all agents that call them
- [ ] DB schema constraints enforced (no duplicate orders, no orphan records)

### Regression
- [ ] Previously passing tests still pass after this sprint's code is added
- [ ] No imports from other sprint code folders (only `code/shared/`)

---

## Section 3 — Security (Senior QA + Manager QA)

- [ ] No credentials in any committed file (check `.env`, `.py`, `.txt`, `.md`)
- [ ] All SQL uses parameterized queries — no string concatenation in queries
- [ ] No `eval()`, `exec()`, `shell=True` in any code file
- [ ] `.env` is in `.gitignore` and not committed
- [ ] API keys sourced from environment variables only
- [ ] No sensitive data logged (no PATs, passwords, or PII in log output)

---

## Section 4 — Performance (Senior QA — Sprint 10+)

- [ ] FTF API call rate ≤ 1 per 60 minutes (rate limit respected)
- [ ] Max 500 orders processed per API call
- [ ] Estimate send delay is randomized 6–13 minutes (not 0)
- [ ] No blocking operations in the main loop (async or queue-based)

---

## Section 5 — Release Gate (Manager QA only)

- [ ] All sections above pass
- [ ] All test cases in `TEAM/qa/test_cases/sprint_NN_test_cases.md` pass
- [ ] No BLOCKER or CRITICAL issues open in `issues/issue.md` for this sprint
- [ ] Sprint file Completion Brief is filled in
- [ ] `CHANGELOG.md` updated with sprint release entry
- [ ] `TEAM/qa/QA_learning.md` updated with findings from this sprint
- [ ] Code pushed to GitHub and confirmed on remote
