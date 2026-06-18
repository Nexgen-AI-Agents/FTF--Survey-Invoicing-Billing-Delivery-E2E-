"""probe_amount.py — READ-ONLY discovery of where an order's invoiced AMOUNT lives.

For invoiced+unpaid orders, get_order().due_amount IS the amount. For PAID orders
due_amount=0, so we need another source. This probes the FTF MySQL payments/invoice
tables to find the column that holds the invoiced total. Runs on the Actions runner
(prod RDS is firewalled from local). Read-only: information_schema + SELECTs only.

Usage:  python scripts/probe_amount.py [paid_order_id] [unpaid_order_id]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.ftf_mysql import _connect
from config.settings import MYSQL_DB

PAID   = sys.argv[1] if len(sys.argv) > 1 else "1000285363"   # invoiced & paid
UNPAID = sys.argv[2] if len(sys.argv) > 2 else "1000285369"   # invoiced & unpaid (due_amount=500)


def _vals(r):
    return list(r.values()) if isinstance(r, dict) else list(r)


def main():
    con = _connect(); cur = con.cursor()
    print(f"DB={MYSQL_DB} paid={PAID} unpaid={UNPAID}\n")

    # 1) Candidate tables that could hold an amount/invoice/payment
    cur.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s "
        "AND (TABLE_NAME LIKE '%%payment%%' OR TABLE_NAME LIKE '%%invoice%%' "
        "OR TABLE_NAME LIKE '%%order%%') ORDER BY TABLE_NAME",
        (MYSQL_DB,),
    )
    tables = [_vals(r)[0] for r in cur.fetchall()]
    print("=== candidate tables ===")
    for t in tables:
        print("  ", t)

    # 2) For payment/invoice tables, list columns that look monetary + sample by order
    for tbl in ("ng_payments", "ng_orders", "ls_setup_invoices", "ls_setup_invoices_detail",
                "ng_payment_items", "ng_crew_invoice"):
        cur.execute(
            "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
            (MYSQL_DB, tbl),
        )
        cols = [_vals(c) for c in cur.fetchall()]
        if not cols:
            print(f"\n!! {tbl} not found")
            continue
        money = [c for c in cols
                 if any(k in c[0].lower() for k in ("amount", "amt", "total", "price", "due", "paid", "balance", "rate", "fee", "cost"))]
        print(f"\n=== {tbl}: ALL columns ===")
        print("   " + ", ".join(c[0] for c in cols))
        print(f"=== {tbl}: monetary-looking columns ===")
        for name, dt in money:
            print(f"   {name:28s} {dt}")
        # find order-id column (prefer exact 'ng_order'/'order_id', else any with 'order')
        oid_col = next((c[0] for c in cols if c[0].lower() in ("ng_order", "order_id", "ng_order_id")), None) \
            or next((c[0] for c in cols if "order" in c[0].lower()), None)
        print(f"   (order-id column guess: {oid_col})")

        # 3) Sample rows for both orders
        if oid_col:
            for label, oid in (("PAID", PAID), ("UNPAID", UNPAID)):
                sel = ", ".join([f"`{n}`" for n, _ in money][:8]) or "*"
                try:
                    cur.execute(f"SELECT {sel} FROM {tbl} WHERE `{oid_col}`=%s LIMIT 5", (oid,))
                    rows = cur.fetchall()
                    print(f"   [{label} {oid}] {len(rows)} row(s):")
                    for r in rows:
                        d = r if isinstance(r, dict) else dict(zip([n for n, _ in money][:8], r))
                        print("     ", {k: str(v) for k, v in d.items()})
                except Exception as e:
                    print(f"   [{label}] query error: {e}")

    cur.close(); con.close()
    print("\nprobe complete (read-only).")


if __name__ == "__main__":
    main()
