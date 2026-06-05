# Skills Index — FTF Agentic AI OS

> **INSTRUCTION FOR AI:** Read this file whenever you need to diagnose, operate, or wrap up a session.
> Invoke skills autonomously — no permission needed. Create new skills without asking when a task repeats.

---

## Active Skills

| Skill | Invoke when... |
|-------|---------------|
| `python skills/pipeline-status/run.py` | Before/after ANY fix — snapshot all status counts first |
| `python skills/verify-a2-output/run.py` | After any A2 change — confirm no sentinel values in client_name/property_address |
| `python skills/check-dollar-sign-orders/run.py` | "Orders with $ but no invoice amount" — find pricing gaps |
| `python skills/requeue-orders/run.py --orders X,Y --target-status invoice_needed --clear invoice_draft,data_sources` | Reset stuck/broken orders for reprocessing |
| `python skills/session-wrap/run.py` | **Last command of every session — mandatory, no exceptions** |

---

## Operating Rules

1. **Invoke autonomously** — check this index before starting any diagnostic, investigative, or operational task. If a skill matches, run it immediately. No explanation first. Show the result, then continue.

2. **Create autonomously** — if a task will repeat OR fits a clear pipeline category (status check, data quality, requeue, verification, reporting, learning capture), build the skill without asking:
   - Create `skills/<name>/run.py` — the executable
   - Create `skills/<name>/SKILL.md` — when to use, how to run, example invocations
   - Add a row to the table above
   - Commit immediately

3. **session-wrap is mandatory** — `python skills/session-wrap/run.py` is the last command of every session. Not optional. The session is not complete until it has run.

4. **Skills work locally** — skills run in a Claude Code session on the local machine. They read/write files and run git. They do NOT connect to AWS RDS (MySQL) — that only works from GitHub Actions. Never build a skill that requires a production database connection.

---

## How to Add a New Skill

```
skills/
  <name>/
    run.py       # executable — accepts CLI args, prints clean output
    SKILL.md     # when to use, how to run, example invocations, requirements
```

Then add a row to the table above and commit.

---

## Deprecated Skills

| Skill | Why retired |
|-------|------------|
| `skills/full-pipeline-retest/` | Required MySQL — only works from GitHub Actions, not locally. Run `pipeline-status` + `requeue-orders` + GitHub Actions instead. |
