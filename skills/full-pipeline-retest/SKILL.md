# full-pipeline-retest — DEPRECATED

This skill is broken locally. AWS RDS is only accessible from GitHub Actions runners.
Running it locally times out on every A2/A3 call.

## What to use instead

| Goal | Command |
|------|---------|
| Requeue orders | `python skills/requeue-orders/run.py --orders X,Y --target-status invoice_needed --clear invoice_draft,data_sources` |
| Run pipeline | GitHub Actions → workflow_dispatch |
| Verify output | `python skills/verify-a2-output/run.py` |
| Before/after snapshot | `python skills/pipeline-status/run.py` |
