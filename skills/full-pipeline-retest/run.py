#!/usr/bin/env python3
"""full-pipeline-retest: DEPRECATED — requires MySQL access unavailable locally."""
print("""
DEPRECATED — full-pipeline-retest does not work locally.

AWS RDS (MySQL) is only accessible from GitHub Actions runners.
Running A2 or A3 locally will fail with a connection timeout.

To retest orders after a fix:
  1. Requeue:
       python skills/requeue-orders/run.py --orders X,Y \\
         --target-status invoice_needed --clear invoice_draft,data_sources
  2. Trigger pipeline via GitHub Actions workflow_dispatch
  3. After run completes, verify:
       python skills/verify-a2-output/run.py

For snapshot/diff only (works locally):
  python skills/pipeline-status/run.py
""")
