import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone

import httpx

from config.models import HUMAN_GATE_MODEL
from config.settings import (
    APPROVAL_TIMEOUT_HOURS,
    FTF_ORDER_URL,
    TEAMS_APPROVAL_WEBHOOK_URL,
    TEAMS_WEBHOOK_URL,
)
from core.db import (
    get_all_awaiting_orders, get_all_flagged_orders, get_flagged_order,
    get_order_by_id, get_overdue_approvals, log_decision, save_order_state,
)
from core.exceptions import AgentError
from core.logger import get_logger

AGENT_NAME = "agent_04_human_gate"
log = get_logger(AGENT_NAME)

# Status constants for the human review lifecycle
STATUS_AWAITING = "awaiting_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


def _build_teams_payload(order_id: str, db_row: dict) -> dict:
    """Build a legacy MessageCard payload for MS Teams."""
    amount = db_row.get("estimate_amount")
    amount_str = f"${amount:,.2f}" if amount is not None else "TBD"
    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": f"FTF Order {order_id} Requires Human Review",
        "themeColor": "FF0000",
        "title": "FTF Estimate — Human Review Required",
        "sections": [
            {
                "facts": [
                    {"name": "Order ID", "value": order_id},
                    {"name": "Service", "value": db_row.get("service_type") or "Unknown"},
                    {"name": "County", "value": db_row.get("property_county") or "MISSING"},
                    {"name": "State", "value": db_row.get("property_state") or "Unknown"},
                    {"name": "Flag Reason", "value": db_row.get("flag_reason") or "See order"},
                    {"name": "Estimate Amount", "value": amount_str},
                    {"name": "Flagged At", "value": str(db_row.get("flagged_at") or "Unknown")},
                ]
            }
        ],
        "potentialAction": [],  # Approval buttons added in I-025 resolution (Sprint N)
    }


def notify_human(order_id: str) -> dict:
    """POST a Teams alert for a flagged order and advance its status to awaiting_approval.

    Returns: dict with keys "order_id", "notified", "status".
    Raises AgentError if Teams webhook is not configured or the POST fails.
    """
    if not TEAMS_WEBHOOK_URL:
        raise AgentError("TEAMS_WEBHOOK_URL not configured — cannot notify human reviewer")

    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"notify_human: order {order_id} not found in processed_orders")

    payload = _build_teams_payload(order_id, db_row)

    try:
        r = httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=15.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(f"Teams webhook POST failed: HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise AgentError(f"Teams webhook POST failed: {exc}") from exc

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
        output_summary=f"Teams alert sent; status={STATUS_AWAITING}",
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
    """POST an escalation Teams alert for an overdue approval."""
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": f"ESCALATION: FTF Order {order_id} awaiting approval >{timeout_hours}h",
        "themeColor": "FF6600",
        "title": f"FTF Estimate — ESCALATION: Approval Overdue ({timeout_hours}h+)",
        "sections": [
            {
                "facts": [
                    {"name": "Order ID", "value": order_id},
                    {"name": "Service", "value": db_row.get("service_type") or "Unknown"},
                    {"name": "County", "value": db_row.get("property_county") or "MISSING"},
                    {"name": "Flag Reason", "value": db_row.get("flag_reason") or "See order"},
                    {"name": "Flagged At", "value": str(db_row.get("flagged_at") or "Unknown")},
                    {
                        "name": "Action Required",
                        "value": f"Awaiting approval for >{timeout_hours}h — please approve or reject",
                    },
                ]
            }
        ],
        "potentialAction": [],
    }

    try:
        r = httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=15.0)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"Teams escalation POST failed: HTTP {exc.response.status_code}"
        ) from exc
    except Exception as exc:
        raise AgentError(f"Teams escalation POST failed: {exc}") from exc

    log_decision(
        agent_name=AGENT_NAME,
        decision="escalated",
        order_id=order_id,
        reason=f"awaiting_approval >{timeout_hours}h",
        input_summary=f"service={db_row.get('service_type')}",
        output_summary="escalation alert sent to Teams",
        model_used=HUMAN_GATE_MODEL,
    )


