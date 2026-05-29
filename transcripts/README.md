# Transcripts — FTF Agentic AI OS

This folder stores all call transcripts between Prateek, Ryan, and other stakeholders.
Every transcript gets processed: only FTF-project-relevant points are extracted.

---

## Folder Structure

```
transcripts/
├── README.md          ← this file
├── raw/               ← original transcript files, untouched
└── extracted/         ← extracted project points only, one file per transcript
```

---

## Naming Convention

| Format | Example |
|--------|---------|
| `raw/YYYY-MM-DD_[people]_[topic].txt` | `2026-05-26_ryan-prateek_45min.txt` |
| `extracted/YYYY-MM-DD_[people]_extracted.md` | `2026-05-26_ryan-prateek_extracted.md` |

---

## Transcripts Index

| Date | File | People | Duration | Extracted | Status |
|------|------|---------|----------|-----------|--------|
| 2026-05-25 | [raw](raw/2026-05-25_ryan-prateek_agentic-ai-hermes-upsell.txt) | Ryan, Prateek | ~56 min | [extracted](extracted/2026-05-25_ryan-prateek_extracted.md) | ✅ Done |
| 2026-05-26 | [raw](raw/2026-05-26_ryan-prateek_45min.txt) | Ryan, Prateek | ~52 min | [extracted](extracted/2026-05-26_ryan-prateek_extracted.md) | ✅ Done |

---

## Extraction Rules (What to Pull vs. Skip)

### PULL — FTF-project relevant
- Business requirements Ryan states ("there should be an agent that...")
- Pricing rules, business logic, hard rules
- New features to build (becomes an issue in issues/issue.md)
- Decisions Ryan makes that override previous assumptions
- Blocked dependencies (waiting on Jessica, Robert, etc.)
- Architecture/strategy direction from Ryan's perspective
- Corrections to existing AI behavior ("50 orders a week → a lot of orders")
- Client-facing workflow changes

### SKIP — Not for this project
- Ryan's personal AI assistant plans (coffee, home automation, real estate)
- NGE internal staff/incentive discussions unrelated to FTF
- General business philosophy / motivational talk
- Tech stack discussions that aren't actionable now (future sprints only)
- Conversations about other clients (Poff's, etc.) unless they affect FTF architecture
- Small talk, scheduling, logistics of calls

---

## What Happens After Extraction

1. New actionable items → logged in `issues/issue.md` as new issue IDs
2. Business rules confirmed → added to `memory.md` Confirmed Decisions table
3. Hard rules (refunds, out-of-state, etc.) → added to `memory.md` + code if immediate
4. Dependencies clarified → update `memory.md` Open Dependencies table
5. CHANGELOG entry added

---

## How I Think About This (Being Prateek)

Every transcript has two layers:
1. **Ryan's layer** — what the business needs, what feels wrong, what the client will experience
2. **Prateek's layer** — what's technically possible, what sprint it belongs in, what's blocked

When processing a transcript I ask:
- What is Ryan actually asking for, underneath the words?
- Is this a rule (hard constraint) or a preference (configurable)?
- Does this break something already built?
- What sprint does this belong in — now, or after we have more data?
- Is there a dependency before this can be built?
- Does this change how I'd build something from scratch?

Prateek's operating style:
- Sprint-first: everything maps to a sprint or becomes a future sprint issue
- Automation-first: if something is manual, figure out how to automate it
- Data-driven: build it, run it, see the data, then tune
- Hard rules are non-negotiable — code them in, not just documented
- Everything goes to review first, then automate over time as confidence builds
