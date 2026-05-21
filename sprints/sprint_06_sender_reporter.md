# Sprint 6 — Agent 8: Sender + Agent 9: Reporter ⭐

## Overview

| Field | Value |
|-------|-------|
| Goal | AI sends validated estimate with 6–13 min random delay; daily digest to all stakeholders via MS Teams. MILESTONE: first full end-to-end estimate on staging. |
| Status | 🔲 Not Started |
| Dates | TBD |
| Reads From | [sprint_05_reviewer.md](sprint_05_reviewer.md) — needs validated estimate + invoice line items; needs `core/ftf_client.py` (`create_invoice`, `send_invoice`, `mark_estimate_sent`) |
| Outputs | `agent_08_sender.py`, `agent_09_reporter.py`, `config/prompts/reporter.txt`, confirmed estimate in Ryan's inbox, daily Teams digest |

---

## Tasks

- [ ] `agents/estimate_generation/agent_08_sender.py` — create invoice → random delay → send → mark sent → log
- [ ] `agents/estimate_generation/agent_09_reporter.py` — daily digest from DB → Claude summary → Teams post
- [ ] `config/prompts/reporter.txt`
- [ ] Full chain integration test (all 9 agents end-to-end on staging)

---

## Test Results

| Check | Status | Notes |
|-------|--------|-------|
| Estimate received in Ryan's inbox | 🔲 | Ryan confirms it looks professional |
| Random delay 6–13 min applied | 🔲 | |
| Change order clause visible in email | 🔲 | |
| `estimate_sent=true` marked in FTF CRM | 🔲 | |
| Invoice created in FTF Books | 🔲 | |
| Daily digest received on MS Teams | 🔲 | |
| Full chain: order → detect → classify → price → write → review → send | 🔲 | |

---

## Milestone Sign-Off

**Ryan must confirm:** test estimate received, looks correct and professional → GO for staging tests.

---

## Blockers

_None._

---

## Decisions Made

_Log here as they happen._

---

## Stakeholder Testing

| Role | Person | What They Test | Required? |
|------|--------|----------------|-----------|
| CTO | Prateek | Full chain integration test, delay applied, FTF CRM marked sent | Yes |
| Decision Maker | Ryan | Open test estimate in inbox — confirm it looks professional, correct, and the change order clause is visible. **Must sign off before Sprint 7.** | Yes — MILESTONE |
| Operations SME | Robert / Mark | Confirm estimate content and format match FTF standards | Yes |
| Business Stakeholders | Jessica, Wyatt | Review daily Teams digest format | Optional |

---

## Completion Brief

- **Built:**
- **Tests:**
- **Changed from plan:**
- **Carry forward for Sprint 7:**
