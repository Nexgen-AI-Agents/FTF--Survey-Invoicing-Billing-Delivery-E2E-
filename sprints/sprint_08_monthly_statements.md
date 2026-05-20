# Sprint 8 — Agents 15–17: Monthly Statement Loop

## Overview

| Field | Value |
|-------|-------|
| Goal | 1st of every month — compile all B2B orders, generate Excel + PDF statement, deliver via MS Teams + email |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | [sprint_07_ar_followup.md](sprint_07_ar_followup.md) — needs `core/ftf_client.py` Books methods, `core/claude_client.py`; requires Wyatt + Jessica Recording 11 for prompt |
| Outputs | `agent_15_statement_generator.py`, `agent_16_statement_reviewer.py`, `agent_17_statement_sender.py`, `config/prompts/statement_generator.txt`, Excel + PDF statement confirmed delivered |

---

## Tasks

- [ ] `agents/monthly_statements/agent_15_statement_generator.py` — compile B2B orders via `openpyxl` (Excel) + `reportlab` (PDF)
- [ ] `agents/monthly_statements/agent_16_statement_reviewer.py` — validate all orders present, no duplicates, amounts correct
- [ ] `agents/monthly_statements/agent_17_statement_sender.py` — send to master billing email (fallback: most recent order email) + Teams to Ryan/Wyatt/Jessica
- [ ] `config/prompts/statement_generator.txt` — populated from Wyatt + Jessica Recording 11
- [ ] Test: sample statement generated for test B2B company

---

## Statement Content

Each statement includes: Order Number, Service Type, Date, Amount, Payment Status, Balance Due Total.

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| All B2B orders for period included — no gaps | 🔲 | |
| No duplicate orders in statement | 🔲 | |
| Amounts match FTF Books | 🔲 | |
| Excel file opens correctly | 🔲 | |
| PDF file opens correctly | 🔲 | |
| Sent to master billing email (or fallback) | 🔲 | |
| Teams message to Ryan/Wyatt/Jessica with attachments | 🔲 | |
| Validation failure → statement held, Ryan alerted | 🔲 | |

---

## Blockers

**Wyatt + Jessica Recording 11 (monthly statement process) must be completed before `config/prompts/statement_generator.txt` can be written.**

---

## Decisions Made

_Log here as they happen._

---

## Completion Brief

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 9:**
