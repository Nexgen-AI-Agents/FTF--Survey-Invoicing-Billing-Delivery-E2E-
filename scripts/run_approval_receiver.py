"""
run_approval_receiver.py — Start the Teams Outgoing Webhook approval receiver.

This is a persistent service. Run it on your server once and leave it running.
Teams will POST to it whenever Robert or Ryan types APPROVE / REJECT in the channel.

Usage:
    python scripts/run_approval_receiver.py

Environment:
    TEAMS_OUTGOING_WEBHOOK_SECRET   — from Teams admin Outgoing Webhook registration
    TEAMS_APPROVAL_WEBHOOK_URL      — webhook URL of the approval channel
    APPROVAL_RECEIVER_HOST          — bind host (default 0.0.0.0)
    APPROVAL_RECEIVER_PORT          — bind port (default 5001)
    DB_*                            — PostgreSQL connection vars

Public URL required:
    Teams must reach this server over HTTPS. Options:
      - Reverse proxy (nginx) with Let's Encrypt cert on your VPS
      - ngrok for local dev:  ngrok http 5001
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.teams_approval_receiver import run_server

if __name__ == "__main__":
    run_server()
