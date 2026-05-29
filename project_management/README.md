# Project Management — FTF Agentic AI OS

> Maintained by: Claude Code (updated after every session with new work)
> Master tracker: `FTF_AI_OS_Project_Tracker.csv` (open in Excel)
> Last updated: 2026-05-29

---

## Folder Structure (Jira-style)

```
project_management/
├── README.md               ← this file
├── FTF_AI_OS_Project_Tracker.csv   ← MASTER Excel-compatible tracker
├── backlog/
│   └── items.md            ← not started, queued for future sprints
├── in_dev/
│   └── items.md            ← currently being coded
├── dev_done/
│   └── items.md            ← code complete, awaiting QA
├── qa_in_progress/
│   └── items.md            ← QA Junior / Senior / Manager running
├── qa_pass/
│   └── items.md            ← QA passed, awaiting UAT
├── uat_in_progress/
│   └── items.md            ← stakeholder UAT running
├── uat_pass/
│   └── items.md            ← UAT passed, ready for production
└── completed/
    └── items.md            ← shipped to production
```

---

## Status Lifecycle

```
BACKLOG → IN DEV → DEV DONE → QA IN PROGRESS → QA PASS → UAT IN PROGRESS → UAT PASS → COMPLETED
                                     ↑__________________________|
                                     (QA FAIL at any level → back to IN DEV)
```

---

## Item Types

| Type | Meaning |
|------|---------|
| `FEATURE` | New capability not previously designed |
| `CR` | Change Request — change to existing built/designed functionality |
| `BUG` | Defect in existing code |
| `TASK` | Infrastructure, setup, config, docs |
| `EPIC` | Sprint-level grouping of features/tasks |

---

## Priority Levels

| Priority | Meaning |
|----------|---------|
| `P0` | Blocker — stops all other work |
| `P1` | Critical — must ship in current sprint |
| `P2` | High — should ship in current sprint |
| `P3` | Medium — next sprint |
| `P4` | Low — future backlog |

---

## How to Update

Claude Code updates both `items.md` files and `FTF_AI_OS_Project_Tracker.csv` after every session.
When an item moves stages, move it in the relevant items.md AND update the Status column in the CSV.
