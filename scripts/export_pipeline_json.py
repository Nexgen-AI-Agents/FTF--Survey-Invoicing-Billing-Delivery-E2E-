"""Export pipeline_state.xlsx → data/pipeline_state.json for the live dashboard."""
import json
import os
import sys
from datetime import datetime, timezone

import openpyxl

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXCEL_PATH = os.path.join(REPO_ROOT, "data", "invoice_pipeline_state.xlsx")
JSON_PATH  = os.path.join(REPO_ROOT, "data", "pipeline_state.json")

STATUS_ORDER = [
    "invoice_needed", "data_collected", "invoice_draft_posted",
    "invoice_approved", "invoice_finalized", "invoice_sent",
    "on_hold", "invoice_rejected", "invoice_modification_requested",
]


def _coerce(v):
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def main():
    if not os.path.exists(EXCEL_PATH):
        print("Excel not found — writing empty JSON", file=sys.stderr)
        payload = {"orders": [], "generated_at": datetime.now(timezone.utc).isoformat(), "total": 0}
    else:
        wb = openpyxl.load_workbook(EXCEL_PATH)
        ws = wb["pipeline_state"]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            orders = []
        else:
            headers = [str(h) if h is not None else "" for h in rows[0]]
            orders = [
                {headers[i]: _coerce(row[i] if i < len(row) else None) for i in range(len(headers))}
                for row in rows[1:]
            ]

        # Status summary counts
        status_counts = {}
        for o in orders:
            s = o.get("status") or "unknown"
            status_counts[s] = status_counts.get(s, 0) + 1

        payload = {
            "orders":        orders,
            "status_counts": status_counts,
            "total":         len(orders),
            "generated_at":  datetime.now(timezone.utc).isoformat(),
        }

    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, default=str, indent=2)
    print(f"Exported {payload['total']} orders -> {JSON_PATH}")


if __name__ == "__main__":
    main()
