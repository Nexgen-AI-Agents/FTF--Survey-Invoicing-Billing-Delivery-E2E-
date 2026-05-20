# Issue Tracker — FTF Agentic AI OS

## Status Lifecycle

```
OPEN → IN DEV → DEV COMPLETE → QA JUNIOR → QA SENIOR → QA MANAGER → RELEASED → CLOSED
                                      ↑____________________________|
                                      (QA FAIL at any level → back to IN DEV)
```

## Severity Definitions

| Severity | Meaning |
|----------|---------|
| **BLOCKER** | Cannot proceed to next sprint. Stops all work on this sprint now. |
| **CRITICAL** | Must fix before release. Does not block other sprint work. |
| **MAJOR** | Significant regression or incorrect behavior. Should fix in current sprint. |
| **MINOR** | Cosmetic or low-impact. Tracked but not sprint-blocking. |

---

## Open Issues

| ID | Sprint | Severity | Title | Assigned | Status | Opened | Notes |
|----|--------|----------|-------|----------|--------|--------|-------|
| — | — | — | No issues yet | — | — | — | — |

---

## Closed Issues

| ID | Sprint | Severity | Title | Resolved By | Closed | Resolution |
|----|--------|----------|-------|-------------|--------|------------|
| — | — | — | No closed issues yet | — | — | — |

---

## Issue ID Format

`I-NNN` — sequential. Example: `I-001`, `I-002`, `I-003`.

## How to Log a New Issue

Add a row to **Open Issues** with:
- **ID**: next sequential number
- **Sprint**: which sprint's code (e.g., Sprint 0)
- **Severity**: BLOCKER / CRITICAL / MAJOR / MINOR
- **Title**: one-line description of the problem
- **Assigned**: `junior_dev`, `senior_dev`, or `dev_manager`
- **Status**: `OPEN`
- **Opened**: YYYY-MM-DD
- **Notes**: exact input that caused it + what happened + what was expected

## How to Close an Issue

Move the row to **Closed Issues** and fill in Resolved By, Closed date, and Resolution.
