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

Supported commands (typed in Teams channel or as reply to a bot notification):
  APPROVE                         — approve the single pending order (error if 0 or >1)
  APPROVE ALL                     — approve every pending order
  APPROVE <id> [<id2> ...]        — approve one or more specific orders
  REJECT                          — reject the single pending order (error if 0 or >1)
  REJECT ALL [reason]             — reject every pending order with optional reason
  REJECT <id> [reason]            — reject a specific order with optional reason

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

# Statuses that may be approved/rejected by a human reviewer
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
    invalid — not found or wrong status
    """
    valid, invalid = [], []
    for oid in order_ids:
        row = get_order_by_id(oid)
        if not row:
            invalid.append(f"{oid} (not found — check spelling)")
        elif row.get("status") not in _APPROVABLE_STATUSES:
            status = row.get("status", "unknown")
            invalid.append(f"{oid} (status={status} — not pending approval)")
        else:
            valid.append(oid)
    return valid, invalid


def _get_all_pending() -> list[str]:
    """Return all order IDs currently pending approval (flagged + awaiting_approval)."""
    flagged  = get_all_flagged_orders()
    awaiting = get_all_awaiting_orders()
    return [r["order_id"] for r in flagged + awaiting]


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
        action         = cmd["action"]
        order_ids      = cmd["order_ids"]   # list[str] or None for bare/all variants
        reason         = cmd["reason"]
        sender         = cmd["sender"]
        cmd_dt         = cmd["created_at_dt"]
        parent_msg_id  = cmd.get("parent_message_id")  # set when command came as thread reply

        log.info("cmd action=%s order_ids=%s sender=%s dry_run=%s",
                 action, order_ids, sender, dry_run)

        # ── Sender whitelist ──────────────────────────────────────────────────
        sender_first = (sender or "").split()[0].lower()
        if sender_first not in APPROVED_SENDERS:
            authorized = ", ".join(s.capitalize() for s in APPROVED_SENDERS)
            warn = (
                f"<strong>'{sender}'</strong> is not authorized to approve or reject estimates.<br>"
                f"Only <strong>{authorized}</strong> can use APPROVE/REJECT commands in this channel."
            )
            if not dry_run:
                send_confirmation(warn, "orange", parent_message_id=parent_msg_id)
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
            if action == "approve_bare":
                _do_approve_bare(sender, summary, process_approval_reply, parent_msg_id)

            elif action == "approve_all":
                _do_approve_all(sender, summary, process_approval_reply, parent_msg_id)

            elif action == "approve":
                _do_approve_multi(order_ids or [], sender, summary, process_approval_reply, parent_msg_id)

            elif action == "reject_bare":
                _do_reject_bare(sender, reason, summary, process_approval_reply, parent_msg_id)

            elif action == "reject_all":
                _do_reject_all(sender, reason, summary, process_approval_reply, parent_msg_id)

            elif action == "reject":
                _do_reject(order_ids or [], sender, reason, summary, process_approval_reply, parent_msg_id)

        except AgentError as exc:
            msg = f"Could not process <strong>{action}</strong>: {exc}"
            send_confirmation(msg, "orange", parent_message_id=parent_msg_id)
            summary["failed"] += 1
            log.error("command failed action=%s error=%s", action, exc)

        if cmd_dt > newest_dt:
            newest_dt = cmd_dt

    if not dry_run and newest_dt > since:
        _save_last_polled(newest_dt)

    # ── Batch summary: report any orders still pending after this poll cycle ──
    # Always posted as a NEW top-level message (no parent_message_id) so it is
    # visible in the channel feed regardless of which thread the user replied to.
    # This handles the case where pending orders span multiple notification threads.
    if not dry_run and (summary["approved"] > 0 or summary["rejected"] > 0):
        still_pending = _get_all_pending()
        if still_pending:
            id_list = "<br>".join(f"&nbsp;&nbsp;<strong>{oid}</strong>" for oid in still_pending[:10])
            suffix  = f"<br>&nbsp;&nbsp;...+{len(still_pending)-10} more" if len(still_pending) > 10 else ""
            msg = (
                f"<strong>{len(still_pending)} order(s) still pending — action required:</strong><br>"
                f"{id_list}{suffix}<br><br>"
                f"Reply to any notification thread or type here:<br>"
                f"&nbsp;&nbsp;<strong>APPROVE &lt;id&gt;</strong> &nbsp;or&nbsp; "
                f"<strong>REJECT &lt;id&gt; &lt;reason&gt;</strong>"
            )
            # parent_message_id=None → top-level post, always visible in channel feed
            send_confirmation(msg, "blue", parent_message_id=None)
            log.info("batch summary: %d still pending after this cycle", len(still_pending))

    log.info("poll complete found=%d approved=%d rejected=%d failed=%d",
             summary["found"], summary["approved"], summary["rejected"], summary["failed"])
    return summary


# ── Action handlers ───────────────────────────────────────────────────────────

def _do_approve_bare(sender: str, summary: dict, process_fn, parent_msg_id: str | None) -> None:
    """Handle bare APPROVE (no IDs specified) — auto-detect the single pending order."""
    targets = _get_all_pending()

    if not targets:
        send_confirmation("No orders are currently pending approval.", "blue", parent_message_id=parent_msg_id)
        log.info("approve_bare: nothing pending")
        return

    if len(targets) > 1:
        id_list = ", ".join(targets[:10])
        suffix  = f" ... (+{len(targets) - 10} more)" if len(targets) > 10 else ""
        msg = (
            f"<strong>{len(targets)} orders</strong> are pending approval — please specify which ones:<br>"
            f"&nbsp;&nbsp;<strong>APPROVE ALL</strong> — approve everything<br>"
            f"&nbsp;&nbsp;<strong>APPROVE {id_list}{suffix}</strong> — approve specific orders"
        )
        send_confirmation(msg, "orange", parent_message_id=parent_msg_id)
        log.info("approve_bare: %d pending — asked sender to specify", len(targets))
        return

    # Exactly 1 pending — treat same as APPROVE <id>
    _do_approve_multi(targets, sender, summary, process_fn, parent_msg_id)


def _do_approve_all(sender: str, summary: dict, process_fn, parent_msg_id: str | None) -> None:
    targets = _get_all_pending()

    if not targets:
        send_confirmation("No orders are currently pending approval.", "blue", parent_message_id=parent_msg_id)
        log.info("approve_all: nothing pending")
        return

    send_confirmation(
        f"<strong>{sender}</strong> approving ALL <strong>{len(targets)}</strong> pending order(s):<br>"
        f"<strong>{', '.join(targets)}</strong><br>"
        f"Processing now...",
        "green",
        parent_message_id=parent_msg_id,
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

    msg = (
        f"<strong>{sender}</strong> approved ALL <strong>{len(approved_ids)}</strong> order(s):<br>"
        f"<strong>{', '.join(approved_ids)}</strong><br>"
        f"Estimates will be sent."
    )
    if failed_ids:
        msg += f"<br><strong>Warnings:</strong> {', '.join(failed_ids)}"
    send_confirmation(msg, "green", parent_message_id=parent_msg_id)
    log.info("approve_all done approved=%d failed=%d", len(approved_ids), len(failed_ids))


def _do_approve_multi(
    order_ids: list[str],
    sender: str,
    summary: dict,
    process_fn,
    parent_msg_id: str | None,
) -> None:
    if not order_ids:
        send_confirmation("APPROVE command received but no order IDs provided.", "orange", parent_message_id=parent_msg_id)
        return

    valid, invalid = _validate_order_ids(order_ids)

    if invalid:
        warn = "Cannot process the following IDs:<br>" + "<br>".join(f"&nbsp;&nbsp;{e}" for e in invalid)
        send_confirmation(warn, "orange", parent_message_id=parent_msg_id)
        log.warning("invalid order_ids=%s", invalid)

    if not valid:
        return

    # Double confirmation for multiple orders: announce intent before processing
    if len(valid) > 1:
        send_confirmation(
            f"<strong>{sender}</strong> approving <strong>{len(valid)}</strong> order(s):<br>"
            f"<strong>{', '.join(valid)}</strong><br>"
            f"Processing now...",
            "green",
            parent_message_id=parent_msg_id,
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

    if len(approved_ids) == 1 and not failed_ids:
        send_confirmation(
            f"<strong>{sender}</strong> approved order <strong>{approved_ids[0]}</strong>.<br>"
            f"Estimate will be sent.",
            "green",
            parent_message_id=parent_msg_id,
        )
    elif approved_ids:
        msg = (
            f"<strong>{sender}</strong> approved <strong>{len(approved_ids)}</strong> order(s):<br>"
            f"<strong>{', '.join(approved_ids)}</strong><br>"
            f"Estimates will be sent."
        )
        if failed_ids:
            msg += f"<br><strong>Warnings:</strong> {', '.join(failed_ids)}"
        send_confirmation(msg, "green", parent_message_id=parent_msg_id)
    else:
        msg = "Could not approve any orders.<br><strong>Issues:</strong> " + ", ".join(failed_ids)
        send_confirmation(msg, "orange", parent_message_id=parent_msg_id)

    log.info("approve_multi done approved=%d failed=%d", len(approved_ids), len(failed_ids))


def _do_reject_bare(
    sender: str,
    reason: str | None,
    summary: dict,
    process_fn,
    parent_msg_id: str | None,
) -> None:
    """Handle bare REJECT (no ID specified) — auto-detect the single pending order."""
    targets = _get_all_pending()

    if not targets:
        send_confirmation("No orders are currently pending approval.", "blue", parent_message_id=parent_msg_id)
        log.info("reject_bare: nothing pending")
        return

    if len(targets) > 1:
        id_list = ", ".join(targets[:10])
        suffix  = f" ... (+{len(targets) - 10} more)" if len(targets) > 10 else ""
        msg = (
            f"<strong>{len(targets)} orders</strong> are pending — please specify which one to reject:<br>"
            f"&nbsp;&nbsp;<strong>REJECT ALL [reason]</strong> — reject everything<br>"
            f"&nbsp;&nbsp;<strong>REJECT {targets[0]} [reason]</strong> — reject a specific order"
        )
        send_confirmation(msg, "orange", parent_message_id=parent_msg_id)
        log.info("reject_bare: %d pending — asked sender to specify", len(targets))
        return

    _do_reject(targets[0], sender, reason, summary, process_fn, parent_msg_id)


def _do_reject_all(
    sender: str,
    reason: str | None,
    summary: dict,
    process_fn,
    parent_msg_id: str | None,
) -> None:
    targets = _get_all_pending()

    if not targets:
        send_confirmation("No orders are currently pending approval.", "blue", parent_message_id=parent_msg_id)
        log.info("reject_all: nothing pending")
        return

    reason_str = f"<strong>Reason:</strong> {reason}<br>" if reason else ""
    send_confirmation(
        f"<strong>{sender}</strong> rejecting ALL <strong>{len(targets)}</strong> pending order(s):<br>"
        f"<strong>{', '.join(targets)}</strong><br>"
        f"{reason_str}"
        f"Processing now...",
        "orange",
        parent_message_id=parent_msg_id,
    )

    rejected_ids, failed_ids = [], []
    for oid in targets:
        try:
            process_fn(oid, "reject")
            rejected_ids.append(oid)
            summary["rejected"] += 1
        except AgentError as exc:
            failed_ids.append(f"{oid} ({exc})")
            summary["failed"] += 1

    msg = (
        f"<strong>{sender}</strong> rejected ALL <strong>{len(rejected_ids)}</strong> order(s):<br>"
        f"<strong>{', '.join(rejected_ids)}</strong>."
    )
    if reason:
        msg += f"<br><strong>Reason:</strong> {reason}"
    if failed_ids:
        msg += f"<br><strong>Warnings:</strong> {', '.join(failed_ids)}"
    send_confirmation(msg, "red", parent_message_id=parent_msg_id)
    log.info("reject_all done rejected=%d failed=%d", len(rejected_ids), len(failed_ids))


def _do_reject(
    order_ids: list[str] | None,
    sender: str,
    reason: str | None,
    summary: dict,
    process_fn,
    parent_msg_id: str | None,
) -> None:
    if not order_ids:
        send_confirmation("REJECT command missing order ID.", "orange", parent_message_id=parent_msg_id)
        return

    valid, invalid = _validate_order_ids(order_ids)

    if invalid:
        warn = "Cannot process:<br>" + "<br>".join(f"&nbsp;&nbsp;{e}" for e in invalid)
        send_confirmation(warn, "orange", parent_message_id=parent_msg_id)

    if not valid:
        return

    rejected_ids, failed_ids = [], []
    for oid in valid:
        try:
            process_fn(oid, "reject")
            rejected_ids.append(oid)
            summary["rejected"] += 1
        except AgentError as exc:
            failed_ids.append(f"{oid} ({exc})")
            summary["failed"] += 1
            log.error("reject failed order=%s error=%s", oid, exc)

    if len(rejected_ids) == 1 and not failed_ids:
        msg = f"<strong>{sender}</strong> rejected order <strong>{rejected_ids[0]}</strong>."
        if reason:
            msg += f"<br><strong>Reason:</strong> {reason}"
        send_confirmation(msg, "red", parent_message_id=parent_msg_id)
    elif rejected_ids:
        msg = (
            f"<strong>{sender}</strong> rejected <strong>{len(rejected_ids)}</strong> order(s):<br>"
            f"<strong>{', '.join(rejected_ids)}</strong>."
        )
        if reason:
            msg += f"<br><strong>Reason:</strong> {reason}"
        if failed_ids:
            msg += f"<br><strong>Warnings:</strong> {', '.join(failed_ids)}"
        send_confirmation(msg, "red", parent_message_id=parent_msg_id)
    else:
        msg = "Could not reject any orders.<br><strong>Issues:</strong> " + ", ".join(failed_ids)
        send_confirmation(msg, "orange", parent_message_id=parent_msg_id)

    log.info("reject done rejected=%d failed=%d", len(rejected_ids), len(failed_ids))


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
