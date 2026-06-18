"""probe_amount2.py — READ-ONLY: find which column holds the order's amount.

Dumps the full ng_orders row for given order(s) and highlights any column whose
value matches the known REST due_amount, so we learn the real amount column.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.ftf_mysql import _connect

# order_id : known REST due_amount
TARGETS = {"1000285369": 500.0, "1000285368": 400.0, "1000285282": 950.0}


def main():
    con = _connect(); cur = con.cursor()
    for oid, known in TARGETS.items():
        cur.execute("SELECT * FROM ng_orders WHERE ng_order=%s LIMIT 1", (oid,))
        row = cur.fetchone()
        if not row:
            print(f"\n{oid}: no ng_orders row"); continue
        d = row if isinstance(row, dict) else dict(zip([c[0] for c in cur.description], row))
        print(f"\n=== ng_orders {oid} (known REST due_amount={known}) ===")
        hits = []
        for k, v in d.items():
            try:
                if v is not None and abs(float(v) - known) < 0.01:
                    hits.append(k)
            except (ValueError, TypeError):
                pass
        print("  columns matching the amount:", hits or "NONE")
        # print any column whose name hints at money/estimate/quote, with value
        for k, v in d.items():
            if any(t in k.lower() for t in ("amount", "amt", "price", "total", "due", "estimate",
                                            "quote", "fee", "cost", "rate", "paid", "balance", "invoice")):
                print(f"    {k:30s} = {str(v)[:60]}")
    cur.close(); con.close()
    print("\nprobe complete (read-only).")


if __name__ == "__main__":
    main()
