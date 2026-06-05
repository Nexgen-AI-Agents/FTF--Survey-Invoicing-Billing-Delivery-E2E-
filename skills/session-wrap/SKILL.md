# session-wrap

End-of-session learning capture. Run this before ending every Claude Code session.

## How to run

```bash
# Show recent learnings, template, git status, and checklist
python skills/session-wrap/run.py

# Show the above AND append a new entry to learnings.md
python skills/session-wrap/run.py \
  --title "A3 skipped reset orders due to stale OneDrive rows" \
  --body "- Bug: A3 dedup guard checked OneDrive sheet but not invoice_draft\n- Fix: condition now requires invoice_draft to be set before skipping"
```

## What it does

1. Shows the last 2 entries in `learnings.md` (format reference + avoid duplicates)
2. Prints a blank dated template ready to fill
3. Shows `git status` — uncommitted files that should be committed before leaving
4. Prints the end-of-session checklist
5. Optionally appends a new entry to `learnings.md` (use `--title` + `--body`)

## When to use

- Before ending EVERY session — this is the last skill to run
- After fixing a bug — capture the pattern so the next session doesn't repeat it
- When Prateek says "remember this" or "teach the agents"
- When any rule, schema fact, or behavior was discovered that isn't already in learnings.md

## Why it exists

Skills don't help if the next session forgets to read them. This skill forces the
capture step: what did we learn, is it written down, is it committed? Without this
ritual, knowledge lives only in the session context and evaporates.
