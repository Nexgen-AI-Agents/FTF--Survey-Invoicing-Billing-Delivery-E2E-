#!/usr/bin/env bash
# FTF Invoice Pipeline — twice-daily Teams report to the 'AI - Invoicing Agent' chat.
#
# Posts EVERY DAY at 12:00 PM ET (Midday) and 7:00 PM ET (Evening) so the team can monitor
# what the agent has done and by whom. Cron runs this at 16:00, 17:00, 23:00 AND 00:00 UTC;
# the Eastern-hour guard below makes it post EXACTLY once at each target time year-round
# (16/23 UTC during EDT, 17/00 UTC during EST). The run label (Midday vs Evening) and the
# look-back window are derived inside daily_report.py from the Eastern hour. No flock needed —
# the report only reads state + posts a chat message; it never touches pipeline state.
set -uo pipefail

export TZ="America/New_York"
H="$(date +%H)"
[ "$H" != "12" ] && [ "$H" != "19" ] && exit 0   # only fire at 12 PM and 7 PM Eastern
# (weekend skip removed — reports run every day)

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
