"""Diagnostic: dump the prod FTF API response for an order via the same get_order() A3 uses."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
from dotenv import load_dotenv
load_dotenv()
from core.ftf_client import get_order

for oid in sys.argv[1:] or ["1000285363"]:
    print(f"\n=== {oid} ===")
    try:
        d = get_order(oid)
        print("keys:", list(d.keys()))
        for k in ("invoiced", "paid", "due_amount", "invoice_id", "ng_invoice_needed",
                  "status", "ng_status_desc", "invoice", "is_invoiced", "has_invoice"):
            if k in d:
                print(f"  {k} = {d[k]!r}")
        print("FULL:", json.dumps(d, default=str)[:1200])
    except Exception as exc:
        print("ERROR:", exc)
