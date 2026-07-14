#!/usr/bin/env python3
"""Bring a SPECIFIC set of FTF order IDs onto the Approvals sheet.

The normal pipeline (A1 flag-hunter) auto-discovers orders by the invoice_needed
flag + an intake watermark — it has no way to target explicit IDs. This one-off
utility seeds a given list of order IDs straight into the pipeline and runs the
per-order data-collection (A2) + pricing/posting (A3) steps for exactly those IDs,
so they land on the OneDrive Approvals tab without touching any other order.

MUST run ON THE PROD SERVER: A2 reads order details from the FTF stage MySQL DB,
which is only reachable from the prod host.

Nothing is approved and no email is sent — this only posts draft rows for review.

Usage (from project root, on the server):
  python scripts/seed_specific_orders.py                 # the default 10 test IDs
  python scripts/seed_specific_orders.py 286740 1000286741 ...   # explicit IDs

IDs may be given as the 6-digit short form (286740) or the full 10-digit order id
(1000286740) — the short form is expanded to 1000-prefixed automatically.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_11_invoice_pipeline"))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

# Default test-order set the operator asked for (6-digit short form).
DEFAULT_IDS = [
    "286740", "286741", "286743", "286744", "286745",
    "286746", "286747", "286748", "286750", "286751",
]


def _normalize(raw: str) -> str:
    """Expand the 6-digit short form to the full 10-digit FTF order id."""
    s = raw.strip()
    if not s:
        return ""
    if len(s) <= 6 and s.isdigit():
        return "1000" + s.zfill(6)
    return s


def main(argv=None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    raw_ids = argv or DEFAULT_IDS
    order_ids = [oid for oid in (_normalize(x) for x in raw_ids) if oid]

    # Imported here (after sys.path/env setup) so module-level config reads succeed.
    from core.excel_db import order_exists, save_order_state, get_order_by_id
    from agents.agent_a2_data_collector import collect_for_order
    from agents.agent_a3_invoice_compiler import compile_for_order
    from core.onedrive_excel_client import _close_session

    print(f"Seeding {len(order_ids)} order(s): {', '.join(order_ids)}")
    results = []
    try:
        for oid in order_ids:
            row = {"order_id": oid, "in_sheet_before": order_exists(oid)}
            try:
                if row["in_sheet_before"]:
                    print(f"  {oid}: already on the sheet — skipping (left as-is)")
                    row["result"] = "already_on_sheet"
                    results.append(row)
                    continue

                # 1. Seed into the pipeline as a freshly-flagged order.
                save_order_state(oid, status="invoice_needed")

                # 2. Collect data (A2) — FTF DB + API. Moves to data_collected / details_missing / excluded.
                c = collect_for_order(oid)
                st = (get_order_by_id(oid) or {}).get("status", "")
                print(f"  {oid}: A2 collect -> status={st} ({c.get('status') if isinstance(c, dict) else c})")

                # 3. Price + post to the sheet (A3) only if data collection succeeded.
                if st == "data_collected":
                    compile_for_order(oid)
                    posted = order_exists(oid)
                    row["result"] = "posted" if posted else "compiled_no_row"
                    print(f"  {oid}: A3 compile -> on_sheet={posted}")
                else:
                    row["result"] = f"stopped_at:{st or 'unknown'}"
            except Exception as exc:  # noqa: BLE001
                row["result"] = f"error:{exc}"
                print(f"  {oid}: ERROR {exc}")
            results.append(row)
    finally:
        try:
            _close_session()
        except Exception:
            pass

    print("\n=== SUMMARY ===")
    for r in results:
        print(f"  {r['order_id']:>12} | {r.get('result','?')}")
    on_sheet = sum(1 for r in results if r.get("result") in ("posted", "already_on_sheet"))
    print(f"\n{on_sheet}/{len(results)} order(s) now on the Approvals sheet. "
          "Nothing approved, no emails sent.")


if __name__ == "__main__":
    main()
