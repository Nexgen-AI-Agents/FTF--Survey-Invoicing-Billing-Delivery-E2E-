"""
poll_teams_approvals.py — Poll the FTF-Approvals Teams channel for APPROVE/REJECT commands.

Reads the last 50 messages from the channel via Microsoft Graph API.
Processes any new APPROVE / APPROVE ALL / REJECT commands since the last run.
Sends a confirmation back to the channel for each command processed.

No public URL. No ngrok. No Flask server. The pipeline calls this every cycle.

Usage:
    python scripts/poll_teams_approvals.py
    python scripts/poll_teams_approvals.py --since-hours 2   # only look at last 2h of messages
    python scripts/poll_teams_approvals.py --dry-run          # show commands without processing

State: last processed timestamp is stored in poll_state.json (gitignored).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))  # for sprint_03_human_gate

from core.db import get_all_awaiting_orders, get_all_flagged_orders
from core.exceptions import AgentError
from core.logger import get_logger
from core.teams_graph_client import check_for_approvals, send_confirmation

log = get_logger("poll_teams_approvals")

# State file — tracks last processed message timestamp to avoid re-processing
_STATE_FILE = Path(__file__).parent / "poll_state.json"


def _load_last_polled() -> datetime | None:
    """Return the datetime of the last successfully processed message, or None."""
    if not _STATE_FILE.exists():
        return None
    try:
        data = json.loads(_STATE_FILE.read_text())
        ts   = data.get("last_processed_at")
        return datetime.fromisoformat(ts) if ts else None
    except Exception:
        return None


def _save_last_polled(dt: datetime) -> None:
    """Persist the last processed message timestamp."""
    try:
        _STATE_FILE.write_text(json.dumps({"last_processed_at": dt.isoformat()}))
    except Exception as exc:
        log.warning("could not save poll state: %s", exc)


def run_poll(since_hours: int = 2, dry_run: bool = False) -> dict:
    """Poll the channel and process any APPROVE/REJECT commands.

    since_hours — look back this many hours for new messages (fallback if no state file)
    dry_run     — parse and log commands but do not write to DB or send confirmations
    Returns summary: {found, approved, rejected, failed, dry_run}
    """
    # Determine the cutoff datetime
    last_polled = _load_last_polled()
    if last_polled:
        since = last_polled
        log.info("polling since last_processed=%s", since.isoformat())
    else:
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        log.info("no state file — polling last %dh", since_hours)

    # Fetch commands from Teams channel
    try:
        commands = check_for_approvals(since=since)
    except AgentError as exc:
        log.error("Teams channel poll failed: %s", exc)
        return {"found": 0, "approved": 0, "rejected": 0, "failed": 1, "dry_run": dry_run}

    summary = {"found": len(commands), "approved": 0, "rejected": 0, "failed": 0, "dry_run": dry_run}

    if not commands:
        log.info("poll complete: no approval commands found")
        return summary

    # Import here to avoid circular imports at module level
    from sprint_03_human_gate.agents.agent_04_human_gate import process_approval_reply  # type: ignore[import]

    newest_dt = since

    for cmd in commands:
        action   = cmd["action"]
        order_id = cmd["order_id"]
        reason   = cmd["reason"]
        sender   = cmd["sender"]
        cmd_dt   = cmd["created_at_dt"]

        log.info("processing command action=%s order=%s sender=%s dry_run=%s",
                 action, order_id, sender, dry_run)

        if dry_run:
            print(f"[DRY RUN] {action} | order={order_id} | sender={sender}")
            if cmd_dt > newest_dt:
                newest_dt = cmd_dt
            continue

        try:
            if action == "approve_all":
                flagged  = get_all_flagged_orders()
                awaiting = get_all_awaiting_orders()
                targets  = [r["order_id"] for r in flagged + awaiting]

                if not targets:
                    send_confirmation(f"✅ {sender}: No orders pending approval right now.", "green")
                    log.info("approve_all: no orders pending")
                else:
                    approved_ids, failed_ids = [], []
                    for oid in targets:
                        try:
                            process_approval_reply(oid, "approve")
                            approved_ids.append(oid)
                            summary["approved"] += 1
                        except AgentError as exc:
                            failed_ids.append(f"{oid} ({exc})")
                            summary["failed"] += 1

                    msg = f"✅ {sender} approved ALL {len(approved_ids)} order(s): {', '.join(approved_ids)}"
                    if failed_ids:
                        msg += f"<br>⚠️ Could not approve: {', '.join(failed_ids)}"
                    send_confirmation(msg, "green")
                    log.info("approve_all complete approved=%d failed=%d", len(approved_ids), len(failed_ids))

            elif action == "approve":
                process_approval_reply(order_id, "approve")
                msg = f"✅ {sender} approved order {order_id}. Estimate will be sent."
                send_confirmation(msg, "green")
                summary["approved"] += 1
                log.info("approved order=%s", order_id)

            elif action == "reject":
                process_approval_reply(order_id, "reject")
                msg = f"🚫 {sender} rejected order {order_id}."
                if reason:
                    msg += f" Reason: {reason}"
                send_confirmation(msg, "red")
                summary["rejected"] += 1
                log.info("rejected order=%s reason=%s", order_id, reason)

        except AgentError as exc:
            msg = f"⚠️ Could not process {action} for {order_id}: {exc}"
            send_confirmation(msg, "orange")
            summary["failed"] += 1
            log.error("command failed action=%s order=%s error=%s", action, order_id, exc)

        if cmd_dt > newest_dt:
            newest_dt = cmd_dt

    # Persist the timestamp of the newest message processed
    if not dry_run and newest_dt > since:
        _save_last_polled(newest_dt)

    log.info(
        "poll complete found=%d approved=%d rejected=%d failed=%d",
        summary["found"], summary["approved"], summary["rejected"], summary["failed"],
    )
    return summary


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Poll FTF-Approvals Teams channel")
    parser.add_argument("--since-hours", type=int, default=2,
                        help="Hours to look back for messages if no state file (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and log commands without writing to DB")
    args = parser.parse_args(argv)

    result = run_poll(since_hours=args.since_hours, dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
