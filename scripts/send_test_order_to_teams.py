"""
send_test_order_to_teams.py — Create a test order in the DB and post it to
FTF-Approvals so you can manually type APPROVE/REJECT and verify the bot flow.

Usage:
    python scripts/send_test_order_to_teams.py
    python scripts/send_test_order_to_teams.py --order-id MY-TEST-001
    python scripts/send_test_order_to_teams.py --multi    # send two orders (tests multi-approve)
    python scripts/send_test_order_to_teams.py --cleanup  # delete all QA-LIVE-TEST-* from DB
"""

import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from config.settings import FTF_ORDER_URL
from core.db import _get_cursor, get_order_by_id, save_order_state
from core.teams_graph_client import send_channel_message

TEST_PREFIX = "QA-LIVE-TEST-"


def _create_order(order_id: str, amount: float, service: str, flag_reason: str) -> None:
    save_order_state(
        order_id=order_id,
        status="awaiting_approval",
        service_type=service,
        customer_email="qa-manual@ftf-test.internal",
        estimate_amount=amount,
        flag_reason=flag_reason,
    )
    print(f"  [OK] Order {order_id} created (status=awaiting_approval, amount=${amount:,.2f})")


def _cleanup() -> None:
    with _get_cursor() as cur:
        cur.execute("DELETE FROM processed_orders WHERE order_id LIKE %s", (f"{TEST_PREFIX}%",))
        n = cur.rowcount
    print(f"[OK] Removed {n} {TEST_PREFIX}* order(s) from DB")


def send_single(order_id: str) -> None:
    existing = get_order_by_id(order_id)
    if existing:
        print(f"[INFO] {order_id} already exists (status={existing['status']}) -- updating to awaiting_approval")
    _create_order(order_id, 475.00, "Boundary Survey", "QA live test -- approve to verify bot flow")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    link    = f"{FTF_ORDER_URL}/{order_id}"
    msg = (
        f"[MANUAL QA TEST]  {now_str}\n"
        f"\n"
        f"Test order pending your approval:\n"
        f"  Order:     {order_id}\n"
        f"  Service:   Boundary Survey\n"
        f"  Estimate:  $475.00\n"
        f"  Property:  1234 Test Lane, Orlando FL 32801\n"
        f"  FTF link:  {link}\n"
        f"  Note:      QA test order -- safe to approve or reject\n"
        f"\n"
        f"To APPROVE:  APPROVE {order_id}\n"
        f"To REJECT:   REJECT {order_id} test rejection reason\n"
        f"\n"
        f"(Only Robert, Ryan, or Prateek -- bot will warn if anyone else tries)"
    )
    send_channel_message(msg, subject="FTF QA Test -- Action Required")
    print(f"  [OK] Notification posted to FTF-Approvals channel")
    _print_next_steps([order_id])


def send_multi(ids: list[str]) -> None:
    for i, oid in enumerate(ids):
        _create_order(oid, 350.00 + i * 125, "Boundary Survey", f"QA multi-approve test #{i+1}")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    id_list = "  ".join(ids)
    approve_cmd = "APPROVE " + " ".join(ids)
    msg = (
        f"[MANUAL QA TEST -- MULTI-APPROVE]  {now_str}\n"
        f"\n"
        f"Two test orders pending approval (tests multi-ID approval + double confirmation):\n"
        f"\n"
    )
    for i, oid in enumerate(ids):
        link = f"{FTF_ORDER_URL}/{oid}"
        msg += f"  {oid} | Boundary Survey | ${350.00 + i*125:,.2f} | {link}\n"
    msg += (
        f"\n"
        f"To approve BOTH at once:  {approve_cmd}\n"
        f"To approve one:  APPROVE {ids[0]}\n"
        f"To reject one:   REJECT {ids[0]} test reason\n"
        f"\n"
        f"(Bot will confirm before + after processing multiple IDs)"
    )
    send_channel_message(msg, subject="FTF QA Test Multi-Approve -- Action Required")
    print(f"  [OK] Multi-order notification posted to FTF-Approvals channel")
    _print_next_steps(ids)


def _print_next_steps(ids: list[str]) -> None:
    approve_cmd = "APPROVE " + " ".join(ids)
    print()
    print("Next steps:")
    print("  1. Open FTF-Approvals channel in Teams")
    print(f"  2. Type:  {approve_cmd}")
    print(f"     or:    REJECT {ids[0]} your reason here")
    print(f"  3. Run:   python scripts/poll_teams_approvals.py --since-hours 1")
    print(f"     (bot processes the command and posts confirmation back)")
    print(f"  4. Cleanup: python scripts/send_test_order_to_teams.py --cleanup")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Create test order(s) and notify Teams")
    parser.add_argument("--order-id", default=f"{TEST_PREFIX}001",
                        help=f"Single order ID to create (default: {TEST_PREFIX}001)")
    parser.add_argument("--multi", action="store_true",
                        help="Create two orders to test multi-ID approve flow")
    parser.add_argument("--cleanup", action="store_true",
                        help=f"Delete all {TEST_PREFIX}* orders from DB")
    args = parser.parse_args(argv)

    if args.cleanup:
        _cleanup()
        return

    print(f"\nCreating test order(s) in DB and posting to FTF-Approvals...\n")
    if args.multi:
        send_multi([f"{TEST_PREFIX}001", f"{TEST_PREFIX}002"])
    else:
        send_single(args.order_id)


if __name__ == "__main__":
    main()
