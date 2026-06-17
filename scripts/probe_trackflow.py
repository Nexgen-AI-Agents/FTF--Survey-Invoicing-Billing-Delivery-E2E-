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


def _vals(row):
    """Return a row's values as a list, whether the cursor yields dicts or tuples."""
    return list(row.values()) if isinstance(row, dict) else list(row)


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
            print("   candidate table:", _vals(r)[0])
        cur.close(); con.close()
        return

    col_pairs = [_vals(c) for c in cols]
    col_names = [c[0] for c in col_pairs]
    print("=== ng_log_trackflow columns ===")
    for name, dtype in col_pairs:
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
            print("   ", _vals(r)[0])

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
            print("   ", dict(zip(header, [str(v)[:80] for v in _vals(r)])))
    else:
        print("\n!! no order-like column found — cannot pull rows for the probe order")

    # 4) What do real invoice-generation events look like? (find the exact marker + user format)
    print("\n=== recent ng_type='Invoice' events (any order) ===")
    cur.execute(
        "SELECT ng_order, ng_user, ng_action, LEFT(ng_value,60) AS ng_value, "
        "LEFT(ng_result,60) AS ng_result, ng_dtentered, LEFT(notes,40) AS notes "
        "FROM ng_log_trackflow WHERE ng_type='Invoice' ORDER BY ng_dtentered DESC LIMIT 15"
    )
    for r in cur.fetchall():
        d = r if isinstance(r, dict) else dict(zip([c[0] for c in cur.description], r))
        print("   ", {k: (str(v)[:60] if v is not None else None) for k, v in d.items()})

    print("\n=== distinct ng_action where ng_type='Invoice' ===")
    cur.execute("SELECT DISTINCT ng_action FROM ng_log_trackflow WHERE ng_type='Invoice' LIMIT 40")
    for r in cur.fetchall():
        print("   ", _vals(r)[0])

    # 5) Match diagnostics for the probe order — int vs string, and ANY type
    for label, val in (("string", ORDER_ID), ("int", int(ORDER_ID) if str(ORDER_ID).isdigit() else ORDER_ID)):
        cur.execute("SELECT COUNT(*) AS c FROM ng_log_trackflow WHERE ng_order=%s", (val,))
        c = _vals(cur.fetchall()[0])[0]
        print(f"\norder {ORDER_ID} as {label}: {c} total trackflow rows")
    cur.execute(
        "SELECT ng_type, COUNT(*) AS c FROM ng_log_trackflow WHERE ng_order=%s GROUP BY ng_type",
        (int(ORDER_ID) if str(ORDER_ID).isdigit() else ORDER_ID,),
    )
    print(f"   by type for {ORDER_ID}:")
    for r in cur.fetchall():
        d = r if isinstance(r, dict) else dict(zip(["ng_type", "c"], r))
        print("     ", d)

    cur.close()
    con.close()
    print("\nprobe complete (read-only).")


if __name__ == "__main__":
    main()
