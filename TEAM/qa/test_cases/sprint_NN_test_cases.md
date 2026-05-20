# Sprint NN — Test Cases Template

> Copy this file to `sprint_[number]_test_cases.md` and fill it in.
> Senior QA writes this BEFORE development starts (shift-left testing).
> Junior QA executes Section 1. Senior QA executes Sections 2–3.

---

## Sprint Info

| Field | Value |
|-------|-------|
| Sprint | Sprint NN — Name |
| Agents | Agent NN, Agent NN |
| Written by | Senior QA |
| Date written | YYYY-MM-DD |
| Dev start date | YYYY-MM-DD |
| QA start date | YYYY-MM-DD |

---

## Section 1 — Happy Path (Junior QA)

| TC# | Test Case | Input | Expected Output | Pass/Fail | Notes |
|-----|-----------|-------|----------------|-----------|-------|
| TC-01 | | | | | |
| TC-02 | | | | | |
| TC-03 | | | | | |

---

## Section 2 — Edge Cases (Senior QA)

| TC# | Test Case | Input / Condition | Expected Behavior | Pass/Fail | Notes |
|-----|-----------|-------------------|-------------------|-----------|-------|
| TC-10 | API returns empty list | `orders = []` | No crash, no output, log entry written | | |
| TC-11 | API timeout | Simulate timeout | Retry N times, then fail gracefully | | |
| TC-12 | Missing env variable | Remove key from `.env` | Clear startup error, not silent | | |
| TC-13 | | | | | |

---

## Section 3 — Security (Senior QA)

| TC# | Check | Pass/Fail | Notes |
|-----|-------|-----------|-------|
| TC-20 | No credentials in committed files | | |
| TC-21 | All SQL parameterized | | |
| TC-22 | No `eval()` / `exec()` / `shell=True` | | |
| TC-23 | No sensitive data in logs | | |

---

## Results Summary

| Section | Total TCs | Passed | Failed | Blocked |
|---------|-----------|--------|--------|---------|
| Section 1 (Happy Path) | | | | |
| Section 2 (Edge Cases) | | | | |
| Section 3 (Security) | | | | |
| **Total** | | | | |

**QA recommendation:** PASS / FAIL / BLOCKED

**Notes:**
