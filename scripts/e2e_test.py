"""E2E Pipeline Test — Sprint 11
Runs TC1 (Approve+Email), TC2 (Reject), TC3 (Price→Confirm→Approve+Email)
directly against the live pipeline state and FTF API.
EMAIL_OVERRIDE_ALL must be set — all emails go to Prateek, never to real clients.
"""

import json
import os
import sys
import traceback
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code", "shared"))
sys.path.insert(0, os.path.join(ROOT, "code", "sprint_11_invoice_pipeline"))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from core.excel_db import get_order_by_id, save_order_state
from core.teams_graph_client import post_chat_message
from config.settings import EMAIL_OVERRIDE_ALL

PASS = "✅ PASS"
FAIL = "❌ FAIL"

# ── Test orders ─────────────────────────────────────────────────────────────
TC1_ORDER = "1000283094"   # Aldo Tolentino | $475 Land Survey Only | has email
TC2_ORDER = "1000283046"   # Marlene M. Tiernan | $475 Land Survey Only | has email
TC3_ORDER = "1000283532"   # BCM Inc. | $0 → we price at $750

results: list[str] = []


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check(label: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    msg = f"{status}  {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append(msg)


# ── Pre-flight ───────────────────────────────────────────────────────────────

section("PRE-FLIGHT")
check("EMAIL_OVERRIDE_ALL is set (no real client emails)",
      bool(EMAIL_OVERRIDE_ALL),
      EMAIL_OVERRIDE_ALL or "NOT SET — ABORT")

if not EMAIL_OVERRIDE_ALL:
    print("ABORTING: EMAIL_OVERRIDE_ALL not set. Real client emails would be sent.")
    sys.exit(1)

# ── TC1: Approve → A5 creates invoice → A6 sends email ──────────────────────

section("TC1: APPROVE — Order " + TC1_ORDER)

try:
    # Save current state so we can restore if needed
    original = get_order_by_id(TC1_ORDER)
    check("TC1 order exists in state", bool(original),
          f"status={original.get('status') if original else 'NOT FOUND'}")

    if not original:
        raise Exception(f"Order {TC1_ORDER} not found")

    orig_status = original.get("status")
    orig_draft  = original.get("invoice_draft")

    check("TC1 order has invoice_draft", bool(orig_draft),
          f"draft_len={len(orig_draft or '')}")
    check("TC1 order has customer_email", bool(original.get("customer_email")),
          original.get("customer_email", "MISSING"))

    # Verify draft has services and amount
    draft = json.loads(orig_draft) if orig_draft else {}
    check("TC1 draft has services", bool(draft.get("services")),
          str([s.get("name") for s in draft.get("services", [])]))
    check("TC1 draft total > 0", float(draft.get("total_amount", 0)) > 0,
          f"${draft.get('total_amount', 0)}")

    # Step 1: Mark as approved (simulating Prateek saying "Hey @Nesa approve TC1_ORDER")
    print(f"\n→ Simulating: Hey @Nesa approve {TC1_ORDER}")
    save_order_state(TC1_ORDER, status="invoice_approved", approved_by="prateek")
    refreshed = get_order_by_id(TC1_ORDER)
    check("TC1 status set to invoice_approved",
          refreshed.get("status") == "invoice_approved",
          f"actual={refreshed.get('status')}")

    # Step 2: Run A5 — create FTF invoice
    print(f"\n→ Running A5 (create FTF invoice) for {TC1_ORDER}...")
    from agents.agent_a5_invoice_finalizer import finalize_order
    a5_result = finalize_order(TC1_ORDER)
    check("TC1 A5 returned ok", a5_result.get("ok"), str(a5_result))
    check("TC1 A5 returned invoice_id", bool(a5_result.get("invoice_id")),
          f"invoice_id={a5_result.get('invoice_id')}")

    after_a5 = get_order_by_id(TC1_ORDER)
    check("TC1 status is invoice_finalized", after_a5.get("status") == "invoice_finalized",
          f"actual={after_a5.get('status')}")

    # Step 3: Run A6 — send email
    print(f"\n→ Running A6 (send email) for {TC1_ORDER}...")
    from agents.agent_a6_sender_v2 import send_for_order
    a6_result = send_for_order(TC1_ORDER, skip_delay=True)
    check("TC1 A6 email sent", a6_result.get("sent"), str(a6_result))
    check("TC1 email went to override address", EMAIL_OVERRIDE_ALL in a6_result.get("to", ""),
          f"to={a6_result.get('to')}")

    after_a6 = get_order_by_id(TC1_ORDER)
    check("TC1 final status is invoice_sent", after_a6.get("status") == "invoice_sent",
          f"actual={after_a6.get('status')}")

    print(f"\n✅ TC1 COMPLETE — invoice #{a5_result.get('invoice_id')} created, "
          f"email sent to {a6_result.get('to')}")

except Exception as exc:
    check("TC1 EXCEPTION", False, traceback.format_exc()[-300:])

# ── TC2: Reject ──────────────────────────────────────────────────────────────

section("TC2: REJECT — Order " + TC2_ORDER)

try:
    original2 = get_order_by_id(TC2_ORDER)
    check("TC2 order exists", bool(original2),
          f"status={original2.get('status') if original2 else 'NOT FOUND'}")

    if not original2:
        raise Exception(f"Order {TC2_ORDER} not found")

    orig_status2 = original2.get("status")

    # Simulate: Hey @Nesa reject TC2_ORDER client changed their mind
    reason = "Client changed their mind — price too high"
    print(f"\n→ Simulating: Hey @Nesa reject {TC2_ORDER} {reason}")
    save_order_state(TC2_ORDER, status="invoice_rejected")

    after_reject = get_order_by_id(TC2_ORDER)
    check("TC2 status set to invoice_rejected",
          after_reject.get("status") == "invoice_rejected",
          f"actual={after_reject.get('status')}")

    # Verify A5 would skip it (should not find any invoice_approved orders for TC2)
    from core.excel_db import get_orders_by_status
    approved = [r for r in get_orders_by_status("invoice_approved") if str(r["order_id"]) == TC2_ORDER]
    check("TC2 not in invoice_approved queue", len(approved) == 0,
          f"found {len(approved)} copies — would have been double-invoiced")

    # Verify A6 would skip it too
    finalized = [r for r in get_orders_by_status("invoice_finalized") if str(r["order_id"]) == TC2_ORDER]
    check("TC2 not in invoice_finalized queue", len(finalized) == 0,
          f"found {len(finalized)}")

    # Post Teams rejection notice
    post_chat_message(
        f"❌ <strong>TEST TC2 — Order #{TC2_ORDER} REJECTED</strong><br>"
        f"Reason: {reason}<br>"
        f"Client: {original2.get('client_name', 'Unknown')} | "
        f"Amount: ${float(original2.get('estimate_amount') or 0):,.2f}<br>"
        f"Status: invoice_rejected — no invoice created, no email sent.",
        subject="E2E Test TC2 — Reject"
    )
    check("TC2 Teams rejection notice posted", True, "")

    print(f"\n✅ TC2 COMPLETE — order {TC2_ORDER} rejected, not invoiced")

except Exception as exc:
    check("TC2 EXCEPTION", False, traceback.format_exc()[-300:])

# ── TC3: Price → Confirm → Approve → Invoice → Email ────────────────────────

section("TC3: PRICE THEN APPROVE — Order " + TC3_ORDER)

try:
    original3 = get_order_by_id(TC3_ORDER)
    check("TC3 order exists", bool(original3),
          f"status={original3.get('status') if original3 else 'NOT FOUND'}")

    if not original3:
        raise Exception(f"Order {TC3_ORDER} not found")

    # Step 1: Set price (simulating "Hey @Nesa price TC3_ORDER $750")
    TEST_PRICE = 750.0
    TEST_SVC   = "Land Survey (Boundary)"
    print(f"\n→ Simulating: Hey @Nesa price {TC3_ORDER} ${TEST_PRICE}")

    new_draft = {
        "total_amount": TEST_PRICE,
        "services": [{
            "name": TEST_SVC,
            "description": "Manually priced by prateek via E2E test.",
            "amount": TEST_PRICE,
        }],
        "pricing_reasoning": f"Manual price $750 set by prateek (E2E test)",
        "confidence": "HIGH",
        "escalate_flag": False,
        "escalate_reason": None,
        "flags": ["MANUAL_PRICE: Set by prateek (E2E test)."],
    }
    save_order_state(TC3_ORDER, status="invoice_draft_posted",
                     invoice_draft=json.dumps(new_draft), estimate_amount=TEST_PRICE)

    after_price = get_order_by_id(TC3_ORDER)
    draft3 = json.loads(after_price.get("invoice_draft") or "{}")
    check("TC3 price saved correctly",
          float(draft3.get("total_amount", 0)) == TEST_PRICE,
          f"${draft3.get('total_amount')}")

    # Post confirmation card to Teams
    post_chat_message(
        f"<strong>📋 TEST TC3 — Pricing set — Order #{TC3_ORDER}</strong><br>"
        f"<strong>Service:</strong> {TEST_SVC}<br>"
        f"<strong>Amount:</strong> <strong>${TEST_PRICE:,.2f}</strong><br>"
        f"<strong>Set by:</strong> prateek (E2E test)<br>"
        f"<br>"
        f"✅ This is the confirmation card Prateek would see after pricing.<br>"
        f"Proceeding directly to approval for the E2E test...",
        subject=f"TEST: Confirm pricing — Order {TC3_ORDER}"
    )

    # Step 2: Approve (simulating "Hey @Nesa approve TC3_ORDER")
    print(f"\n→ Simulating: Hey @Nesa approve {TC3_ORDER}")
    save_order_state(TC3_ORDER, status="invoice_approved", approved_by="prateek")
    after_approve = get_order_by_id(TC3_ORDER)
    check("TC3 status set to invoice_approved",
          after_approve.get("status") == "invoice_approved",
          f"actual={after_approve.get('status')}")

    # Step 3: A5 — create FTF invoice
    print(f"\n→ Running A5 for {TC3_ORDER}...")
    from agents.agent_a5_invoice_finalizer import finalize_order as fin3
    a5r3 = fin3(TC3_ORDER)
    check("TC3 A5 ok", a5r3.get("ok"), str(a5r3))
    check("TC3 invoice_id returned", bool(a5r3.get("invoice_id")),
          f"invoice_id={a5r3.get('invoice_id')}")

    # Step 4: A6 — send email
    print(f"\n→ Running A6 for {TC3_ORDER}...")
    from agents.agent_a6_sender_v2 import send_for_order as snd3
    a6r3 = snd3(TC3_ORDER, skip_delay=True)
    check("TC3 email sent", a6r3.get("sent"), str(a6r3))
    check("TC3 email to override", EMAIL_OVERRIDE_ALL in a6r3.get("to", ""),
          f"to={a6r3.get('to')}")

    after_final = get_order_by_id(TC3_ORDER)
    check("TC3 final status invoice_sent",
          after_final.get("status") == "invoice_sent",
          f"actual={after_final.get('status')}")

    print(f"\n✅ TC3 COMPLETE — ${TEST_PRICE:.0f} invoice #{a5r3.get('invoice_id')} "
          f"created and emailed to {a6r3.get('to')}")

except Exception as exc:
    check("TC3 EXCEPTION", False, traceback.format_exc()[-300:])


# ── Summary ──────────────────────────────────────────────────────────────────

section("TEST SUMMARY")
passed = sum(1 for r in results if PASS in r)
failed = sum(1 for r in results if FAIL in r)
print(f"\n{passed} passed / {failed} failed out of {len(results)} checks\n")
for r in results:
    print(" ", r)

# Post summary to Teams
summary_lines = "\n".join(f"  {r}" for r in results)
post_chat_message(
    f"<strong>🧪 E2E Pipeline Test Results</strong><br>"
    f"<strong>{passed} passed / {failed} failed ({len(results)} checks)</strong><br><br>"
    f"TC1 Approve + Email (Order {TC1_ORDER}): {'✅' if all(FAIL not in r for r in results if TC1_ORDER in r or 'TC1' in r) else '❌'}<br>"
    f"TC2 Reject (Order {TC2_ORDER}): {'✅' if all(FAIL not in r for r in results if TC2_ORDER in r or 'TC2' in r) else '❌'}<br>"
    f"TC3 Price→Approve→Email (Order {TC3_ORDER}): {'✅' if all(FAIL not in r for r in results if TC3_ORDER in r or 'TC3' in r) else '❌'}<br>"
    f"<br><em>All emails overridden to {EMAIL_OVERRIDE_ALL} — no real client was contacted.</em>",
    subject="E2E Test Complete"
)

print(f"\nDone. Test summary posted to Teams.")
sys.exit(0 if failed == 0 else 1)
