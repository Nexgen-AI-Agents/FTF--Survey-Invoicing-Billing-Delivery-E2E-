#!/usr/bin/env bash
# FTF Invoice Pipeline — Teams chat watcher (every 30 min).
#
# Reads new messages in the 'AI - Invoicing Agent' chat, LEARNS from the team's answers
# (stored in data/learned_rules.json, which A3 reads when pricing), and replies in the chat
# ONLY when there is something to say: what it learned, plus any clarification it needs
# before acting. Silent when there is no new input — no chat spam.
#
# Read-only w.r.t. the Approvals sheet; never emails a client. The flock stops two watcher
# runs overlapping (a slow LLM call could straddle the 30-min tick); writes to the learning
# memory are atomic (temp file + os.replace), so other agents writing it stay safe.
set -uo pipefail

DEPLOY_DIR="$HOME/FTF Invoicing Agent"
VENV_PY="$DEPLOY_DIR/.venv/bin/python"
LOG_DIR="$DEPLOY_DIR/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/teams_watch_$(date +%Y%m%d).log"

{
    echo "===== $(date -Is) teams watch START ====="
    cd "$DEPLOY_DIR" && flock -w 60 "$DEPLOY_DIR/data/.learning.lock" \
        "$VENV_PY" scripts/teams_watch.py
    echo "===== $(date -Is) teams watch END (rc=$?) ====="
} >> "$LOG" 2>&1

# Keep 14 days of watcher logs.
find "$LOG_DIR" -name 'teams_watch_*.log' -mtime +14 -delete 2>/dev/null || true
