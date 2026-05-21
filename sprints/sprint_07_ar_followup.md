# Sprint 7 — Agents 10–14: AR Follow-Up Loop

## Overview

| Field | Value |
|-------|-------|
| Goal | Daily automated payment reminders — tone scales with overdue days, 90-day escalation to Ryan |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | [sprint_06_sender_reporter.md](sprint_06_sender_reporter.md) — needs `core/ftf_client.py` Books methods (`get_invoices`, `send_reminder`), `core/db.py` AR tables, `core/claude_client.py` |
| Outputs | `agent_10_ar_scanner.py`, `agent_11_scheduler.py`, `agent_12_reminder_writer.py`, `agent_13_ar_reviewer.py`, `agent_14_ar_sender.py`, `config/prompts/reminder_writer.txt` |

---

## Tasks

- [ ] `agents/ar_followup/agent_10_ar_scanner.py` — scan FTF Books for unpaid invoices
- [ ] `agents/ar_followup/agent_11_scheduler.py` — calculate reminder tier from days_overdue
- [ ] `agents/ar_followup/agent_12_reminder_writer.py` — generate personalized reminder per tone tier
- [ ] `agents/ar_followup/agent_13_ar_reviewer.py` — verify invoice still unpaid before sending
- [ ] `agents/ar_followup/agent_14_ar_sender.py` — send reminder, log, escalate at 90 days
- [ ] `config/prompts/reminder_writer.txt` — populated from Jessica's Recording 10

---

## Reminder Tiers

| Days Overdue | Tier | Tone |
|-------------|------|------|
| ≤ -5 | 1 | Friendly — "just a heads up" |
| -4 to -2 | 2 | Firm — "please arrange payment" |
| 0 | 3 | Direct — "payment is due today" |
| 1–89 | 4 | Urgent — every 3 days |
| ≥ 90 | 5 | Escalate to Ryan via Teams |

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| Friendly reminder at 5 days before due | 🔲 | |
| Firm reminder at 2–3 days before due | 🔲 | |
| Direct reminder on due date | 🔲 | |
| Urgent reminder every 3 days after due | 🔲 | |
| 90-day overdue → Teams escalation to Ryan | 🔲 | |
| Excluded client → no reminder sent | 🔲 | |
| Already-paid invoice → skipped | 🔲 | |

---

## Blockers

**Jessica's Recording 10 (AR follow-up process) must be completed before `config/prompts/reminder_writer.txt` can be written.**

---

## Decisions Made

_Log here as they happen._

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | All 5 reminder tiers fire correctly, exclusion list blocks sends, DB logging | Yes |
| AR Lead | Jessica | Read all 5 reminder tones — confirm language matches what she currently sends manually; confirm escalation format; approve exclusion list logic | Yes — she owns AR process |
| Decision Maker | Ryan | Confirm 90-day escalation alert format on Teams | Yes |
| Operations SME | Robert / Mark | Not involved this sprint | No |
| Oversight | Wyatt | Not involved this sprint | No |

---

## Completion Brief

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 8:**