def run_escalation_check(timeout_hours: int = APPROVAL_TIMEOUT_HOURS) -> list[str]:
    """Find orders stuck in awaiting_approval longer than timeout_hours and send escalation alerts.

    Returns list of escalated order_ids.
    Raises AgentError if TEAMS_WEBHOOK_URL is not configured.
    """
    if not TEAMS_WEBHOOK_URL:
        raise AgentError("TEAMS_WEBHOOK_URL not configured — cannot send escalation alerts")

    overdue = get_overdue_approvals(timeout_hours)
    escalated: list[str] = []

    for order_rec in overdue:
        order_id = order_rec["order_id"]
        _send_escalation_alert(order_id, order_rec, timeout_hours)
        escalated.append(order_id)
        log.warning("escalation sent order=%s awaiting>%sh", order_id, timeout_hours)

    log.info("escalation check complete escalated=%s", len(escalated))
    return escalated


def send_batch_approval_digest() -> dict:
    """Send one hourly Teams digest with ALL flagged + awaiting orders.

    I-064: Ryan (2026-05-26) — "Bobby should get that spreadsheet every hour —
    job link, job size, brief description, estimate total, Approve/Deny column."
    Robert bulk-approves or picks specific ones to deny and handle manually.

    Returns summary dict with counts.
    """
    flagged = get_all_flagged_orders()
    awaiting = get_all_awaiting_orders()
    all_orders = flagged + awaiting

    if not all_orders:
        log.info("batch digest: no orders to review")
        return {"flagged": 0, "awaiting": 0, "sent": False}

    # Use dedicated approval channel if configured; fall back to general webhook
    _approval_url = TEAMS_APPROVAL_WEBHOOK_URL or TEAMS_WEBHOOK_URL
    if not _approval_url:
        raise AgentError("TEAMS_APPROVAL_WEBHOOK_URL not configured — cannot send batch digest")

    rows = []
    now = datetime.now(timezone.utc)
    for rec in all_orders:
        order_id = rec["order_id"]
        amount = rec.get("estimate_amount")
        amount_str = f"${float(amount):,.2f}" if amount else "TBD"
        age_h = ""
        if rec.get("flagged_at"):
            try:
                from datetime import datetime as _dt
                flagged_at = _dt.fromisoformat(str(rec["flagged_at"]))
                if flagged_at.tzinfo is None:
                    import pytz; flagged_at = pytz.utc.localize(flagged_at)
                age_h = f"{int((now - flagged_at).total_seconds() / 3600)}h ago"
            except Exception:
                pass
        link = f"{FTF_ORDER_URL}/{order_id}"
        row = (
            f"**[{order_id}]({link})** | "
            f"{rec.get('service_type') or 'Unknown'} | "
            f"{amount_str} | "
            f"{rec.get('flag_reason') or 'see order'[:60]} | "
            f"{rec.get('status', '')} | {age_h}"
        )
        rows.append(row)

    table_text = "\n".join(rows)
    order_count = len(all_orders)
    title = f"FTF Estimates Pending Review — {order_count} order{'s' if order_count != 1 else ''}"
    body = (
        f"**@Robert @Ryan — please review and approve/deny the following estimates:**\n\n"
        f"| Order | Service | Amount | Flag Reason | Status | Age |\n"
        f"|---|---|---|---|---|---|\n"
        f"{chr(10).join('| ' + r.replace(' | ', ' | ') for r in rows)}\n\n"
        f"---\n"
        f"**Reply directly in this channel (Outgoing Webhook listens):**\n"
        f"- `APPROVE <order_id>` — approve one estimate for sending\n"
        f"- `APPROVE ALL` — approve everything in this list\n"
        f"- `REJECT <order_id> [reason]` — reject and hold\n\n"
        f"*Example:* `APPROVE 1000276115`"
    )

    payload = {
        "@type":      "MessageCard",
        "@context":   "http://schema.org/extensions",
        "themeColor": "0078D7",
        "summary":    title,
        "title":      title,
        "text":       body,
    }

    try:
        r = httpx.post(_approval_url, json=payload, timeout=15.0)
        r.raise_for_status()
    except Exception as exc:
        raise AgentError(f"batch digest Teams POST failed: {exc}") from exc

    # Advance all flagged orders to awaiting_approval
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
            output_summary="included in hourly batch digest",
            model_used=HUMAN_GATE_MODEL,
        )

    log.info("batch digest sent: %d flagged + %d awaiting = %d total", len(flagged), len(awaiting), order_count)
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
        print(f"notified={result['order_id']}" if result else "no flagged orders")
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
