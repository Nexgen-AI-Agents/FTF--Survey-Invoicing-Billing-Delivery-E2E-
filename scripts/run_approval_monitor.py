"""
run_approval_monitor.py — Smart continuous Teams approval monitor.

Polls the FTF-Approvals Teams channel every 60 seconds while there are orders
awaiting approval. When the queue is empty, it backs off to a 5-minute DB check
interval to avoid unnecessary API calls.

Usage:
    python scripts/run_approval_monitor.py            # run indefinitely
    python scripts/run_approval_monitor.py --dry-run  # parse commands, no DB writes
    python scripts/run_approval_monitor.py --once     # one cycle then exit
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

from core.db import get_all_awaiting_orders, save_loop_state
from core.logger import get_logger

sys.path.insert(0, os.path.dirname(__file__))
from poll_teams_approvals import run_poll

log = get_logger("run_approval_monitor")

LOOP_NAME = "approval_monitor"
ACTIVE_POLL_SECS = 60
IDLE_CHECK_SECS = 300


def _get_awaiting_count() -> int:
    try:
        return len(get_all_awaiting_orders())
    except Exception as exc:
        log.error("failed to query awaiting orders: %s", exc)
        return 0


def run_monitor(dry_run: bool = False, once: bool = False) -> None:
    log.info("=== Approval Monitor started ===")
    was_active = None

    while True:
        count = _get_awaiting_count()
        now = datetime.now(timezone.utc)

        if count > 0:
            if was_active is not True:
                log.info("ACTIVE: %d order(s) awaiting approval — polling Teams every %ds",
                         count, ACTIVE_POLL_SECS)
            save_loop_state(LOOP_NAME, "running", last_run_at=now)
            result = run_poll(since_hours=2, dry_run=dry_run)
            log.info("poll result: %s", result)
            was_active = True
            if once:
                break
            time.sleep(ACTIVE_POLL_SECS)
        else:
            if was_active is not False:
                log.info("IDLE: no orders awaiting approval — sleeping %ds between DB checks",
                         IDLE_CHECK_SECS)
            save_loop_state(LOOP_NAME, "idle", last_run_at=now)
            was_active = False
            if once:
                log.info("--once: no pending orders, exiting")
                break
            time.sleep(IDLE_CHECK_SECS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart continuous Teams approval monitor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse commands without writing to DB or sending confirmations")
    parser.add_argument("--once", action="store_true",
                        help="Run one cycle then exit")
    args = parser.parse_args()

    try:
        run_monitor(dry_run=args.dry_run, once=args.once)
    except KeyboardInterrupt:
        log.info("Monitor stopped by user (Ctrl+C)")
        save_loop_state(LOOP_NAME, "idle")


if __name__ == "__main__":
    main()
