# PR Checklist — FTF Agentic AI OS

Every piece of code must pass this checklist before Senior Dev review.
Junior Dev completes self-check. Senior Dev verifies before approving to Manager.

---

## Code Quality

- [ ] One agent = one file. No combined agents.
- [ ] No raw API/DB/LLM calls inside agent files — all through `code/shared/core/`
- [ ] No hardcoded credentials, model names, prices, or business rules
- [ ] No wildcard imports (`from x import *`)
- [ ] No `eval()`, `exec()`, or `shell=True`
- [ ] No swallowed exceptions (`except: pass`)
- [ ] All SQL uses parameterized queries
- [ ] Naming conventions followed (`snake_case`, `PascalCase`, `UPPER_SNAKE_CASE`)

---

## Testing

- [ ] Test file exists for every new agent file
- [ ] All external calls mocked in unit tests
- [ ] All tests pass (`pytest` returns 0 errors)
- [ ] At least one happy-path integration test (if sprint allows staging access)

---

## Structure

- [ ] Prompts in `code/shared/config/prompts/` — not inline
- [ ] Model names sourced from `code/shared/config/models.py`
- [ ] Flag triggers sourced from `code/shared/config/flag_triggers.py`
- [ ] Sprint README.md updated to reflect what was added

---

## Review Sign-Off

- [ ] Junior Dev self-check complete
- [ ] Senior Dev review complete (logic, edge cases, standards)
- [ ] Dev Manager approval (architecture fit, cross-sprint safety)
- [ ] No open BLOCKER or CRITICAL issues in `issues/issue.md` for this sprint

---

## Before Merge

- [ ] `TEAM/dev/developer_review.md` updated if any new learnings surfaced
- [ ] `issues/issue.md` updated — new issues added, resolved issues closed
- [ ] Code pushed to correct sprint branch or directly to master (Sprint 0 only)
