"""
run_email_monitor.py â€” Continuous runner for Agent 12 (Email Monitor).

Polls nesa@nexgenlogix.com via IMAP every N seconds.
When a customer approval email is found, converts the order quoteâ†’pending
and notifies the team via Teams.

Required env vars (add to .env or GitHub Actions secrets):
  IMAP_HOST      -- e.g. imap.gmail.com or outlook.office365.com
  IMAP_PORT      -- default 993 (IMAP SSL)
  IMAP_USER      -- nesa@nexgenlogix.com
  IMAP_PASSWORD  -- app password (not the login password)

Usage:
    python scripts/run_email_monitor.py             # poll every 120s
    python scripts/run_email_monitor.py --interval 60
    python scripts/run_email_monitor.py --once      # one run then exit
    python scripts/run_email_monitor.py --dry-run   # no DB writes

Deployment options:
    1. Local / VPS: run in a screen/tmux session or as a systemd service
    2. GitHub Actions: add a workflow that runs on schedule (e.g. every 10 min)
    3. Docker: add to docker-compose as a separate service

GitHub Actions example (add to .github/workflows/email_monitor.yml):
    on:
      schedule:
        - cron: "*/10 * * * *"   # every 10 minutes
    steps:
      - run: python scripts/run_email_monitor.py --once
        env:
          IMAP_HOST:     ${{ secrets.IMAP_HOST }}
          IMAP_PORT:     ${{ secrets.IMAP_PORT }}
          IMAP_USER:     ${{ secrets.IMAP_USER }}
          IMAP_PASSWORD: ${{ secrets.IMAP_PASSWORD }}
          # ... (all other secrets from poll_approval_monitor.yml)
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

from core.logger import get_logger

log = get_logger("run_email_monitor")

DEFAULT_INTERVAL = 120   # seconds between IMAP polls


def _check_env() -> list[str]:
    """Return list of missing required env vars."""
    required = ["IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD"]
    return [v for v in required if not os.getenv(v)]


def run_once(dry_run: bool = False) -> dict:
    """Run Agent 12 once and return the result dict."""
    from sprint_05_email_monitor.agents.agent_12_email_monitor import run  # type: ignore[import]
    return run(dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description="FTF Email Monitor â€” continuous IMAP poller")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help=f"Seconds between IMAP polls (default {DEFAULT_INTERVAL})")
    parser.add_argument("--once", action="store_true", help="Run one cycle then exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse emails, no DB writes or team notifications")
    args = parser.parse_args()

    missing = _check_env()
    if missing:
        print(f"ERROR: missing env vars: {', '.join(missing)}")
        print("Set them in .env or as GitHub Actions secrets. See script docstring for instructions.")
        sys.exit(1)

    imap_user = os.getenv("IMAP_USER", "?")
    print(f"FTF Email Monitor â€” watching {imap_user}")
    print(f"  Poll interval : {args.interval}s")
    print(f"  Dry run       : {args.dry_run}")
    print()

    try:
        while True:
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            try:
                result = run_once(dry_run=args.dry_run)
                converted     = result.get("converted", 0)
                refund_routed = result.get("refund_routed", 0)
                flagged       = result.get("flagged", 0)
                processed     = result.get("processed", 0)
                if processed:
                    print(
                        f"[{now}] processed={processed} converted={converted} "
                        f"refund_routed={refund_routed} flagged={flagged}"
                    )
            except Exception as exc:
                log.error("email monitor cycle failed: %s", exc)
                print(f"[{now}] ERROR: {exc}", flush=True)

            if args.once:
                break
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nEmail monitor stopped.")


if __name__ == "__main__":
    main()

