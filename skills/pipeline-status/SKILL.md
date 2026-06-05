# pipeline-status

Snapshot of all order statuses in `data/invoice_pipeline_state.xlsx`.
Run before and after any fix to see what moved.

## How to run

```bash
python skills/pipeline-status/run.py
```

## Output

```
============================================================
  PIPELINE STATUS SNAPSHOT  (403 total orders)
============================================================
  Status                         Count  Sample Order IDs
  ----------------------------------------------------------
  invoice_draft_posted             272  1000284561, 1000284560 (+270 more)
  details_missing                   82  1000283200, 1000283199 (+80 more)
  data_collected                    30  1000284100, 1000284099 (+28 more)
  ...
============================================================
```

## When to use

- Before any pipeline fix — get baseline counts
- After any pipeline fix — verify orders moved to expected status
- Whenever Prateek asks "how many orders are stuck?"
- At the start of every debugging session
