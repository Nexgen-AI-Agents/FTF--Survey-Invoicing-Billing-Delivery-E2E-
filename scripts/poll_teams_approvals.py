"""
poll_teams_approvals.py — Poll the FTF-Approvals Teams channel for APPROVE/REJECT commands.

Reads the last 50 messages from the channel via Microsoft Graph API.
Processes any new APPROVE / APPROVE ALL / REJECT commands since the last run.
Sends a confirmation back to the channel for each command processed.

Security:
  - Only Robert, Ryan, or Prateek (first-name match, case-insensitive) can approve/reject.
  - Unauthorized senders get a warning posted to the channel.
  - Invalid or misspelled order IDs get a warning per ID.
  - Multiple order IDs: bot confirms (pre + post) before processing.

Usage:
    python scripts/poll_teams_approvals.py
    python scripts/poll_teams_approvals.py --since-hours 2   # look back 2h if no state
    python scripts/poll_teams_approvals.py --dry-run          # parse without DB writes

State: last processed timestamp stored in loop_state DB table (primary) and
       poll_state.json (backup/fallback).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

from config.settings import APPROVED_SENDERS
from core.db import get_all_awaiting_orders, get_all_flagged_orders, get_order_by_id
from core.exceptions import AgentError
from core.logger import get_logger
from core.teams_graph_client import check_for_approvals, send_confirmation

log = get_logger("poll_teams_approvals")

_STATE_FILE     = Path(__file__).parent / "poll_state.json"
_POLL_LOOP_NAME = "poll_teams_approvals"

# Statuses that may be approved by a human reviewer
_APPROVABLE_STATUSES = {"awaiting_approval", "flagged", "priced"}


# ── State persistence (DB primary, file fallback) ─────────────────────────────

def _load_last_polled() -> datetime | None:
    """Return datetime of last processed message. Checks DB first, then file."""
    try:
        from core.db import get_loop_state
        state = get_loop_state(_POLL_LOOP_NAME)
        if state and state.get("last_run_at"):
            lr = state["last_run_at"]
            if isinstance(lr, datetime):
                return lr if lr.tzinfo else lr.replace(tzinfo=timezone.utc)
            dt = datetime.fromisoformat(str(lr))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass  # table may not exist on first run — fall through to file

    if not _STATE_FILE.exists():
        return None
    try:
        data = json.loads(_STATE_FILE.read_text())
        ts   = data.get("last_processed_at")
        return datetime.fromisoformat(ts) if ts else None
    except Exception:
        return None


def _save_last_polled(dt: datetime) -> None:
    """Persist last processed timestamp to DB (primary) and file (fallback)."""
    try:
        from core.db import save_loop_state
        save_loop_state(_POLL_LOOP_NAME, "completed", last_run_at=dt)
    except Exception as exc:
        log.warning("could not save poll state to DB: %s", exc)

    try:
        _STATE_FILE.write_text(json.dumps({"last_processed_at": dt.isoformat()}))
    except Exception as exc:
        log.warning("could not save poll state file: %s", exc)


# ── Order ID validation ───────────────────────────────────────────────────────

def _validate_order_ids(order_ids: list[str]) -> tuple[list[str], list[str]]:
    """Split order_ids into (valid, invalid).

    valid   — order exists in DB with an approvable status
    invalid — not found or wrong status (with reason appended as ":reason")
    """
    valid, invalid = [], []
    for oid in order_ids:
        row = get_order_by_id(oid)
        if not row:
            invalid.append(f"{oid} (not found -- check spelling)")
        elif row.get("status") not in _APPROVABLE_STATUSES:
            status = row.get("status", "unknown")
            invalid.append(f"{oid} (status={status} -- not pending approval)")
        else:
            valid.append(oid)
    return valid, invalid


# ── Main poll ─────────────────────────────────────────────────────────────────

def run_poll(since_hours: int = 2, dry_run: bool = False) -> dict:
    """Poll the channel and process APPROVE/REJECT commands.

    since_hours — look-back window when no stored state
    dry_run     — parse and log without writing to DB or sending confirmations
    Returns summary: {found, approved, rejected, failed, dry_run}
    """
    last_polled = _load_last_polled()
    if last_polled:
        since = last_polled
        log.info("polling since last_processed=%s", since.isoformat())
    else:
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        log.info("no stored state -- polling last %dh", since_hours)

    try:
        commands = check_for_approvals(since=since)
    except AgentError as exc:
        log.error("Teams channel poll failed: %s", exc)
        return {"found": 0, "approved": 0, "rejected": 0, "failed": 1, "dry_run": dry_run}

    summary = {"found": len(commands), "approved": 0, "rejected": 0, "failed": 0, "dry_run": dry_run}

    if not commands:
        log.info("poll complete: no approval commands found")
        return summary

    from sprint_03_human_gate.agents.agent_04_human_gate import process_approval_reply  # type: ignore[import]

    newest_dt = since

    for cmd in commands:
        action    = cmd["action"]
        order_ids = cmd["order_ids"]   # list[str] or None for approve_all
        reason    = cmd["reason"]
        sender    = cmd["sender"]
        cmd_dt    = cmd["created_at_dt"]

        log.info("cmd action=%s order_ids=%s sender=%s dry_run=%s",
                 action, order_ids, sender, dry_run)

        # ── Sender whitelist ──────────────────────────────────────────────────
        sender_first = (sender or "").split()[0].lower()
        if sender_first not in APPROVED_SENDERS:
            authorized = ", ".join(s.capitalize() for s in APPROVED_SENDERS)
            warn = (
                f"[WARNING] '{sender}' is not authorized to approve or reject estimates. "
                f"Only {authorized} can use APPROVE/REJECT commands in this channel."
            )
            if not dry_run:
                send_confirmation(warn, "orange")
            log.warning("unauthorized sender=%s", sender)
            if cmd_dt > newest_dt:
                newest_dt = cmd_dt
            continue

        if dry_run:
            print(f"[DRY RUN] {action} | order_ids={order_ids} | sender={sender}")
            if cmd_dt > newest_dt:
                newest_dt = cmd_dt
            continue

        # ── Process command ───────────────────────────────────────────────────
        try:
            if action == "approve_all":
                _do_approve_all(sender, summary, process_approval_reply)

            elif action == "approve":
                _do_approve_multi(order_ids or [], sender, summary, process_approval_reply)

            elif action == "reject":
                oid = (order_ids or [None])[0]
                _do_reject(oid, sender, reason, summary, process_approval_reply)

        except AgentError as exc:
            msg = f"[WARNING] Could not process {action}: {exc}"
            send_confirmation(msg, "orange")
            summary["failed"] += 1
            log.error("command failed action=%s error=%s", action, exc)

        if cmd_dt > newest_dt:
            newest_dt = cmd_dt

    if not dry_run and newest_dt > since:
        _save_last_polled(newest_dt)

    log.info("poll complete found=%d approved=%d rejected=%d failed=%d",
             summary["found"], summary["approved"], summary["rejected"], summary["failed"])
    return summary


# ── Action handlers ───────────────────────────────────────────────────────────

def _do_approve_all(sender: str, summary: dict, process_fn) -> None:
    flagged  = get_all_flagged_orders()
    awaiting = get_all_awaiting_orders()
    targets  = [r["order_id"] for r in flagged + awaiting]

    if not targets:
        send_confirmation(f"[INFO] {sender}: no orders are pending approval right now.", "green")
        log.info("approve_all: nothing pending")
        return

    send_confirmation(
        f"[CONFIRM] {sender} approved ALL {len(targets)} pending order(s): "
        f"{', '.join(targets)}. Processing now...",
        "green",
    )

    approved_ids, failed_ids = [], []
    for oid in targets:
        try:
            process_fn(oid, "approve")
            approved_ids.append(oid)
            summary["approved"] += 1
        except AgentError as exc:
            failed_ids.append(f"{oid} ({exc})")
            summary["failed"] += 1

    msg = f"[APPROVED] {sender} approved ALL {len(approved_ids)} order(s): {', '.join(approved_ids)}."
    if failed_ids:
        msg += f" Warnings: {', '.join(failed_ids)}"
    send_confirmation(msg, "green")
    log.info("approve_all done approved=%d failed=%d", len(approved_ids), len(failed_ids))


def _do_approve_multi(order_ids: list[str], sender: str, summary: dict, process_fn) -> None:
    if not order_ids:
        send_confirmation("[WARNING] APPROVE command received but no order IDs provided.", "orange")
        return

    valid, invalid = _validate_order_ids(order_ids)

    if invalid:
        warn = "[WARNING] Cannot process: " + ", ".join(invalid)
        send_confirmation(warn, "orange")
        log.warning("invalid order_ids=%s", invalid)

    if not valid:
        return

    # Double confirmation for multiple orders: announce intent before processing
    if len(valid) > 1:
        send_confirmation(
            f"[CONFIRM] {sender} is approving {len(valid)} order(s): "
            f"{', '.join(valid)}. Processing now...",
            "green",
        )

    approved_ids, failed_ids = [], []
    for oid in valid:
        try:
            process_fn(oid, "approve")
            approved_ids.append(oid)
            summary["approved"] += 1
        except AgentError as exc:
            failed_ids.append(f"{oid} ({exc})")
            summary["failed"] += 1
            log.error("approve failed order=%s error=%s", oid, exc)

    # Final confirmation (second confirmation for multi, only confirmation for single)
    if len(approved_ids) == 1 and not failed_ids:
        send_confirmation(
            f"[APPROVED] {sender} approved order {approved_ids[0]}. Estimate will be sent.",
            "green",
        )
    elif approved_ids:
        msg = f"[APPROVED] {sender} approved {len(approved_ids)} order(s): {', '.join(approved_ids)}. Estimates will be sent."
        if failed_ids:
            msg += f" Warnings: {', '.join(failed_ids)}"
        send_confirmation(msg, "green")
    else:
        send_confirmation(
            f"[WARNING] Could not approve any orders. Issues: {', '.join(failed_ids)}",
            "orange",
        )

    log.info("approve_multi done approved=%d failed=%d", len(approved_ids), len(failed_ids))


def _do_reject(order_id: str | None, sender: str, reason: str | None, summary: dict, process_fn) -> None:
    if not order_id:
        send_confirmation("[WARNING] REJECT command missing order ID.", "orange")
        return

    row = get_order_by_id(order_id)
    if not row:
        send_confirmation(
            f"[WARNING] Order '{order_id}' not found -- check spelling and try again.",
            "orange",
        )
        log.warning("reject: order not found order_id=%s", order_id)
        summary["failed"] += 1
        return

    if row.get("status") not in _APPROVABLE_STATUSES:
        status = row.get("status", "unknown")
        send_confirmation(
            f"[WARNING] Order {order_id} cannot be rejected -- current status is '{status}'.",
            "orange",
        )
        log.warning("reject: wrong status order=%s status=%s", order_id, status)
        summary["failed"] += 1
        return

    process_fn(order_id, "reject")
    msg = f"[REJECTED] {sender} rejected order {order_id}."
    if reason:
        msg += f" Reason: {reason}"
    send_confirmation(msg, "red")
    summary["rejected"] += 1
    log.info("rejected order=%s reason=%s", order_id, reason)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Poll FTF-Approvals Teams channel")
    parser.add_argument("--since-hours", type=int, default=2,
                        help="Hours to look back when no stored state (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and log commands without writing to DB")
    args = parser.parse_args(argv)

    result = run_poll(since_hours=args.since_hours, dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
