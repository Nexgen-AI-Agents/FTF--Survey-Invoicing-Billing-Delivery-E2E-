#!/usr/bin/env bash
# FTF Invoice Pipeline — server-side cron runner (single-runner deployment).
#
# Runs the full A0 orchestrator (A1 intake -> A3 draft-to-sheet -> A4-A6
# finalize/send) every 30 min on the prod server (FTF-NEAdmin-HA-01), which is
# the ONLY host that can reach the private RDS. This replaces the GitHub Actions
# invoice_pipeline / excel_approval_watcher / approval_poller workflows (disabled
# at cutover) so there is exactly one runner and one state file — no duplicate
# invoices or emails.
#
# - flock: only one run at a time; a 30-min tick is skipped if a run overruns.
# - TZ pinned to Eastern so all timestamps + any time-of-day logic match the
#   GitHub Actions behaviour this replaced. NOTE: A6 (sender v2) has NO send-time
#   window guard -- an approved invoice is emailed immediately, any hour.
# - All stdout/stderr -> daily log under <deploy>/logs/.
set -uo pipefail

export TZ="America/New_York"

DEPLOY_DIR="$HOME/FTF Invoicing Agent"
SPRINT_DIR="$DEPLOY_DIR/code/sprint_11_invoice_pipeline"
VENV_PY="$DEPLOY_DIR/.venv/bin/python"
LOG_DIR="$DEPLOY_DIR/logs"
LOCK_FILE="$DEPLOY_DIR/.pipeline.lock"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d).log"

# Single-instance guard — skip this tick if the previous run is still active.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "$(date -Is) SKIP: previous pipeline run still active" >> "$LOG_FILE"
    exit 0
fi

{
    echo "===== $(date -Is) pipeline run START ====="
    cd "$SPRINT_DIR" || { echo "FATAL: cannot cd to $SPRINT_DIR"; exit 1; }
    "$VENV_PY" -m agents.agent_a0_orchestrator
    rc=$?
    # Refresh the local dashboard JSON from the just-updated state store.
    ( cd "$DEPLOY_DIR" && "$VENV_PY" scripts/export_pipeline_json.py ) || echo "$(date -Is) export_pipeline_json failed (non-fatal)"
    # Never fail silently: alert a human on a non-zero rc (CI used to do this on failure).
    if [ "$rc" -ne 0 ]; then
        echo "$(date -Is) PIPELINE FAILED rc=$rc -- sending alert"
        "$VENV_PY" "$DEPLOY_DIR/scripts/notify_failure_email.py" --workflow "FTF Server Pipeline (A0)" --run-url "log $LOG_FILE on $(hostname)" || true
    fi
    echo "===== $(date -Is) pipeline run END (rc=$rc) ====="
} >> "$LOG_FILE" 2>&1
