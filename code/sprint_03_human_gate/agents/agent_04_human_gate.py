import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone

from config.models import HUMAN_GATE_MODEL
from config.settings import APPROVAL_TIMEOUT_HOURS, FTF_ORDER_URL
from core.db import (
    get_all_awaiting_orders, get_all_flagged_orders,
    get_order_by_id, get_overdue_approvals, log_decision, save_order_state,
)
from core.exceptions import AgentError
from core.logger import get_logger
from core.teams_graph_client import (
    build_digest_html, check_for_approvals, send_channel_message, send_confirmation,
)

AGENT_NAME = "agent_04_human_gate"
log = get_logger(AGENT_NAME)

# Status constants for the human review lifecycle
STATUS_AWAITING = "awaiting_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


def notify_human(order_id: str) -> dict:
    """Send a Teams alert for a flagged order and advance status to awaiting_approval.

    Uses Graph API (teams_graph_client). No webhook URL required.
    Returns: dict with keys "order_id", "notified", "status".
    Raises AgentError if Graph API is not configured or send fails.
    """
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"notify_human: order {order_id} not found in processed_orders")

    amount     = db_row.get("estimate_amount")
    amount_str = f"${amount:,.2f}" if amount is not None else "TBD"
    link       = f"{FTF_ORDER_URL}/{order_id}"

    html = (
        f"<h3>FTF Estimate — Human Review Required</h3>"
        f"<p><b>@Robert @Ryan</b> — the following order has been flagged and requires your decision.</p>"
        f"<ul>"
        f"<li><b>Order:</b> <a href='{link}'>{order_id}</a></li>"
        f"<li><b>Service:</b> {db_row.get('service_type') or 'Unknown'}</li>"
        f"<li><b>County:</b> {db_row.get('property_county') or 'MISSING'}</li>"
        f"<li><b>Flag Reason:</b> {db_row.get('flag_reason') or 'see order'}</li>"
        f"<li><b>Estimate:</b> {amount_str}</li>"
        f"</ul>"
        f"<p>Reply: <code>APPROVE {order_id}</code> or <code>REJECT {order_id} reason</code></p>"
    )

    send_channel_message(html, subject=f"Order {order_id} — Review Required")

    save_order_state(
        order_id,
        status=STATUS_AWAITING,
        flagged_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        agent_name=AGENT_NAME,
        decision="notified",
        order_id=order_id,
        reason=db_row.get("flag_reason"),
        input_summary=f"service={db_row.get('service_type')} county={db_row.get('property_county')}",
        output_summary=f"Teams Graph API alert sent; status={STATUS_AWAITING}",
        model_used=HUMAN_GATE_MODEL,
    )

    log.info("human notified order=%s status=%s", order_id, STATUS_AWAITING)
    return {"order_id": order_id, "notified": True, "status": STATUS_AWAITING}


def check_approval(order_id: str) -> str:
    """Return the current human-review status for an order.

    Possible return values: "awaiting_approval", "approved", "rejected", or
    the raw status string from the DB if unknown.

    STUB — actual inbound approval mechanism is undefined until I-025 is resolved.
    For now: poll the DB status column. When Robert/Mark update it externally
    (manual DB edit, webhook callback, or Teams bot), this function will detect it.
    """
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"check_approval: order {order_id} not found")

    status = db_row.get("status", STATUS_AWAITING)
    log.debug("check_approval order=%s status=%s", order_id, status)
    return status


def process_approval_reply(order_id: str, decision: str) -> dict:
    """Record a human reviewer's approve or reject decision.

    Called by:
    - Teams bot callback (future I-025 full implementation)
    - CLI: python -m agents.agent_04_human_gate --approve ORD-001
    - Any inbound mechanism once I-025 is wired up

    decision: "approve" or "reject" (case-insensitive)
    Returns: {"order_id": ..., "decision": ..., "status": ...}
    Raises AgentError if order not found, decision invalid, or order not awaiting approval.
    """
    decision = decision.lower().strip()
    if decision not in ("approve", "reject"):
        raise AgentError(
            f"process_approval_reply: invalid decision '{decision}' — must be 'approve' or 'reject'"
        )

    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"process_approval_reply: order {order_id} not found")

    current_status = db_row.get("status")
    if current_status != STATUS_AWAITING:
        raise AgentError(
            f"process_approval_reply: order {order_id} is not awaiting approval (status={current_status})"
        )

    new_status = STATUS_APPROVED if decision == "approve" else STATUS_REJECTED

    save_order_state(order_id, status=new_status)

    log_decision(
        agent_name=AGENT_NAME,
        decision=new_status,
        order_id=order_id,
        reason=f"human reviewer decision: {decision}",
        input_summary=f"service={db_row.get('service_type')} county={db_row.get('property_county')}",
        output_summary=f"status updated to {new_status}",
        model_used=HUMAN_GATE_MODEL,
    )

    log.info("approval processed order=%s decision=%s status=%s", order_id, decision, new_status)

    return {"order_id": order_id, "decision": decision, "status": new_status}


