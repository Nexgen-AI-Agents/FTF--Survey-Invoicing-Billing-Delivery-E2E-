"""qa_a6_idempotency.py — Prod-safe QA for A6 exactly-once invoice sending.

Proves that NO failure mode can send a customer the invoice email twice, and that
FTF-down (pre-delivery) failures stay safely retryable. Fully offline:
  * temp state store (never touches data/invoice_pipeline_state.xlsx)
  * the FTF portal deliver call is monkeypatched — NO login, NO email, NO network
  * synthetic numeric order id

Run:  python scripts/qa_a6_idempotency.py
Exit 0 = all scenarios pass.
"""
import os
import sys
import tempfile

# Make the regression guard run on ANY console (the prod server / Windows cp1252 would
# otherwise crash on a non-ASCII char before a single assertion executes).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_11_invoice_pipeline"))

import core.excel_db as excel_db
from core.exceptions import AgentError, DeliveryAttemptedError, PreDeliveryError
from agents import agent_a6_sender_v2 as a6

ORDER_ID = "9000090001"           # synthetic, matches ^\d{7,12}$
INVOICE_ID = "349001"             # no "TEST" substring -> passes A6's real-invoice check

_fails = []


def _check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    if not cond:
        _fails.append(name)


def _reset_order(status="invoice_finalized"):
    excel_db.save_order_state(
        ORDER_ID, status=status, invoice_id=INVOICE_ID,
        customer_email="qa@example.test", property_address="1 QA Way, Test FL",
    )


def _status():
    return str((excel_db.get_order_by_id(ORDER_ID) or {}).get("status") or "")


class Counter:
    """A fake deliver_invoice_as_nesa. Counts how many times the email was actually
    'sent' (POST reached) vs how many times the function was merely invoked."""
    def __init__(self, mode):
        self.mode = mode
        self.invoked = 0       # function entered
        self.sent = 0          # email actually delivered (POST succeeded)

    def __call__(self, order_id, client_email, property_address="", subject="",
                 message="", on_before_deliver=None):
        self.invoked += 1
        if self.mode == "predelivery":
            # FTF down at login/PDF — tombstone NEVER set, nothing sent.
            raise PreDeliveryError("simulated FTF down (login/PDF)")
        # login + PDF succeeded -> tombstone set right before the (would-be) POST
        if on_before_deliver is not None:
            on_before_deliver()
        if self.mode == "ambiguous":
            raise DeliveryAttemptedError("simulated lost ack on deliver POST")
        # success
        self.sent += 1
        return {"sent": True, "to": client_email or "qa@example.test",
                "pdf": f"invoice/invoice-{order_id}-order.pdf"}


def scenario_success():
    print("Scenario 1: success -> sent once; second call is a no-op (guard)")
    _reset_order()
    fake = Counter("success")
    a6.deliver_invoice_as_nesa = fake
    r1 = a6.send_for_order(ORDER_ID)
    _check("first call sent", r1.get("sent") is True)
    _check("status invoice_sent", _status() == "invoice_sent", _status())
    r2 = a6.send_for_order(ORDER_ID)
    _check("second call skipped (no resend)", r2.get("sent") is False and r2.get("skipped") == "invoice_sent")
    _check("email delivered exactly once", fake.sent == 1, f"sent={fake.sent}")


def scenario_predelivery():
    print("Scenario 2: FTF down before send -> retried in-run, stays retryable, nothing sent")
    _reset_order()
    fake = Counter("predelivery")
    a6.deliver_invoice_as_nesa = fake
    raised = False
    try:
        a6.send_for_order(ORDER_ID)
    except AgentError:
        raised = True
    _check("raised after retries", raised)
    _check("retried MAX_RETRY times", fake.invoked == a6.MAX_RETRY, f"invoked={fake.invoked}")
    _check("nothing sent", fake.sent == 0)
    _check("status still invoice_finalized (retryable)", _status() == "invoice_finalized", _status())
    # Now FTF recovers -> one clean send
    fake2 = Counter("success")
    a6.deliver_invoice_as_nesa = fake2
    a6.send_for_order(ORDER_ID)
    _check("recovers and sends once", fake2.sent == 1 and _status() == "invoice_sent")


def scenario_ambiguous():
    print("Scenario 3: deliver POST attempted then fails -> held as invoice_sending, never resent")
    _reset_order()
    fake = Counter("ambiguous")
    a6.deliver_invoice_as_nesa = fake
    raised = False
    try:
        a6.send_for_order(ORDER_ID)
    except DeliveryAttemptedError:
        raised = True
    _check("raised DeliveryAttemptedError", raised)
    _check("status invoice_sending (tombstone)", _status() == "invoice_sending", _status())
    # Re-run must NOT resend
    r2 = a6.send_for_order(ORDER_ID)
    _check("re-run skipped (no resend)", r2.get("sent") is False and r2.get("skipped") == "invoice_sending")
    _check("deliver attempted exactly once", fake.invoked == 1, f"invoked={fake.invoked}")


