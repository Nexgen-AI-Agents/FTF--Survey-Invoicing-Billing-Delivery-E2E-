"""Agent 11 — AR Escalation

Queries ar_reminders for invoices that have crossed Day 60 or Day 90
thresholds and sends internal Teams alerts per the escalation policy:
  Day 60 → alert Jessica only   (reminder_level 1 → 2)
  Day 90 → alert all stakeholders (reminder_level < 3 → 3)

90-day escalations are processed first so no invoice can be double-counted.
"""

import httpx

from config.settings import AR_ALERT_DAYS_60, AR_ESCALATION_DAYS, TEAMS_WEBHOOK_URL
from core.db import get_invoices_due_for_escalation, log_decision, update_ar_escalation_level
from core.logger import get_logger

logger = get_logger(__name__)

_JESSICA_MENTION = "Jessica"
_STAKEHOLDERS    = "Jessica, Ryan, Mark, Robert, Wyatt"


def _send_teams_alert(order_id: str, customer_email: str, days_overdue: int,
                      invoice_amount: float, tier: int) -> None:
    if not TEAMS_WEBHOOK_URL:
        logger.warning("TEAMS_WEBHOOK_URL not set — skipping Teams alert order=%s", order_id)
        return

    if tier == 2:
        color   = "FF8C00"
        title   = f"AR Alert — Day 60 Overdue: Order {order_id}"
        mention = _JESSICA_MENTION
    else:
        color   = "FF0000"
        title   = f"AR Alert — Day 90 Overdue: Order {order_id}"
        mention = _STAKEHOLDERS

    body = (
        f"**Order:** {order_id}  \n"
        f"**Days Overdue:** {days_overdue}  \n"
        f"**Invoice Amount:** ${invoice_amount:,.2f}  \n"
        f"**Action Required:** {mention} — please review and follow up."
    )

    payload = {
        "@type":       "MessageCard",
        "@context":    "https://schema.org/extensions",
        "themeColor":  color,
        "summary":     title,
        "title":       title,
        "text":        body,
    }

    try:
        resp = httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=15)
        resp.raise_for_status()
        logger.info("teams_alert sent tier=%d order=%s days=%d", tier, order_id, days_overdue)
    except Exception as exc:
        logger.error("teams_alert failed order=%s: %s", order_id, exc)


def run() -> dict:
    alerts_90 = 0
    alerts_60 = 0

    # 90-day first — prevents a 90d invoice from also being counted at 60d
    invoices_90 = get_invoices_due_for_escalation(min_days=AR_ESCALATION_DAYS, max_level=3)
    for inv in invoices_90:
        _send_teams_alert(
            order_id=inv["order_id"],
            customer_email=inv["customer_email"],
            days_overdue=inv["days_overdue"],
            invoice_amount=float(inv["invoice_amount"]),
            tier=3,
        )
        update_ar_escalation_level(inv["order_id"], new_level=3)
        log_decision(
            agent_name="agent_11_ar_escalation",
            decision="day90_alert_sent",
            order_id=inv["order_id"],
            reason=f"{inv['days_overdue']} days overdue — all stakeholders alerted",
        )
        alerts_90 += 1

    # 60-day — only those not yet advanced to level 2+
    invoices_60 = get_invoices_due_for_escalation(min_days=AR_ALERT_DAYS_60, max_level=2)
    for inv in invoices_60:
        _send_teams_alert(
            order_id=inv["order_id"],
            customer_email=inv["customer_email"],
            days_overdue=inv["days_overdue"],
            invoice_amount=float(inv["invoice_amount"]),
            tier=2,
        )
        update_ar_escalation_level(inv["order_id"], new_level=2)
        log_decision(
            agent_name="agent_11_ar_escalation",
            decision="day60_alert_sent",
            order_id=inv["order_id"],
            reason=f"{inv['days_overdue']} days overdue — Jessica alerted",
        )
        alerts_60 += 1

    logger.info("agent_11_ar_escalation: 90d=%d alerts, 60d=%d alerts", alerts_90, alerts_60)
    return {"alerts_90": alerts_90, "alerts_60": alerts_60}


if __name__ == "__main__":
    result = run()
    print(result)