def _send_escalation_alert(order_id: str, db_row: dict, timeout_hours: int) -> None:
    """Send an escalation Teams alert for an overdue approval (Graph API)."""
    link = f"{FTF_ORDER_URL}/{order_id}"
    html = (
        f"<h3>&#9888; ESCALATION — Approval Overdue ({timeout_hours}h+)</h3>"
        f"<p><b>@Robert @Ryan</b> — order <a href='{link}'>{order_id}</a> "
        f"has been awaiting approval for more than {timeout_hours} hours.</p>"
        f"<ul>"
        f"<li><b>Service:</b> {db_row.get('service_type') or 'Unknown'}</li>"
        f"<li><b>County:</b> {db_row.get('property_county') or 'MISSING'}</li>"
        f"<li><b>Flag Reason:</b> {db_row.get('flag_reason') or 'see order'}</li>"
        f"<li><b>Flagged At:</b> {db_row.get('flagged_at') or 'Unknown'}</li>"
        f"</ul>"
        f"<p>Reply: <code>APPROVE {order_id}</code> or <code>REJECT {order_id} reason</code></p>"
    )

    send_channel_message(html, subject=f"ESCALATION — Order {order_id} overdue {timeout_hours}h+")

    log_decision(
        agent_name=AGENT_NAME,
        decision="escalated",
        order_id=order_id,
        reason=f"awaiting_approval >{timeout_hours}h",
        input_summary=f"service={db_row.get('service_type')}",
        output_summary="escalation alert sent via Graph API",
        model_used=HUMAN_GATE_MODEL,
    )


def run_escalation_check(timeout_hours: int = APPROVAL_TIMEOUT_HOURS) -> list[str]:
    """Find orders stuck in awaiting_approval longer than timeout_hours and escalate.

    Returns list of escalated order_ids.
    """
    overdue   = get_overdue_approvals(timeout_hours)
    escalated: list[str] = []

    for order_rec in overdue:
        order_id = order_rec["order_id"]
        _send_escalation_alert(order_id, order_rec, timeout_hours)
        escalated.append(order_id)
        log.warning("escalation sent order=%s awaiting>%sh", order_id, timeout_hours)

    log.info("escalation check complete escalated=%s", len(escalated))
    return escalated


def send_batch_approval_digest() -> dict:
    """Send one hourly Teams digest with ALL flagged + awaiting orders via Graph API.

    I-064: Ryan (2026-05-26) — "Bobby should get that spreadsheet every hour —
    job link, job size, brief description, estimate total, Approve/Deny column."

    Returns summary dict with counts.
    """
    flagged    = get_all_flagged_orders()
    awaiting   = get_all_awaiting_orders()
    all_orders = flagged + awaiting

    if not all_orders:
        log.info("batch digest: no orders to review")
        return {"flagged": 0, "awaiting": 0, "sent": False}

    html  = build_digest_html(all_orders, FTF_ORDER_URL)
    count = len(all_orders)
    send_channel_message(
        html,
        subject=f"FTF Estimates Pending Review — {count} order{'s' if count != 1 else ''}",
    )

    # Advance all newly-flagged orders to awaiting_approval
    for rec in flagged:
        save_order_state(
            rec["order_id"],
            status=STATUS_AWAITING,
            flagged_at=datetime.now(timezone.utc).isoformat(),
        )
        log_decision(
            agent_name=AGENT_NAME,
            decision="batch_notified",
            order_id=rec["order_id"],
            reason=rec.get("flag_reason"),
            input_summary=f"service={rec.get('service_type')}",
            output_summary="included in hourly batch digest (Graph API)",
            model_used=HUMAN_GATE_MODEL,
        )

    log.info(
        "batch digest sent via Graph API: %d flagged + %d awaiting = %d total",
        len(flagged), len(awaiting), count,
    )
    return {"flagged": len(flagged), "awaiting": len(awaiting), "sent": True}


def run() -> dict | None:
    """Send the hourly batch approval digest to Robert.

    I-064: Replaced per-order ping with hourly batch list — all flagged +
    awaiting_approval orders in one Teams message with Approve/Deny column.
    Returns None if no orders are waiting.
    """
    result = send_batch_approval_digest()
    return result if result.get("sent") else None


def main(argv=None) -> None:
    """CLI entrypoint for manual operations.

    Usage:
      python -m agents.agent_04_human_gate --run
      python -m agents.agent_04_human_gate --approve ORD-001
      python -m agents.agent_04_human_gate --reject  ORD-001
      python -m agents.agent_04_human_gate --check-escalations
    """
    import argparse

    parser = argparse.ArgumentParser(description="FTF Human Gate — Agent 4")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", action="store_true", help="Process next flagged order")
    group.add_argument("--approve", metavar="ORDER_ID", help="Mark order as approved")
    group.add_argument("--reject", metavar="ORDER_ID", help="Mark order as rejected")
    group.add_argument(
        "--check-escalations",
        action="store_true",
        help="Send escalation alerts for overdue approvals",
    )
    args = parser.parse_args(argv)

    if args.run:
        result = run()
        print(f"digest sent: flagged={result['flagged']} awaiting={result['awaiting']}" if result else "no flagged orders")
    elif args.approve:
        result = process_approval_reply(args.approve, "approve")
        print(f"approved={result['order_id']}")
    elif args.reject:
        result = process_approval_reply(args.reject, "reject")
        print(f"rejected={result['order_id']}")
    elif args.check_escalations:
        escalated = run_escalation_check()
        print(f"escalated={len(escalated)}")


if __name__ == "__main__":
    main()
