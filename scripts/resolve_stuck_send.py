"""resolve_stuck_send.py — clear an invoice 'sending' tombstone after a human check.

When A6 attempts to deliver an invoice but the outcome is unknown (lost ack, timeout,
or a crash right after the send), it parks the order at status=invoice_sending and
NEVER auto-resends it — to guarantee a customer is never emailed the same invoice twice.

IMPORTANT — how to verify before deciding:
  An order parked at invoice_sending is ambiguous on purpose. Two situations look
  identical here (same status, same send_attempted_at):
    (a) the process died BEFORE the email went out  -> safe to re-send, OR
    (b) the email WAS sent but the acknowledgement was lost -> re-sending = DUPLICATE.
  FTF exposes NO "email already sent" flag, so you must check the AUTHORITATIVE source:
  the SendGrid Activity feed (https://app.sendgrid.com/email_activity) for the client's
  email around `send_attempted_at`. If SendGrid shows a delivered/processed event for
  that invoice -> use --confirm-sent. Only if you are CERTAIN nothing was delivered
  -> use --retry (which requires the explicit --i-verified-not-delivered acknowledgement).

  Already delivered (do NOT resend):   python scripts/resolve_stuck_send.py --order-id 1234567 --confirm-sent
  NOT delivered (let A6 re-send it):   python scripts/resolve_stuck_send.py --order-id 1234567 --retry --i-verified-not-delivered
  List everything currently parked:    python scripts/resolve_stuck_send.py --list
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.excel_db import get_order_by_id, get_orders_by_status, save_order_state  # noqa: E402


def _list() -> None:
    rows = get_orders_by_status("invoice_sending")
    if not rows:
        print("No orders are parked at invoice_sending.")
        return
    print(f"{len(rows)} order(s) awaiting send confirmation:")
    for r in rows:
        print(f"  order={r.get('order_id')}  invoice_id={r.get('invoice_id')}  "
              f"attempted_at={r.get('send_attempted_at')}  client={r.get('client_name')}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Resolve an invoice_sending tombstone after a human check.")
    p.add_argument("--order-id")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--confirm-sent", action="store_true",
                   help="The email DID go out (verified in SendGrid) — mark invoice_sent (no resend).")
    g.add_argument("--retry", action="store_true",
                   help="The email did NOT go out — revert to invoice_finalized so A6 re-sends it. "
                        "Requires --i-verified-not-delivered.")
    p.add_argument("--i-verified-not-delivered", action="store_true",
                   help="Acknowledge you checked SendGrid and the invoice was NOT delivered. "
                        "Required guard for --retry to prevent a duplicate email.")
    p.add_argument("--list", action="store_true", help="List all orders parked at invoice_sending.")
    args = p.parse_args(argv)

    if args.list or not args.order_id:
        _list()

    # An action flag without --order-id is a no-op that could mislead an operator under
    # pressure — fail loudly instead of silently returning.
    if not args.order_id:
        if args.confirm_sent or args.retry:
            print("ERROR: --confirm-sent/--retry require --order-id. Nothing changed.")
            sys.exit(1)
        return

    row = get_order_by_id(args.order_id)
    if not row:
        print(f"ERROR: order {args.order_id} not found in state store.")
        sys.exit(1)
    status = str(row.get("status") or "")
    if status != "invoice_sending":
        print(f"WARNING: order {args.order_id} is status={status!r}, not 'invoice_sending'. "
              "Nothing to resolve — aborting to be safe.")
        sys.exit(1)

    if args.confirm_sent:
        save_order_state(args.order_id, status="invoice_sent",
                         sent_at=datetime.now(timezone.utc).isoformat())
        print(f"OK: order {args.order_id} marked invoice_sent (confirmed delivered — will not resend).")
    elif args.retry:
        if not args.i_verified_not_delivered:
            print(
                f"REFUSED: --retry will RE-SEND the invoice email for order {args.order_id} "
                f"(attempted_at={row.get('send_attempted_at')}).\n"
                "  This order is ambiguous: the email may ALREADY have gone out (lost ack), in which\n"
                "  case re-sending DOUBLE-EMAILS the customer. FTF has no 'sent' flag — verify in the\n"
                "  SendGrid Activity feed (https://app.sendgrid.com/email_activity) for the client's\n"
                "  email near that timestamp.\n"
                "  If SendGrid shows it WAS delivered, use --confirm-sent instead.\n"
                "  Only if you are CERTAIN it was NOT delivered, re-run with --i-verified-not-delivered."
            )
            sys.exit(1)
        save_order_state(args.order_id, status="invoice_finalized")
        print(f"OK: order {args.order_id} reverted to invoice_finalized — A6 will re-send it next run.")
    else:
        print(f"order {args.order_id} is parked at invoice_sending "
              f"(attempted_at={row.get('send_attempted_at')}). "
              "Verify in SendGrid, then re-run with --confirm-sent or "
              "--retry --i-verified-not-delivered.")


if __name__ == "__main__":
    main()
