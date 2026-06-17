"""probe_trackflow.py — READ-ONLY schema discovery for ng_log_trackflow.

One-off diagnostic so we can build the "who generated the invoice" lookup against the
REAL production schema instead of guessing column names. Runs on the GitHub Actions
runner (which can reach the firewalled RDS); prints to the Actions log. Read-only:
information_schema + SELECTs only, no writes.

Usage:  python scripts/probe_trackflow.py [order_id]
        default order_id = 1000285363 (a known invoiced order)
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

ORDER_ID = sys.argv[1] if len(sys.argv) > 1 else "1000285363"


def main():
    con = _connect()
    cur = con.cursor()

    print(f"DB = {MYSQL_DB}")
    print(f"probe order = {ORDER_ID}\n")

    # 1) Columns of ng_log_trackflow
    cur.execute(
        "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='ng_log_trackflow' ORDER BY ORDINAL_POSITION",
        (MYSQL_DB,),
    )
    cols = cur.fetchall()
    if not cols:
        print("!! ng_log_trackflow not found in this DB. Searching for similar tables:")
        cur.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s "
            "AND (TABLE_NAME LIKE '%%track%%' OR TABLE_NAME LIKE '%%log%%')",
            (MYSQL_DB,),
        )
        for r in cur.fetchall():
            print("   candidate table:", r[0])
        cur.close(); con.close()
        return

    col_names = [c[0] for c in cols]
    print("=== ng_log_trackflow columns ===")
    for name, dtype in cols:
        print(f"   {name:30s} {dtype}")

    # Heuristic: find the order-id column and the user/actor column
    order_col = next((c for c in col_names if "order" in c.lower()), None)
    user_col = next((c for c in col_names
                     if any(k in c.lower() for k in ("user", "emp", "staff", "actor", "by", "name"))), None)
    type_col = next((c for c in col_names if c.lower() in ("ng_type", "type", "action", "event")), None)
    date_cols = [c for c in col_names if any(k in c.lower() for k in ("dt", "date", "time", "stamp"))]
    text_cols = [c for c in col_names if any(k in c.lower() for k in ("text", "msg", "message", "note", "desc", "detail"))]

    print(f"\nguessed order_col = {order_col!r} | user_col = {user_col!r} | "
          f"type_col = {type_col!r} | date_cols = {date_cols} | text_cols = {text_cols}")

    # 2) Distinct event-type values (to find the 'invoice generated' marker)
    if type_col:
        cur.execute(f"SELECT DISTINCT `{type_col}` FROM ng_log_trackflow LIMIT 50")
        print(f"\n=== distinct `{type_col}` values ===")
        for r in cur.fetchall():
            print("   ", r[0])

    # 3) Recent rows for the probe order — full row dump
    if order_col:
        order_by = f"ORDER BY `{date_cols[0]}` DESC" if date_cols else ""
        cur.execute(
            f"SELECT * FROM ng_log_trackflow WHERE `{order_col}`=%s {order_by} LIMIT 25",
            (ORDER_ID,),
        )
        rows = cur.fetchall()
        header = [d[0] for d in cur.description]
        print(f"\n=== last {len(rows)} ng_log_trackflow rows for order {ORDER_ID} ===")
        print("   cols:", header)
        for r in rows:
            print("   ", dict(zip(header, [str(v)[:80] for v in r])))
    else:
        print("\n!! no order-like column found — cannot pull rows for the probe order")

    cur.close()
    con.close()
    print("\nprobe complete (read-only).")


if __name__ == "__main__":
    main()
