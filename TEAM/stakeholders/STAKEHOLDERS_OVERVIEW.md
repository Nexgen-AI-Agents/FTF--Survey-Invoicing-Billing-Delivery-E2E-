# Stakeholder AI Agents — Overview

> **RULE: Always consult the AI agent FIRST. Only escalate to the real human if the AI agent cannot answer confidently.**
> This layer exists to protect real stakeholders from routine questions during builds.

---

## What This Layer Is

Every human stakeholder has a parallel AI agent that encodes their domain knowledge. These AI agents:
- Live in `TEAM/stakeholders/` and are always available during any sprint
- Answer questions from Dev, QA, Architecture, and Business Analyst agents
- Act as the first line of SME consultation — no need to wait for a real human
- Do NOT replace real humans at milestone sign-offs

---

## Distinction — AI Agent vs. Human Role Card

Both types of files exist. They are completely different things.

| Human Role Card (what the human does) | AI Agent (consultable knowledge clone) |
|---------------------------------------|----------------------------------------|
| `TEAM/leadership/prateek_cto.md` | `TEAM/stakeholders/prateek.md` |
| `TEAM/leadership/ryan_wyatt.md` | `TEAM/stakeholders/ryan.md` + `wyatt.md` |
| `TEAM/sme/robert.md` | `TEAM/stakeholders/robert.md` |
| `TEAM/sme/mark.md` | `TEAM/stakeholders/mark.md` |
| `TEAM/ar/jessica_ar_specialist.md` | `TEAM/stakeholders/jessica.md` |

**Human role cards** define responsibilities, authority, and workflows for the real person.
**AI agent files** (this folder) define what knowledge the AI has and when to consult it.

---

## Org Chart Position

```
TIER 0   — Human Principals (Real Humans — milestone sign-offs only)
             Prateek | Ryan | Robert | Mark | Jessica | Wyatt

TIER 0.5 — Stakeholder AI Agents  ← YOU ARE HERE
             Prateek AI | Ryan AI | Robert AI | Mark AI | Jessica AI | Wyatt AI

TIER 1   — AI Leadership (Dev Manager, QA Manager, Product Owner, Project Manager)
TIER 2   — AI Architecture (Enterprise Architect, IT Infra, DevOps, Prompt Engineer, Security)
TIER 3   — AI Business & Design (Business Analyst, UI/UX Designer)
TIER 4   — AI SME References (human role card files — distinct from this folder)
TIER 5   — AI Dev (Senior Dev, Junior Dev)
TIER 6   — AI QA (Senior QA, Junior QA, QE Manual, QE Automation)
```

---

## Escalation Chain (Updated)

```
Junior Dev / Junior QA
    ↓
Senior Dev / Senior QA
    ↓
Dev Manager / QA Manager
    ↓
Prateek AI  ← consult first
    ↓ (if AI cannot answer)
Real Prateek
    ↓ (if business sign-off needed)
Ryan AI / Wyatt AI  ← consult first
    ↓ (if AI cannot answer or milestone reached)
Real Ryan / Real Wyatt
```

---

## When to Consult AI Agent vs. Real Human

| Situation | Use AI Agent | Use Real Human |
|-----------|-------------|----------------|
| Code standard question | Yes | No |
| Architecture pattern question | Yes | No |
| "Would this estimate pass Robert's review?" | Yes | No |
| "Does this reminder tone match Jessica's process?" | Yes | No |
| Sprint milestone sign-off | No | Yes — required |
| Production GO/NO-GO | No | Yes — required |
| First 5 real estimates review (Sprint 11) | No | Yes — required |
| New external dependency not in BRD | No | Yes — required |
| AI agent gives contradictory/uncertain answer | No | Yes — escalate immediately |

---

## Agent Status: ACTIVE vs. STUB

| Status | Meaning | Reliability |
|--------|---------|-------------|
| **ACTIVE** | Built from existing docs (BRD, memory.md, recordings) — fully reliable | High |
| **STUB** | Built from BRD + existing docs only — recordings not yet received | Medium — answers current doc knowledge, may miss nuance |

**Stubs still answer.** They know the BRD, service names, pricing, and confirmed decisions. They just haven't been enriched with the recording sessions yet.

---

## Enrichment Process — How STUBs Become ACTIVE

When a recording arrives:
1. Read the recording transcript
2. Update the agent's **Knowledge Base** section with key decisions and patterns from the recording
3. Change agent **Status** from `STUB` to `ACTIVE`
4. Push to GitHub

| Agent | Enrichment Source | Sprint When Available |
|-------|------------------|-----------------------|
| Prateek AI | Existing docs — already ACTIVE | Now |
| Ryan AI | Sprint 6 demo feedback | Sprint 6 |
| Robert AI | Recordings 1–8 (estimate generation) | Pre-Sprint 1 |
| Mark AI | Recordings 1–8 | Pre-Sprint 1 |
| Jessica AI | Recording 10 (AR follow-up) | Pre-Sprint 7 |
| Wyatt AI | Recording 11 (monthly statements) | Pre-Sprint 8 |

---

## Agent Files in This Folder

| File | Person | Status | Consult For |
|------|--------|--------|-------------|
| [prateek.md](prateek.md) | Prateek (CTO) | ACTIVE | Architecture, standards, build order, ADRs |
| [ryan.md](ryan.md) | Ryan (Decision Maker) | STUB | Business rules, estimate tone, output quality |
| [robert.md](robert.md) | Robert (Operations SME) | STUB | Service classification, flag triggers, FTF standards |
| [mark.md](mark.md) | Mark (Field Ops SME) | STUB | Edge cases, unusual properties, field workflow |
| [jessica.md](jessica.md) | Jessica (AR Lead) | STUB | Reminder tones, escalation logic, exclusion list |
| [wyatt.md](wyatt.md) | Wyatt (Oversight) | STUB | Statement format, B2B delivery, oversight standards |
