#!/usr/bin/env bash
# FTF Invoice Pipeline — daily Teams report at 06:00 ET to the 'AI - Invoicing Agent' chat.
#
# Cron runs this at 10:00 AND 11:00 UTC; the Eastern-hour guard below makes it post EXACTLY
# once at 06:00 ET year-round (10:00 UTC during EDT, 11:00 UTC during EST). No flock needed —
# the report only reads the sheet + posts a Graph chat message; it never touches pipeline state.
set -uo pipefail

export TZ="America/New_York"
[ "$(date +%H)" != "06" ] && exit 0   # only fire at 6 AM Eastern

DEPLOY_DIR="$HOME/FTF Invoicing Agent"
VENV_PY="$DEPLOY_DIR/.venv/bin/python"
LOG_DIR="$DEPLOY_DIR/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily_report_$(date +%Y%m%d).log"

{
    echo "===== $(date -Is) daily report START ====="
    cd "$DEPLOY_DIR/code/sprint_11_invoice_pipeline" && "$VENV_PY" daily_report.py
    echo "===== $(date -Is) daily report END (rc=$?) ====="
} >> "$LOG" 2>&1
