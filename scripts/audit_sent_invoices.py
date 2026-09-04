#!/usr/bin/env python3
"""Post-send audit — did the client actually receive a usable quote/invoice email?

Why this exists
---------------
On 2026-09-04 the team reported orders 289283/289284 as "client received the quote email, no
quote in order". The pipeline had done everything right — priced, approved, invoice created in
FTF, email delivered — but the BODY it sent was missing "Invoice Amount: $X" and the
"View Invoice" link, so the client got a quote email with no price and no document. Nothing in
the pipeline noticed: A6 logged `invoice sent` and moved on. The defect surfaced a day later,
through the client, and a human had to re-send by hand.

A send is not "done" because the POST returned 200. It is done when the email that landed in
FTF's own delivery log contains what a client needs. This script checks exactly that, straight
from `ng_email_delivered` (FTF's record of what was actually mailed) and reports anything that
does not measure up so a human can re-send it the same hour instead of the next day.

Deliberately narrow and safe:
  * READ-ONLY. Touches MySQL with SELECTs only. Never opens, reads or writes the Excel sheet,
    never re-sends an email, never changes an order.
  * Audits only what nesa sent (`ng_user LIKE 'nesa%'`) — human sends are not ours to judge.
  * Exit code 1 when something is wrong, so the caller can page; 0 when clean.

Usage:
  python scripts/audit_sent_invoices.py                 # last 24h, print report
  python scripts/audit_sent_invoices.py --hours 2       # last 2h (watcher cadence)
  python scripts/audit_sent_invoices.py --hours 2 --alert   # + email NOTIFICATION_TO_EMAILS
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.ftf_mysql import _connect  # noqa: E402
from core.logger import get_logger  # noqa: E402

log = get_logger("audit_sent_invoices")

# What a delivery email must carry to be worth sending. Each maps to something the client needs:
#   Pay Now        — they can pay without calling us
#   Invoice Amount — they know the price (its absence is what was reported on 2026-09-04)
#   View Invoice   — they can open the document if the attachment fails
_REQUIRED = ("Pay Now", "Invoice Amount", "View Invoice")


def audit(hours: int) -> list[dict]:
    """Return one dict per nesa delivery email in the window, worst first."""
    since = datetime.now() - timedelta(hours=hours)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ng_eid, ng_order, ng_dtentered, ng_email_subject, ng_email_content "
                "FROM ng_email_delivered "
                "WHERE ng_user LIKE %s AND ng_dtentered >= %s "
                "ORDER BY ng_eid",
                ("nesa%", since.strftime("%Y-%m-%d %H:%M:%S")),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    out = []
    for r in rows:
        body = str(r.get("ng_email_content") or "")
        missing = [tok for tok in _REQUIRED if tok not in body]
        out.append({
            "order_id": str(r.get("ng_order") or ""),
            "eid":      r.get("ng_eid"),
            "at":       str(r.get("ng_dtentered") or ""),
            "subject":  str(r.get("ng_email_subject") or ""),
            "missing":  missing,
        })
    # Worst first so a human reads the problems, not the noise.
    out.sort(key=lambda x: (-len(x["missing"]), x["at"]))
    return out


def _alert(bad: list[dict], hours: int) -> None:
    """Page the internal notification list. Never raises — an alert failure must not mask the
    finding, which is already in the log and the exit code."""
    orders = ", ".join(b["order_id"] for b in bad[:12])
    more = f" (+{len(bad) - 12} more)" if len(bad) > 12 else ""
    script = os.path.join(os.path.dirname(__file__), "notify_failure_email.py")
    try:
        subprocess.run(
            [sys.executable, script,
             "--workflow", (f"FTF invoice emails INCOMPLETE — {len(bad)} client email(s) in the "
                            f"last {hours}h had no amount / no invoice link: {orders}{more}"),
             "--run-url", "scripts/audit_sent_invoices.py"],
            check=False, timeout=120,
        )
    except Exception as exc:  # pragma: no cover - best effort
        log.warning("audit alert could not be sent: %s", exc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hours", type=int, default=24, help="look-back window (default 24)")
    ap.add_argument("--alert", action="store_true", help="email NOTIFICATION_TO_EMAILS on failures")
    args = ap.parse_args()

    rows = audit(args.hours)
    if not rows:
        log.info("audit: no nesa delivery emails in the last %dh — nothing to check", args.hours)
        return 0

    bad = [r for r in rows if r["missing"]]
    for r in bad:
        log.error("audit: order=%s email eid=%s at %s is MISSING %s — client cannot see %s",
                  r["order_id"], r["eid"], r["at"], "+".join(r["missing"]),
                  "the price" if "Invoice Amount" in r["missing"] else "part of the invoice")

    log.info("audit: %d nesa email(s) in last %dh — %d complete, %d incomplete",
             len(rows), args.hours, len(rows) - len(bad), len(bad))
    print(f"checked={len(rows)} ok={len(rows) - len(bad)} incomplete={len(bad)}")
    for r in bad:
        print(f"  BAD order={r['order_id']} at={r['at']} missing={'+'.join(r['missing'])}")

    if bad and args.alert:
        _alert(bad, args.hours)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
