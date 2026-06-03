"""Morning check-in — posts a status summary to the Teams group chat.

Runs at 10 AM IST (4:30 AM UTC) to confirm the bot ran overnight
even while Prateek's local machine was powered off.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.teams_graph_client import post_chat_message
from core.excel_db import get_orders_by_status
from dotenv import load_dotenv

load_dotenv()


def run() -> None:
    # Count orders in each key status
    approved  = get_orders_by_status("invoice_approved")
    finalized = get_orders_by_status("invoice_finalized")
    sent      = get_orders_by_status("invoice_sent")
    pending   = get_orders_by_status("invoice_draft_posted")
    pricing   = get_orders_by_status("pricing_needed")

    msg = (
        f"🌅 <strong>Good morning, Prateek!</strong><br>"
        f"<br>"
        f"I kept running overnight — your system being off made no difference. "
        f"Here's where things stand right now:<br>"
        f"<br>"
        f"&nbsp;&nbsp;✅ Invoices sent (done): <strong>{len(sent)}</strong><br>"
        f"&nbsp;&nbsp;🔄 Approved, creating invoice: <strong>{len(approved) + len(finalized)}</strong><br>"
        f"&nbsp;&nbsp;⏳ Waiting for your approval: <strong>{len(pending)}</strong><br>"
        f"&nbsp;&nbsp;❓ Need pricing input from you: <strong>{len(pricing)}</strong><br>"
        f"<br>"
        f"I'm checking Teams every 2 minutes, 24/7. "
        f"{'Reply <code>Hey @Nesa approve [order_id]</code> for any of the ' + str(len(pending)) + ' pending orders whenever you are ready.' if pending else 'No orders are waiting — all caught up!'}<br>"
        f"{'<br>⚠️ <strong>' + str(len(pricing)) + ' order(s) need your pricing input.</strong> Reply <code>Hey @Nesa price [order_id] $[amount]</code> for each.' if pricing else ''}"
    )

    post_chat_message(msg, subject="Morning status — Nesa is running")
    print("Morning check-in posted to Teams.")


if __name__ == "__main__":
    run()
