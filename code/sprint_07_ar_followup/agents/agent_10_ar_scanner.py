"""Agent 10 — AR Scanner

Downloads unpaid invoices from FTF Books, identifies overdue accounts
(>= 60 days), and upserts them into ar_reminders for escalation processing.

I-063 hard rule: if any invoice notes contain refund intent, alert Jessica
immediately and skip the AR reminder flow for that order.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import AR_EXCLUSION_LIST
from core.db import get_order_by_id, upsert_ar_reminder
from core.ftf_books_client import get_unpaid_invoices
from core.logger import get_logger
from core.refund_guard import alert_jessica_refund, detect_refund_intent

logger = get_logger(__name__)

MIN_DAYS_OVERDUE = 60


def _check_refund(inv: dict) -> bool:
    """Return True if this invoice/order contains any refund-related text."""
    order_rec = get_order_by_id(inv["order_id"])
    if not order_rec:
        return False
    suspect_fields = [
        order_rec.get("flag_reason") or "",
        order_rec.get("draft_estimate") or "",
    ]
    for field_text in suspect_fields:
        if detect_refund_intent(field_text):
            alert_jessica_refund(inv["order_id"], field_text)
            return True
    return False


def run() -> dict:
    invoices = get_unpaid_invoices()

    tracked = 0
    refund_stopped = 0
    excluded = 0
    for inv in invoices:
        if inv["days_overdue"] >= MIN_DAYS_OVERDUE:
            # AR exclusion list — Jessica manages via AR_EXCLUSION_LIST env var
            email = (inv.get("customer_email") or "").strip().lower()
            if AR_EXCLUSION_LIST and email in AR_EXCLUSION_LIST:
                logger.info("ar_scanner: skipping excluded customer email=%s order=%s",
                            email, inv["order_id"])
                excluded += 1
                continue
            if _check_refund(inv):
                refund_stopped += 1
                continue
            upsert_ar_reminder(
                order_id=inv["order_id"],
                customer_email=inv["customer_email"],
                invoice_amount=inv["invoice_amount"],
                invoice_date=inv["invoice_date"],
                days_overdue=inv["days_overdue"],
            )
            tracked += 1

    logger.info(
        "agent_10_ar_scanner: %d/%d invoices >=60d upserted, %d refund-stopped, %d excluded",
        tracked, len(invoices), refund_stopped, excluded,
    )
    return {
        "scanned":       len(invoices),
        "tracked":       tracked,
        "refund_stopped": refund_stopped,
        "excluded":      excluded,
    }


if __name__ == "__main__":
    result = run()
    print(result)
