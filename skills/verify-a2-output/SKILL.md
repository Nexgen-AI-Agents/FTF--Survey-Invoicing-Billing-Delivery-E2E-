# verify-a2-output

Scan all `data_collected` and `invoice_draft_posted` orders for sentinel values
(`Unknown`, `N/A`, `None`, empty) in `client_name` and `property_address`.

Exits with code 0 (PASS) or 1 (FAIL). Safe to use in CI.

## How to run

```bash
python skills/verify-a2-output/run.py
```

## Output — PASS

```
======================================================================
  A2 OUTPUT VERIFICATION
  Checked 302 orders (statuses: data_collected, invoice_draft_posted)
======================================================================

  PASS — All 302 orders have valid client_name and property_address.

======================================================================
```

## Output — FAIL

```
======================================================================
  FAIL — 3 order(s) with sentinel/empty values:

  Order ID        Status                    Bad Fields
  -----------------------------------------------------------------
  1000283728      data_collected            client_name='Unknown'; property_address='Unknown'
  1000283564      data_collected            client_name='Unknown'
======================================================================
```

## When to use

- After any A2 bug fix — confirm the fix worked
- Before running A3 on a batch — make sure data quality is good
- Routine QA check: run weekly to catch regressions
- Part of `full-pipeline-retest` skill (called automatically)
