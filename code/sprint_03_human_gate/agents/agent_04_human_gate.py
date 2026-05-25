import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone

import httpx

from config.models import HUMAN_GATE_MODEL
from config.settings import APPROVAL_TIMEOUT_HOURS, TEAMS_WEBHOOK_URL
from core.db import get_flagged_order, get_order_by_id, get_overdue_approvals, log_decision, save_order_state
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


def run() -> dict | None:
    """Pick up the oldest flagged order, notify the human reviewer, return result.

    Returns None if no flagged orders are waiting.
    """
    order_rec = get_flagged_order()
    if not order_rec:
        log.info("no flagged orders waiting for human review")
        return None

    order_id = order_rec["order_id"]
    return notify_human(order_id)


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
