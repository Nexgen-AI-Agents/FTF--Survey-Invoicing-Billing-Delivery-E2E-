"""Agent 10 — AR Scanner

Downloads unpaid invoices from FTF Books, identifies overdue accounts
(>= 60 days), and upserts them into ar_reminders for escalation processing.
"""

from core.db import upsert_ar_reminder
from core.ftf_books_client import get_unpaid_invoices
from core.logger import get_logger

logger = get_logger(__name__)

MIN_DAYS_OVERDUE = 60


def run() -> dict:
    invoices = get_unpaid_invoices()

    tracked = 0
    for inv in invoices:
        if inv["days_overdue"] >= MIN_DAYS_OVERDUE:
            upsert_ar_reminder(
                order_id=inv["order_id"],
                customer_email=inv["customer_email"],
                invoice_amount=inv["invoice_amount"],
                invoice_date=inv["invoice_date"],
                days_overdue=inv["days_overdue"],
            )
            tracked += 1

    logger.info("agent_10_ar_scanner: %d/%d invoices >=60d upserted", tracked, len(invoices))
    return {"scanned": len(invoices), "tracked": tracked}


if __name__ == "__main__":
    result = run()
    print(result)
