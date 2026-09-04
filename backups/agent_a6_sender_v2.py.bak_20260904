"""Agent A6 — Sender v2 (Invoice Pipeline)

Delivers the FTF invoice using the portal authenticated as nesa (HR user).
This attributes invoice generation and delivery to nesa in the FTF audit trail.

Steps (via ftf_portal_client):
  1. POST /admin/login         → nesa session cookie
  2. POST /order/invoice       → generates invoice PDF in FTF order repo
  3. POST /order/deliver_invoice → FTF sends email via SendGrid, logs nesa as sender

EMAIL_OVERRIDE_ALL: when set, overrides recipient to override address (staging safety).

Status flow: invoice_finalized → invoice_sent
"""

import contextlib
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import EMAIL_OVERRIDE_ALL, INVOICE_DRY_RUN
from core.excel_db import get_orders_by_status, get_order_by_id, save_order_state, log_decision
from core.exceptions import AgentError, DeliveryAttemptedError, PreDeliveryError
from core.ftf_portal_client import deliver_invoice_as_nesa
from core.logger import get_logger

AGENT_NAME = "agent_a6_sender_v2"
log = get_logger(AGENT_NAME)

# In-run retries for the SAFE pre-delivery phase only (login / PDF). The deliver
# POST itself is never blindly retried — a lost ack could mean a duplicate email.
MAX_RETRY = 3

# Terminal send states — once an order reaches either, A6 must never send again.
#   invoice_sent     = delivery confirmed.
#   invoice_sending  = delivery was ATTEMPTED (outcome unknown). Held for a human to
#                      confirm/resend; auto-resend is forbidden to avoid duplicates.
_NO_RESEND_STATES = {"invoice_sent", "invoice_sending"}

# Defense-in-depth against concurrent senders. The prod single-runner host already
# serializes A0 + the watcher via a shared shell flock, but that lives outside the
# code; this OS advisory lock makes the guard-read -> tombstone -> POST section atomic
# even if A6 is ever invoked outside the wrappers (POSIX). No-op where fcntl is absent
# (e.g. Windows dev/QA) — documented, not silent.
_SEND_LOCK_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", ".a6_send.lock")


@contextlib.contextmanager
def _send_lock():
    try:
        import fcntl
    except ImportError:
        log.debug("fcntl unavailable — A6 send lock is a no-op on this platform")
        yield
        return
    os.makedirs(os.path.dirname(_SEND_LOCK_FILE), exist_ok=True)
    fd = open(_SEND_LOCK_FILE, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            fd.close()


def send_for_order(order_id: str) -> dict:
    """Generate and deliver FTF invoice as nesa for one finalized order."""
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"send_for_order: order {order_id} not in DB")

    # Dry-run: resolve the recipient EXACTLY as the real path would (override or client email),
    # log it, and stop — no portal call, no email, no state advance.
    if INVOICE_DRY_RUN:
        client_email = db_row.get("customer_email", "")
        recipient    = EMAIL_OVERRIDE_ALL or client_email
        log.warning(
            "DRY_RUN A6: would deliver invoice for order=%s to recipient=%s "
            "(override=%s, client_email=%s) — NO portal call, NO email, NO state advance",
            order_id, recipient or "(none)", EMAIL_OVERRIDE_ALL or "(none)", client_email or "(none)",
        )
        return {"sent": False, "dry_run": True, "to": recipient,
                "invoice_id": db_row.get("invoice_id", "")}

    # Hold the OS advisory lock across the ENTIRE guard-read -> tombstone -> POST -> save
    # section, so the read-then-write idempotency check is atomic even under concurrent
    # senders (defense-in-depth beyond the shell flock).
    with _send_lock():
        # Re-read status FRESH under the lock — a concurrent run may have advanced it.
        fresh = get_order_by_id(order_id) or db_row

        # ── Idempotency guard: never send twice. ────────────────────────────────
        # FTF exposes no "already sent" flag, so our local status is the source of truth.
        # invoice_sent = confirmed; invoice_sending = a delivery was already attempted
        # (outcome unknown) and is awaiting human confirmation — auto-resend is forbidden.
        cur_status = str(fresh.get("status") or "")
        if cur_status in _NO_RESEND_STATES:
            log.warning("send_for_order: order=%s status=%s — skipping to avoid duplicate send",
                        order_id, cur_status)
            return {"sent": False, "skipped": cur_status, "invoice_id": fresh.get("invoice_id", "")}

        invoice_id = fresh.get("invoice_id") or ""
        if not invoice_id or "TEST" in str(invoice_id).upper():
            raise AgentError(
                f"send_for_order: order {order_id} has no real invoice_id ({invoice_id!r}) — "
                "run A5 first to create the invoice in FTF"
            )

        client_email    = fresh.get("customer_email", "")
        property_address = fresh.get("property_address", "")

        def _mark_sending() -> None:
            """Durable 'about to send' tombstone, persisted immediately before the deliver
            POST. Once set, any crash/timeout at-or-after the POST leaves status=invoice_sending
            so the order is never auto-resent (it surfaces for manual confirmation instead)."""
            save_order_state(
                order_id,
                status="invoice_sending",
                send_attempted_at=datetime.now(timezone.utc).isoformat(),
            )

        # Retry ONLY the safe pre-delivery phase (login/PDF). The deliver POST is attempted
        # at most once per run; an ambiguous failure is never retried.
        last_pre_exc = None
        for attempt in range(1, MAX_RETRY + 1):
            try:
                result = deliver_invoice_as_nesa(
                    order_id=order_id,
                    client_email=client_email,
                    property_address=property_address,
                    on_before_deliver=_mark_sending,
                )
                break
            except PreDeliveryError as exc:
                # Nothing was sent (failed before the deliver POST). Status is still
                # invoice_finalized → safe to retry in-run, then next run.
                last_pre_exc = exc
                log.warning("A6 pre-delivery attempt=%d failed order=%s (nothing sent): %s",
                            attempt, order_id, exc)
            except DeliveryAttemptedError as exc:
                # The deliver POST was attempted; the email may have gone out. Status is
                # already invoice_sending (tombstone) → DO NOT retry or revert. Surface it.
                log.error("A6 delivery AMBIGUOUS order=%s — held as invoice_sending for manual "
                          "confirmation (no auto-resend): %s", order_id, exc)
                raise
        else:
            # Exhausted pre-delivery retries without ever attempting the POST.
            raise AgentError(
                f"send_for_order: pre-delivery failed for order {order_id} after {MAX_RETRY} attempts "
                f"(nothing sent — will retry next run): {last_pre_exc}"
            )

        # Delivery confirmed. Promote the tombstone to the terminal sent state. If THIS save
        # fails, status stays invoice_sending → still no resend (just needs manual confirm).
        # Persist the FTF Pay Now link (audit) only when present — never overwrite with a blank.
        pay_link = result.get("pay_link") or ""
        extra = {"pay_link": pay_link} if pay_link else {}
        save_order_state(
            order_id,
            status="invoice_sent",
            sent_at=datetime.now(timezone.utc).isoformat(),
            **extra,
        )

        log_decision(
            AGENT_NAME,
            decision="invoice_sent",
            order_id=order_id,
            reason=(f"Invoice delivered via FTF portal as nesa to {result['to']} pdf={result['pdf']} "
                    f"pay_link={'present' if pay_link else 'missing'}"),
            input_summary=f"invoice_id={invoice_id}",
            output_summary=f"sent_to={result['to']}",
            model_used=None,
        )

        log.info("invoice sent order=%s invoice_id=%s to=%s pdf=%s",
                 order_id, invoice_id, result["to"], result["pdf"])
        return {"sent": True, "to": result["to"], "invoice_id": invoice_id}


