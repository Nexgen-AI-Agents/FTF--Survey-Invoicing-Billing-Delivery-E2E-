"""
poll_teams_approvals.py — Poll the FTF-Approvals Teams channel for APPROVE/REJECT commands.

Reads recent messages + thread replies via Microsoft Graph API.
Processes APPROVE / REJECT commands and manages a confirmation state machine
for decision overrides (approve→reject or reject→approve).

Security:
  - Only Robert, Ryan, or Prateek (first-name, case-insensitive) can approve/reject.
  - Unauthorized senders get a channel warning.
  - Invalid/misspelled order IDs warned per ID.
  - Multiple IDs: bot confirms before + after.
  - Comma OR space separated IDs both work.
  - Multiple commands in one message supported (APPROVE A, B REJECT C reason).

Decision reversal (I-088):
  - Trying to reject an already-approved order → confirmation required.
  - Trying to approve an already-rejected order → confirmation required.
  - Bot posts: "Order X was approved. Change to REJECTED? Reply YES or NO."
  - Confirmation waits in pending_confirmations.json (TTL = 24h).
  - YES synonyms: yeah, yep, yup, sure, ok, go ahead, do it, proceed, ...
  - NO synonyms: nope, nah, cancel, keep it, never mind, don't, ...
  - Can repeat: if decision flips again, same confirmation flow repeats.

Usage:
    python scripts/poll_teams_approvals.py
    python scripts/poll_teams_approvals.py --since-hours 2
    python scripts/poll_teams_approvals.py --dry-run
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

from config.settings import APPROVED_SENDERS
from core.db import get_all_awaiting_orders, get_all_flagged_orders, get_order_by_id
from core.exceptions import AgentError
from core.logger import get_logger
from core.teams_graph_client import (
    _get_thread_replies,
    check_for_approvals,
    parse_confirmation_reply,
    send_confirmation,
)

log = get_logger("poll_teams_approvals")

_STATE_FILE        = Path(__file__).parent / "poll_state.json"
_PENDING_CONF_FILE = Path(__file__).parent / "pending_confirmations.json"
_POLL_LOOP_NAME    = "poll_teams_approvals"
_CONF_TTL_HOURS    = 24

# Statuses that can be approved/rejected immediately (no confirmation needed)
_APPROVABLE_STATUSES = {"awaiting_approval", "flagged", "priced"}
_REJECTABLE_STATUSES = {"awaiting_approval", "flagged", "priced"}

# Statuses that require an override confirmation before reversing
_REVERSIBLE_STATUSES = {"approved", "rejected"}


# ── State persistence ─────────────────────────────────────────────────────────

def _load_last_polled() -> datetime | None:
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
        pass
    if not _STATE_FILE.exists():
        return None
    try:
        data = json.loads(_STATE_FILE.read_text())
        ts   = data.get("last_processed_at")
        return datetime.fromisoformat(ts) if ts else None
    except Exception:
        return None


def _save_last_polled(dt: datetime) -> None:
    try:
        from core.db import save_loop_state
        save_loop_state(_POLL_LOOP_NAME, "completed", last_run_at=dt)
    except Exception as exc:
        log.warning("could not save poll state to DB: %s", exc)
    try:
        _STATE_FILE.write_text(json.dumps({"last_processed_at": dt.isoformat()}))
    except Exception as exc:
        log.warning("could not save poll state file: %s", exc)


# ── Pending confirmation state machine ───────────────────────────────────────

def _load_pending_confirmations() -> list[dict]:
    if not _PENDING_CONF_FILE.exists():
        return []
    try:
        return json.loads(_PENDING_CONF_FILE.read_text()).get("confirmations", [])
    except Exception:
        return []


def _save_pending_confirmations(confs: list[dict]) -> None:
    try:
        _PENDING_CONF_FILE.write_text(
            json.dumps({"confirmations": confs}, indent=2, default=str)
        )
    except Exception as exc:
        log.warning("could not save pending_confirmations: %s", exc)


def _add_pending_confirmation(
    order_ids: list[str],
    action: str,
    reason: str | None,
    sender: str,
    parent_msg_id: str | None,
    original_status: str,
) -> None:
    confs = _load_pending_confirmations()
    # Remove any existing confirmation for the same order IDs (replace with latest)
    confs = [c for c in confs if not any(o in c.get("order_ids", []) for o in order_ids)]
    confs.append({
        "id":                   str(uuid.uuid4()),
        "order_ids":            order_ids,
        "pending_action":       action,
        "reason":               reason,
        "sender":               sender,
        "original_status":      original_status,
        "parent_message_id":    parent_msg_id,
        "confirmation_posted_at": datetime.now(timezone.utc).isoformat(),
        "expires_at":           (datetime.now(timezone.utc) + timedelta(hours=_CONF_TTL_HOURS)).isoformat(),
    })
    _save_pending_confirmations(confs)


def _check_pending_confirmations(process_fn, summary: dict) -> None:
    """Scan thread replies for yes/no responses to pending override confirmations."""
    confs = _load_pending_confirmations()
    if not confs:
        return

    remaining  = []
    now        = datetime.now(timezone.utc)

    for conf in confs:
        order_ids      = conf["order_ids"]
        action         = conf["pending_action"]
        reason         = conf.get("reason")
        sender         = conf["sender"]
        parent_msg_id  = conf.get("parent_message_id")
        original_status = conf.get("original_status", "unknown")
        posted_at_str  = conf.get("confirmation_posted_at")
        expires_at_str = conf.get("expires_at")

        # Check expiry
        expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else now
        if now > expires_at:
            send_confirmation(
                f"Confirmation for <strong>{', '.join(order_ids)}</strong> expired "
                f"(no response within 24h).<br>"
                f"Decision remains <strong>{original_status}</strong>.<br>"
                f"Re-submit your APPROVE / REJECT command if you still want to change it.",
                "blue",
                parent_message_id=parent_msg_id,
            )
            log.info("confirmation expired order_ids=%s", order_ids)
            continue  # drop from list

        # Scan thread replies since confirmation was posted
        posted_at = datetime.fromisoformat(posted_at_str) if posted_at_str else now
        response          = None
        response_sender   = None

        if parent_msg_id:
            try:
                for reply in _get_thread_replies(parent_msg_id):
                    if reply["created_at_dt"] <= posted_at:
                        continue
                    parsed = parse_confirmation_reply(reply["text"])
                    if parsed:
                        response        = parsed
                        response_sender = reply["sender"]
                        break
            except Exception as exc:
                log.warning("could not scan replies for confirmation: %s", exc)

        if response == "yes":
            action_word = "approved" if action == "approve" else "rejected"
            send_confirmation(
                f"<strong>{response_sender}</strong> confirmed.<br>"
                f"Changing <strong>{', '.join(order_ids)}</strong> from "
                f"<strong>{original_status}</strong> → <strong>{action_word}</strong>...",
                "orange",
                parent_message_id=parent_msg_id,
            )
            done_ids, fail_ids = [], []
            for oid in order_ids:
                try:
                    process_fn(oid, action)
                    done_ids.append(oid)
                    summary["approved" if action == "approve" else "rejected"] += 1
                except AgentError as exc:
                    fail_ids.append(f"{oid} ({exc})")
                    summary["failed"] += 1

            color = "green" if action == "approve" else "red"
            msg = (
                f"Decision changed: <strong>{', '.join(done_ids)}</strong> → "
                f"<strong>{action_word}</strong>."
            )
            if fail_ids:
                msg += f"<br><strong>Warnings:</strong> {', '.join(fail_ids)}"
            send_confirmation(msg, color, parent_message_id=parent_msg_id)
            log.info("override confirmed action=%s orders=%s by=%s", action, done_ids, response_sender)
            # don't re-add to remaining

        elif response == "no":
            send_confirmation(
                f"Decision kept as <strong>{original_status}</strong> for "
                f"<strong>{', '.join(order_ids)}</strong>. No change made.",
                "blue",
                parent_message_id=parent_msg_id,
            )
            log.info("override cancelled order_ids=%s by=%s", order_ids, response_sender)
            # don't re-add to remaining

        else:
            remaining.append(conf)   # still waiting for a response

    _save_pending_confirmations(remaining)


# ── Order validation & categorisation ────────────────────────────────────────

def _validate_and_categorize(
    order_ids: list[str],
    action: str,            # "approve" or "reject"
) -> tuple[list[str], list[str], list[str]]:
    """Categorise order IDs into three buckets.

    Returns (immediate, needs_confirmation, invalid):
      immediate          — can be actioned right now (pending/flagged/priced status)
      needs_confirmation — previously decided (opposite direction) — requires user YES/NO
      invalid            — not found, already in same end-state, or wrong status
    """
    immediate         : list[str] = []
    needs_confirmation: list[str] = []
    invalid           : list[str] = []

    for oid in order_ids:
        row    = get_order_by_id(oid)
        status = (row or {}).get("status", "")

        if not row:
            invalid.append(f"{oid} (not found — check spelling)")
            continue

        if action == "approve":
            if status in _APPROVABLE_STATUSES:
                immediate.append(oid)
            elif status == "rejected":            # flip: rejected → approve
                needs_confirmation.append(oid)
            elif status == "approved":
                invalid.append(f"{oid} (already approved)")
            else:
                invalid.append(f"{oid} (status={status} — cannot approve)")

        elif action == "reject":
            if status in _REJECTABLE_STATUSES:
                immediate.append(oid)
            elif status == "approved":            # flip: approved → reject
                needs_confirmation.append(oid)
            elif status == "rejected":
                invalid.append(f"{oid} (already rejected)")
            else:
                invalid.append(f"{oid} (status={status} — cannot reject)")

    return immediate, needs_confirmation, invalid


def _post_override_confirmation(
    order_ids: list[str],
    action: str,
    reason: str | None,
    sender: str,
    original_status: str,
    parent_msg_id: str | None,
) -> None:
    """Post a YES/NO confirmation request for a decision reversal."""
    action_word    = "APPROVED" if action == "approve" else "REJECTED"
    original_word  = original_status.upper()
    ids_html       = ", ".join(f"<strong>{o}</strong>" for o in order_ids)
    send_confirmation(
        f"The following order(s) were previously <strong>{original_word}</strong>:<br>"
        f"{ids_html}<br><br>"
        f"Change decision to <strong>{action_word}</strong>?<br>"
        f"Reply <strong>YES</strong> to confirm or <strong>NO</strong> to keep it as {original_word}.",
        "orange",
        parent_message_id=parent_msg_id,
    )
    _add_pending_confirmation(order_ids, action, reason, sender, parent_msg_id, original_status)
    log.info("override confirmation requested action=%s orders=%s by=%s", action, order_ids, sender)


def _get_all_pending() -> list[str]:
    flagged  = get_all_flagged_orders()
    awaiting = get_all_awaiting_orders()
    return [r["order_id"] for r in flagged + awaiting]


# ── Main poll ─────────────────────────────────────────────────────────────────

def run_poll(since_hours: int = 2, dry_run: bool = False) -> dict:
    last_polled = _load_last_polled()
    since = last_polled or (datetime.now(timezone.utc) - timedelta(hours=since_hours))
    log.info("polling since=%s", since.isoformat())

    try:
        commands = check_for_approvals(since=since)
    except AgentError as exc:
        log.error("Teams channel poll failed: %s", exc)
        return {"found": 0, "approved": 0, "rejected": 0, "failed": 1, "dry_run": dry_run}

    summary = {"found": len(commands), "approved": 0, "rejected": 0, "failed": 0, "dry_run": dry_run}

    from sprint_03_human_gate.agents.agent_04_human_gate import process_approval_reply  # type: ignore[import]

    # ── Step 1: resolve any pending YES/NO confirmations first ───────────────
    if not dry_run:
        _check_pending_confirmations(process_approval_reply, summary)

    if not commands:
        log.info("poll complete: no approval commands found")
        return summary

    newest_dt = since

    for cmd in commands:
        action        = cmd["action"]
        order_ids     = cmd["order_ids"]
        reason        = cmd["reason"]
        sender        = cmd["sender"]
        cmd_dt        = cmd["created_at_dt"]
        parent_msg_id = cmd.get("parent_message_id")

        log.info("cmd action=%s order_ids=%s sender=%s dry_run=%s",
                 action, order_ids, sender, dry_run)

        # ── Sender whitelist ──────────────────────────────────────────────────
        sender_first = (sender or "").split()[0].lower()
        if sender_first not in APPROVED_SENDERS:
            authorized = ", ".join(s.capitalize() for s in APPROVED_SENDERS)
            warn = (
                f"<strong>'{sender}'</strong> is not authorized to approve or reject estimates.<br>"
                f"Only <strong>{authorized}</strong> can use APPROVE/REJECT commands."
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

    # ── Step 3: still-pending summary (top-level, always visible) ────────────
    if not dry_run and (summary["approved"] > 0 or summary["rejected"] > 0):
        still_pending = _get_all_pending()
        if still_pending:
            id_list = "<br>".join(f"&nbsp;&nbsp;<strong>{oid}</strong>" for oid in still_pending[:10])
            suffix  = f"<br>&nbsp;&nbsp;...+{len(still_pending)-10} more" if len(still_pending) > 10 else ""
            send_confirmation(
                f"<strong>{len(still_pending)} order(s) still pending — action required:</strong><br>"
                f"{id_list}{suffix}<br><br>"
                f"Reply <strong>APPROVE &lt;id&gt;</strong> or <strong>REJECT &lt;id&gt; &lt;reason&gt;</strong>",
                "blue",
                parent_message_id=None,   # top-level so it's always visible
            )
            log.info("batch summary: %d still pending", len(still_pending))

    log.info("poll complete found=%d approved=%d rejected=%d failed=%d",
             summary["found"], summary["approved"], summary["rejected"], summary["failed"])
    return summary


# ── Action handlers ───────────────────────────────────────────────────────────

def _do_approve_bare(sender, summary, process_fn, parent_msg_id):
    targets = _get_all_pending()
    if not targets:
        send_confirmation("No orders are currently pending approval.", "blue", parent_message_id=parent_msg_id)
        return
    if len(targets) > 1:
        id_list = ", ".join(targets[:10])
        suffix  = f" ...+{len(targets)-10} more" if len(targets) > 10 else ""
        send_confirmation(
            f"<strong>{len(targets)} orders</strong> pending — please specify:<br>"
            f"&nbsp;&nbsp;<strong>APPROVE ALL</strong><br>"
            f"&nbsp;&nbsp;<strong>APPROVE {id_list}{suffix}</strong>",
            "orange", parent_message_id=parent_msg_id,
        )
        return
    _do_approve_multi(targets, sender, summary, process_fn, parent_msg_id)


def _do_approve_all(sender, summary, process_fn, parent_msg_id):
    targets = _get_all_pending()
    if not targets:
        send_confirmation("No orders are currently pending approval.", "blue", parent_message_id=parent_msg_id)
        return
    send_confirmation(
        f"<strong>{sender}</strong> approving ALL <strong>{len(targets)}</strong> pending order(s):<br>"
        f"<strong>{', '.join(targets)}</strong><br>Processing now...",
        "green", parent_message_id=parent_msg_id,
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
        f"<strong>{', '.join(approved_ids)}</strong><br>Estimates will be sent."
    )
    if failed_ids:
        msg += f"<br><strong>Warnings:</strong> {', '.join(failed_ids)}"
    send_confirmation(msg, "green", parent_message_id=parent_msg_id)


def _do_approve_multi(order_ids, sender, summary, process_fn, parent_msg_id):
    if not order_ids:
        send_confirmation("APPROVE command received but no order IDs provided.", "orange", parent_message_id=parent_msg_id)
        return

    immediate, needs_conf, invalid = _validate_and_categorize(order_ids, "approve")

    if invalid:
        send_confirmation(
            "Cannot process:<br>" + "<br>".join(f"&nbsp;&nbsp;{e}" for e in invalid),
            "orange", parent_message_id=parent_msg_id,
        )
    if needs_conf:
        _post_override_confirmation(needs_conf, "approve", None, sender, "rejected", parent_msg_id)
    if not immediate:
        return

    if len(immediate) > 1:
        send_confirmation(
            f"<strong>{sender}</strong> approving <strong>{len(immediate)}</strong> order(s):<br>"
            f"<strong>{', '.join(immediate)}</strong><br>Processing now...",
            "green", parent_message_id=parent_msg_id,
        )
    approved_ids, failed_ids = [], []
    for oid in immediate:
        try:
            process_fn(oid, "approve")
            approved_ids.append(oid)
            summary["approved"] += 1
        except AgentError as exc:
            failed_ids.append(f"{oid} ({exc})")
            summary["failed"] += 1

    if len(approved_ids) == 1 and not failed_ids:
        send_confirmation(
            f"<strong>{sender}</strong> approved order <strong>{approved_ids[0]}</strong>.<br>"
            f"Estimate will be sent.",
            "green", parent_message_id=parent_msg_id,
        )
    elif approved_ids:
        msg = (
            f"<strong>{sender}</strong> approved <strong>{len(approved_ids)}</strong> order(s):<br>"
            f"<strong>{', '.join(approved_ids)}</strong><br>Estimates will be sent."
        )
        if failed_ids:
            msg += f"<br><strong>Warnings:</strong> {', '.join(failed_ids)}"
        send_confirmation(msg, "green", parent_message_id=parent_msg_id)
    else:
        send_confirmation(
            "Could not approve any orders.<br><strong>Issues:</strong> " + ", ".join(failed_ids),
            "orange", parent_message_id=parent_msg_id,
        )


def _do_reject_bare(sender, reason, summary, process_fn, parent_msg_id):
    targets = _get_all_pending()
    if not targets:
        send_confirmation("No orders are currently pending approval.", "blue", parent_message_id=parent_msg_id)
        return
    if len(targets) > 1:
        send_confirmation(
            f"<strong>{len(targets)} orders</strong> pending — please specify which to reject:<br>"
            f"&nbsp;&nbsp;<strong>REJECT ALL [reason]</strong><br>"
            f"&nbsp;&nbsp;<strong>REJECT {targets[0]} [reason]</strong>",
            "orange", parent_message_id=parent_msg_id,
        )
        return
    _do_reject(targets, sender, reason, summary, process_fn, parent_msg_id)


def _do_reject_all(sender, reason, summary, process_fn, parent_msg_id):
    targets = _get_all_pending()
    if not targets:
        send_confirmation("No orders are currently pending approval.", "blue", parent_message_id=parent_msg_id)
        return
    reason_html = f"<strong>Reason:</strong> {reason}<br>" if reason else ""
    send_confirmation(
        f"<strong>{sender}</strong> rejecting ALL <strong>{len(targets)}</strong> pending order(s):<br>"
        f"<strong>{', '.join(targets)}</strong><br>{reason_html}Processing now...",
        "orange", parent_message_id=parent_msg_id,
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


def _do_reject(order_ids, sender, reason, summary, process_fn, parent_msg_id):
    if not order_ids:
        send_confirmation("REJECT command missing order ID.", "orange", parent_message_id=parent_msg_id)
        return

    immediate, needs_conf, invalid = _validate_and_categorize(order_ids, "reject")

    if invalid:
        send_confirmation(
            "Cannot process:<br>" + "<br>".join(f"&nbsp;&nbsp;{e}" for e in invalid),
            "orange", parent_message_id=parent_msg_id,
        )
    if needs_conf:
        _post_override_confirmation(needs_conf, "reject", reason, sender, "approved", parent_msg_id)
    if not immediate:
        return

    rejected_ids, failed_ids = [], []
    for oid in immediate:
        try:
            process_fn(oid, "reject")
            rejected_ids.append(oid)
            summary["rejected"] += 1
        except AgentError as exc:
            failed_ids.append(f"{oid} ({exc})")
            summary["failed"] += 1

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
        send_confirmation(
            "Could not reject any orders.<br><strong>Issues:</strong> " + ", ".join(failed_ids),
            "orange", parent_message_id=parent_msg_id,
        )
    log.info("reject done rejected=%d failed=%d", len(rejected_ids), len(failed_ids))


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Poll FTF-Approvals Teams channel")
    parser.add_argument("--since-hours", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = run_poll(since_hours=args.since_hours, dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
