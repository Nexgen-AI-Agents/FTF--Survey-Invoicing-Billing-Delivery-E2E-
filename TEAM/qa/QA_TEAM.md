# QA Team — FTF Agentic AI OS

## Team Structure

| Role | Agent File | Model | Primary Responsibility |
|------|-----------|-------|----------------------|
| QA Manager | `agents/qa_manager.md` | Sonnet | Final sign-off, release approval, spawns QA agents |
| Senior QA | `agents/senior_qa.md` | Sonnet | Integration testing, edge cases, regression testing |
| Junior QA | `agents/junior_qa.md` | Haiku or Sonnet | Happy path testing, basic functional checks |
| QE Manual | `agents/qe_manual.md` | Sonnet or Haiku | Manual exploratory testing, UX validation of human-facing outputs |
| QE Automation | `agents/qe_automation.md` | Sonnet or Haiku | Automated regression suite, test coverage, CI/CD integration |

---

## Model Selection Rule

| Model | When to Use |
|-------|------------|
| **Haiku** | Simple checks — reading files, running predefined tests, formatting reports |
| **Sonnet** | Complex testing — edge case design, integration analysis, security review |
| **Opus** | NEVER. Blocked at org level. |

---

## QA Flow (Tiered — Each Level Must Pass Before Next)

```
Dev Manager approves code
        ↓
Junior QA — happy path + basic functional tests
QE Manual — exploratory + UX validation          (runs in parallel with Junior QA)
        ↓  (FAIL → back to IN DEV)
Senior QA — edge cases + integration + regression
QE Automation — automated regression suite       (runs in parallel with Senior QA)
        ↓  (FAIL → back to IN DEV)
Manager QA — final sign-off + release approval
        ↓  (FAIL → back to IN DEV)
RELEASED to staging / production
```

No level can be skipped. A failure at any level sends the item back to `IN DEV`.

---

## Spawn Rules (QA Manager only)

- **Spawn QE Manual**: Every sprint with human-facing outputs (estimate emails, AR reminders, monthly statements)
- **Spawn QE Automation**: Sprint 1+ — builds automated regression suite incrementally each sprint
- **Spawn additional Senior QA** when: sprint has 5+ test cases requiring edge case analysis
- **Spawn Security QA** (Senior QA specialist): Sprint 10+ (staging prep) and Sprint 11+ (prod prep)
- **Spawn Performance QA** (Senior QA specialist): Sprint 11–12 (load/stress testing)
- Max concurrent QA agents: Manager + 2 Senior, OR 1 Senior + 2 Junior + QE Manual + QE Automation

---

## Reading Protocol (every QA agent, every task)

1. `CLAUDE.md` → `memory.md`
2. `TEAM/qa/QA_TEAM.md` → `TEAM/qa/QA_CHECKLIST.md` → `TEAM/qa/QA_learning.md`
3. Active sprint file (acceptance criteria section)
4. `TEAM/dev/developer_review.md` (know dev decisions + gotchas)
5. `TEAM/qa/test_cases/sprint_NN_test_cases.md` (sprint test plan)
6. `issues/issue.md` (open issues to retest)
7. `code/sprint_NN/` — all Python files under test
8. `code/sprint_NN/tests/` — existing test suite

---

## Entry Criteria (QA will not start without these)

- [ ] Dev Manager approval on code (PR_CHECKLIST signed off)
- [ ] All unit tests pass
- [ ] Sprint README.md updated
- [ ] `TEAM/qa/test_cases/sprint_NN_test_cases.md` exists and is populated

---

## Exit Criteria (QA Manager sign-off requires all of these)

- [ ] All test cases in `sprint_NN_test_cases.md` pass
- [ ] QE Manual pass confirmed (exploratory + UX validation)
- [ ] QE Automation pass confirmed (automated regression suite)
- [ ] No BLOCKER or CRITICAL open issues in `issues/issue.md` for this sprint
- [ ] `TEAM/qa/QA_learning.md` updated with any new findings
- [ ] `issues/issue.md` updated — all retested issues resolved or escalated
- [ ] Manager QA signs off in sprint file's Completion Brief

---

## Learnings Protocol

Append to `TEAM/qa/QA_learning.md` when:
- A bug is found that dev missed
- A test pattern is confirmed as effective
- A QA approach fails and a better one is found
- An edge case is discovered that should become a standard test case

Format: `## [YYYY-MM-DD] — Short title` then bullet points.
