# data-quality-check

Full data quality scan of `pipeline_state.json`. Single command that shows everything.

## How to run

```bash
python skills/data-quality-check/run.py
```

## What it reports

- Status distribution table
- Phantom rows (non-numeric order_id — should always be 0)
- Orders with sentinel client_name ("Unknown", "N/A", empty)
- Orders with sentinel property_address
- Orders with null service_type
- Orders with null estimate_amount
- Orders with estimate_amount = 0
- Escalated orders count (escalate_flag=True) — informational
- Duplicate address groups — informational
- PASS / FAIL verdict

## Exit codes

- 0 = PASS (no data issues)
- 1 = FAIL (issues found — see report)

## When to use

- At the start of any investigation session
- After any pipeline fix — confirm no regressions
- When Prateek asks "what's broken in the Excel?"
- Before triggering a pipeline run — know the baseline state
