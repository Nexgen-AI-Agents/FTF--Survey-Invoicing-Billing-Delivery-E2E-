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
# run at the same time (both touch the state file + run A5/A6). The watcher WAITS
# for that lock (flock -w) rather than skipping the tick — see the comment below.
set -uo pipefail

export TZ="America/New_York"

DEPLOY_DIR="$HOME/FTF Invoicing Agent"
SPRINT_DIR="$DEPLOY_DIR/code/sprint_11_invoice_pipeline"
VENV_PY="$DEPLOY_DIR/.venv/bin/python"
LOG_DIR="$DEPLOY_DIR/logs"
LOCK_FILE="$DEPLOY_DIR/.pipeline.lock"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/watcher_$(date +%Y%m%d).log"

STAMP_FILE="$DEPLOY_DIR/.watcher_last_run"
ALERT_FILE="$DEPLOY_DIR/.watcher_starved_alert"
[ -f "$STAMP_FILE" ] || touch "$STAMP_FILE"

exec 9>"$LOCK_FILE"
# WAIT for the lock instead of failing fast. Both crons fire on the same minute boundaries and
# the pipeline entry sits first in the crontab, so it wins the race every single time; with
# `flock -n` the watcher was then skipped for the entire pipeline run. On 2026-08-24 that starved
# it for 68 min straight (last real run 15:55) while five human-approved orders sat undelivered.
# 240s < the 5-min tick, so at most one waiter can exist at a time — waiters cannot pile up.
if ! flock -w 240 9; then
    echo "$(date -Is) SKIP: A0 or prior watcher run still active (waited 240s)" >> "$LOG_FILE"
    # A starved watcher is invisible: approvals simply never get actioned and nobody is told.
    # Page a human if no watcher run has actually STARTED in 45 min (max one alert per hour).
    if [ -z "$(find "$STAMP_FILE" -newermt '45 minutes ago' 2>/dev/null)" ] \
       && [ -z "$(find "$ALERT_FILE" -newermt '60 minutes ago' 2>/dev/null)" ]; then
        echo "$(date -Is) STARVED: no watcher run in 45+ min — approvals are NOT being actioned" >> "$LOG_FILE"
        touch "$ALERT_FILE"
        "$VENV_PY" "$DEPLOY_DIR/scripts/notify_failure_email.py" \
            --workflow "FTF Approval Watcher STARVED (no run in 45+ min)" \
            --run-url "log $LOG_FILE on $(hostname)" || true
    fi
    exit 0
fi
touch "$STAMP_FILE"

{
    echo "===== $(date -Is) watcher run START ====="
    cd "$SPRINT_DIR" || { echo "FATAL: cannot cd to $SPRINT_DIR"; exit 1; }
    "$VENV_PY" run_excel_watcher.py
    rc=$?
    # Back up the live OneDrive sheet after every cycle (read-only download → backups/).
    ( cd "$DEPLOY_DIR" && "$VENV_PY" scripts/backup_sheet.py ) || echo "$(date -Is) sheet backup failed (non-fatal)"
    # Verify what actually reached the client. A 200 from FTF's deliver endpoint is not proof the
    # email was worth sending: on 2026-09-03 seventeen quotes went out with no price and no
    # invoice link and nobody noticed until the client complained the next day. This reads FTF's
    # own delivery log and pages if any nesa email in the last 2h is missing the amount or the
    # link. It never re-sends and never touches the sheet, and its exit code is deliberately
    # ignored so an audit problem can never mark a good watcher run as failed.
    ( cd "$DEPLOY_DIR" && "$VENV_PY" scripts/audit_sent_invoices.py --hours 2 --alert ) \
        || echo "$(date -Is) post-send audit reported incomplete emails (see errors above)"
    if [ "$rc" -ne 0 ]; then
        echo "$(date -Is) WATCHER FAILED rc=$rc -- sending alert"
        "$VENV_PY" "$DEPLOY_DIR/scripts/notify_failure_email.py" --workflow "FTF Server Approval Watcher" --run-url "log $LOG_FILE on $(hostname)" || true
    fi
    echo "===== $(date -Is) watcher run END (rc=$rc) ====="
} >> "$LOG_FILE" 2>&1