def scenario_postsave_crash():
    print("Scenario 4: deliver succeeds but invoice_sent save crashes -> no duplicate on retry")
    _reset_order()
    fake = Counter("success")
    a6.deliver_invoice_as_nesa = fake

    real_save = excel_db.save_order_state

    def flaky_save(order_id, **fields):
        if fields.get("status") == "invoice_sent":
            raise RuntimeError("simulated state-store crash after send")
        return real_save(order_id, **fields)

    # Patch the name A6 actually calls (imported into the a6 module namespace).
    a6.save_order_state = flaky_save
    raised = False
    try:
        a6.send_for_order(ORDER_ID)
    except Exception:
        raised = True
    a6.save_order_state = real_save     # restore
    _check("raised on save crash", raised)
    _check("status held at invoice_sending", _status() == "invoice_sending", _status())
    # Re-run must NOT resend
    a6.deliver_invoice_as_nesa = Counter("success")
    r2 = a6.send_for_order(ORDER_ID)
    _check("re-run skipped (no duplicate)", r2.get("sent") is False)
    _check("email delivered exactly once total", fake.sent == 1, f"sent={fake.sent}")


def scenario_dry_run():
    print("Scenario 5: DRY_RUN -> no deliver call, no state write")
    _reset_order()
    fake = Counter("success")
    a6.deliver_invoice_as_nesa = fake
    a6.INVOICE_DRY_RUN = True
    try:
        r = a6.send_for_order(ORDER_ID)
    finally:
        a6.INVOICE_DRY_RUN = False
    _check("dry_run returned", r.get("dry_run") is True)
    _check("no deliver call", fake.invoked == 0)
    _check("status unchanged", _status() == "invoice_finalized", _status())


def scenario_run_accounting():
    print("Scenario 6: run() buckets an ambiguous delivery as needs_confirmation, not errors")
    _reset_order()
    a6.deliver_invoice_as_nesa = Counter("ambiguous")
    summary = a6.run()
    _check("needs_confirmation counted", summary.get("needs_confirmation") == 1, str(summary))
    _check("not counted as error", summary.get("errors") == 0, str(summary))
    _check("processed == sent+skipped+needs_confirmation+errors",
           summary["processed"] == summary["sent"] + summary["skipped"]
           + summary["needs_confirmation"] + summary["errors"], str(summary))
    _check("order held at invoice_sending", _status() == "invoice_sending", _status())


def scenario_resolver_guard():
    print("Scenario 7: resolve_stuck_send --retry refuses without explicit verification")
    import resolve_stuck_send as rss
    _reset_order(status="invoice_sending")
    # --retry alone must REFUSE (exit 1) and leave status untouched (no double-send path).
    refused = False
    try:
        rss.main(["--order-id", ORDER_ID, "--retry"])
    except SystemExit as e:
        refused = (e.code == 1)
    _check("--retry refused without --i-verified-not-delivered", refused)
    _check("status still invoice_sending after refusal", _status() == "invoice_sending", _status())
    # With the explicit acknowledgement it reverts so A6 can re-send.
    rss.main(["--order-id", ORDER_ID, "--retry", "--i-verified-not-delivered"])
    _check("verified retry reverts to invoice_finalized", _status() == "invoice_finalized", _status())
    # --confirm-sent marks sent (no resend).
    _reset_order(status="invoice_sending")
    rss.main(["--order-id", ORDER_ID, "--confirm-sent"])
    _check("confirm-sent marks invoice_sent", _status() == "invoice_sent", _status())


def main():
    # Redirect the state store to a throwaway temp file — never touch real prod state.
    tmp = os.path.join(tempfile.mkdtemp(prefix="ftf_qa_"), "qa_state.xlsx")
    excel_db.EXCEL_PATH = tmp
    print(f"QA state store: {tmp}\n")

    scenario_success()
    scenario_predelivery()
    scenario_ambiguous()
    scenario_postsave_crash()
    scenario_dry_run()
    scenario_run_accounting()
    scenario_resolver_guard()

    print()
    if _fails:
        print(f"RESULT: FAIL ({len(_fails)} checks failed): {_fails}")
        sys.exit(1)
    print("RESULT: PASS — every failure mode sends at most once; FTF-down stays retryable.")


if __name__ == "__main__":
    main()