def run() -> dict:
    """Deliver invoices for all invoice_finalized orders.

    Accounting: processed == sent + skipped + needs_confirmation + errors.
      sent              = delivered this run.
      skipped           = already advanced / dry-run (no work needed).
      needs_confirmation = delivery was ATTEMPTED but outcome unknown (invoice_sending):
                          a human must verify in SendGrid/FTF — NOT auto-resent. Distinct
                          from errors so the dangerous case is never buried.
      errors            = benign failure (e.g. FTF down before send) — auto-retries next run.
    """
    orders  = get_orders_by_status("invoice_finalized")
    summary = {"processed": 0, "sent": 0, "skipped": 0, "needs_confirmation": 0, "errors": 0}

    for db_row in orders:
        order_id = db_row["order_id"]
        try:
            fresh = get_order_by_id(order_id)
            if fresh and fresh.get("status") != "invoice_finalized":
                log.warning("order %s already processed (status=%s) — skipping",
                            order_id, fresh.get("status"))
                summary["skipped"] += 1
            else:
                res = send_for_order(order_id)
                summary["sent" if res.get("sent") else "skipped"] += 1
        except DeliveryAttemptedError as exc:
            # Ambiguous: the email may have gone out. Held at invoice_sending for a human.
            log.error("send AMBIGUOUS order=%s — needs manual confirmation: %s", order_id, exc)
            summary["needs_confirmation"] += 1
        except Exception as exc:
            log.error("send failed order=%s: %s", order_id, exc)
            summary["errors"] += 1
        summary["processed"] += 1

    log.info("sender_v2 complete: %s", summary)
    return summary


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="A6 Sender v2 — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--order-id")
    parser.add_argument("--force", action="store_true",
                        help="Allow sending an order that is not yet invoice_finalized "
                             "(bypasses the approval gate — operator footgun).")
    args = parser.parse_args(argv)

    if args.order_id:
        # Guard the manual path to the same gate the pipeline uses: only a finalized order
        # may be sent, unless --force is given. (The duplicate-send guard inside
        # send_for_order always applies regardless.)
        row = get_order_by_id(args.order_id)
        status = str((row or {}).get("status") or "")
        if not args.force and status != "invoice_finalized":
            print(f"REFUSED: order {args.order_id} is status={status!r}, not 'invoice_finalized'. "
                  "Pass --force to send anyway (bypasses the approval gate).")
            sys.exit(1)
        result = send_for_order(args.order_id)
        print(result)
    elif args.run_now:
        print(run())


if __name__ == "__main__":
    main()
