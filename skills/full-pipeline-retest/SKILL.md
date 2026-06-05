# full-pipeline-retest

End-to-end retest for specific orders: shows before/after pipeline status diff,
runs A2 → A3 directly, then verifies output quality.

Use this after any A2/A3 bug fix to confirm the fix works on real orders.

## How to run

```bash
# Retest 3 specific orders
python skills/full-pipeline-retest/run.py \
  --orders 1000283728,1000283564,1000283486

# Retest all invoice_needed orders currently in the sheet
python skills/full-pipeline-retest/run.py --from-status invoice_needed

# Dry-run: show the plan without executing pipeline steps
python skills/full-pipeline-retest/run.py \
  --orders 1000283728 \
  --dry-run
```

## What it does

1. **Before snapshot** — runs `pipeline-status` skill
2. **A2 data collection** — calls `collect_for_order()` for each order
3. **A3 invoice compiler** — calls A3's `run()` for all `data_collected` orders
4. **Verify output** — runs `verify-a2-output` skill (PASS/FAIL)
5. **After snapshot** — shows what changed

## Requirements

Must be run with the correct virtual environment active (same one the pipeline uses).
All env vars from `.env` must be set (MYSQL_*, ANTHROPIC_API_KEY, etc.).

## When to use

- After fixing A2 or A3 — retest affected orders end-to-end
- Prateek says "rerun these orders after the fix"
- Before committing a fix — verify it works on real data
