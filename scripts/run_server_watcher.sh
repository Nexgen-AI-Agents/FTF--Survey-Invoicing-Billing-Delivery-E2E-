#!/usr/bin/env bash
# FTF Invoice Pipeline — server-side APPROVAL WATCHER (single-runner deployment).
#
# Mirrors the retired excel_approval_watcher.yml: reads pending approvals from the
# OneDrive sheet (get_pending_approvals) and runs
#   A4 process_dispatch_input -> A5 invoice_finalizer -> A6 sender
# i.e. the actual approve -> create FTF invoice -> email-the-customer path. A0's
# own run_a4() is a no-op stub ("Teams retired"), so THIS script is what actions
# human approvals. Runs every 5 min via cron.
#
# Shares .pipeline.lock with run_server_pipeline.sh so A0 and the watcher never
# run at the same time (both touch the state file + run A5/A6). flock -n => skip
# this tick if the other is active; the next tick retries.
set -uo pipefail

export TZ="America/New_York"

DEPLOY_DIR="$HOME/FTF Invoicing Agent"
SPRINT_DIR="$DEPLOY_DIR/code/sprint_11_invoice_pipeline"
VENV_PY="$DEPLOY_DIR/.venv/bin/python"
LOG_DIR="$DEPLOY_DIR/logs"
LOCK_FILE="$DEPLOY_DIR/.pipeline.lock"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/watcher_$(date +%Y%m%d).log"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "$(date -Is) SKIP: A0 or prior watcher run still active" >> "$LOG_FILE"
    exit 0
fi

{
    echo "===== $(date -Is) watcher run START ====="
    cd "$SPRINT_DIR" || { echo "FATAL: cannot cd to $SPRINT_DIR"; exit 1; }
    "$VENV_PY" run_excel_watcher.py
    rc=$?
    # Back up the live OneDrive sheet after every cycle (read-only download → backups/).
    ( cd "$DEPLOY_DIR" && "$VENV_PY" scripts/backup_sheet.py ) || echo "$(date -Is) sheet backup failed (non-fatal)"
    if [ "$rc" -ne 0 ]; then
        echo "$(date -Is) WATCHER FAILED rc=$rc -- sending alert"
        "$VENV_PY" "$DEPLOY_DIR/scripts/notify_failure_email.py" --workflow "FTF Server Approval Watcher" --run-url "log $LOG_FILE on $(hostname)" || true
    fi
    echo "===== $(date -Is) watcher run END (rc=$rc) ====="
} >> "$LOG_FILE" 2>&1
