"""One-time backfill: write pricing_needed + condo_rejected orders to OneDrive Excel.

These orders were processed by A3 before append_approval_row() was added to the
pricing_needed and condo_rejected code paths. They exist in pipeline state but
were never written to the approval spreadsheet.

Run via:
  GitHub Actions → Backfill Excel Rows (One-Time) → Run workflow
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from config.settings import FTF_ORDER_URL
from core.excel_db import get_orders_by_status
from core.ftf_mysql import get_order_details
from core.logger import get_logger
from core.onedrive_excel_client import (
    append_approval_row,
    auto_reject_condo_row,
    get_all_approval_order_ids,
)

log = get_logger("backfill_excel_rows")


def _parse_draft(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def main():
    pricing_needed = get_orders_by_status("pricing_needed")
    condo_rejected  = get_orders_by_status("condo_rejected")
    targets = pricing_needed + condo_rejected

    log.info(
        "backfill targets: %d pricing_needed + %d condo_rejected = %d total",
        len(pricing_needed), len(condo_rejected), len(targets),
    )

    existing = get_all_approval_order_ids()
    log.info("already in Excel: %d rows", len(existing))

    posted = skipped = errors = 0

    for order in targets:
        order_id     = order["order_id"]
        status       = order["status"]
        client_name  = order.get("client_name") or "Unknown"
        address      = order.get("property_address") or ""
        service_type = order.get("service_type") or ""
        ftf_link     = f"{FTF_ORDER_URL}{order_id}"
        draft        = _parse_draft(order.get("invoice_draft"))

        if order_id in existing:
            log.info("skip %s — already in Excel", order_id)
            skipped += 1
            continue

        # Fetch real FTF status — also used to skip Canceled orders
        try:
            details = get_order_details(order_id)
            order_status = str(details.get("ng_status_desc") or "")
            if int(details.get("ng_status") or 1) == 0:
                log.info("skip %s — Canceled in FTF, not posting to Excel", order_id)
                skipped += 1
                continue
        except Exception:
            order_status = ""

        if status == "pricing_needed":
            service    = service_type or "Unknown — see notes"
            amount     = float(order.get("estimate_amount") or 0.0)
            confidence = "LOW"
            escalate   = True
            pn_reason  = draft.get("pricing_reasoning") or "AI could not determine price"
            if len(pn_reason) > 200:
                pn_reason = pn_reason[:200] + "..."
            notes = (
                f"MANUAL PRICING REQUIRED — {pn_reason}. "
                "Enter the correct amount in the Amount column, then set Action = Approve."
            )

        else:  # condo_rejected
            service    = "CONDO — Cannot Survey"
            amount     = 0.0
            confidence = "N/A"
            escalate   = True
            raw_reason = (
                draft.get("pricing_reasoning")
                or "unit number or legal description indicates airspace/condo unit"
            )
            condo_reason = raw_reason.split(".")[0][:150]
            notes = (
                f"CONDO ORDER — Cannot survey. {condo_reason}. "
                "AUTO-REJECTED. ACTION REQUIRED: Contact client to explain that a boundary "
                "survey is not possible on a condo/airspace unit. Arrange refund or redirect "
                "to an appropriate service (e.g. interior unit measurement)."
            )

        try:
            append_approval_row(
                order_id=order_id,
                client_name=client_name,
                address=address,
                service=service,
                amount=amount,
                confidence=confidence,
                escalate=escalate,
                ftf_link=ftf_link,
                order_status=order_status,
                notes=notes,
            )
            log.info("posted order=%s status=%s", order_id, status)

            if status == "condo_rejected":
                try:
                    auto_reject_condo_row(order_id)
                    log.info("auto-rejected condo order=%s", order_id)
                except Exception as exc:
                    log.warning("auto_reject_condo_row failed order=%s: %s", order_id, exc)

            posted += 1

        except Exception as exc:
            log.error("append_approval_row failed order=%s: %s", order_id, exc)
            errors += 1

    result = {
        "posted":         posted,
        "skipped":        skipped,
        "errors":         errors,
        "pricing_needed": len(pricing_needed),
        "condo_rejected": len(condo_rejected),
    }
    log.info("backfill complete: %s", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
