"""Approval poller — A4 → A5 → A6 only.

Called every 2 minutes by .github/workflows/approval_poller.yml.
Checks Teams threads for replies, creates invoices, and sends emails.
Does NOT run A1/A2/A3 (new order discovery/pricing) — those stay in the
30-minute main pipeline so this loop stays fast (~30s per cycle).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from agents.agent_a4_human_gate_v2     import run as run_a4
from agents.agent_a5_invoice_finalizer import run as run_a5
from agents.agent_a6_sender_v2         import run as run_a6
from core.logger import get_logger
from core.teams_graph_client import post_chat_message

log = get_logger("run_approval_poller")

if __name__ == "__main__":
    results = {}
    for label, fn in [("a4_human_gate", run_a4), ("a5_invoice_finalizer", run_a5), ("a6_sender", run_a6)]:
        try:
            results[label] = fn()
        except Exception as exc:
            log.error("%s failed: %s", label, exc)
            results[label] = {"error": str(exc)}

    log.info("approval poller complete: %s", results)
    print(json.dumps(results, indent=2, default=str))

    # Post Teams status only when something actually happened (approved/rejected/sent/errors)
    a4 = results.get("a4_human_gate", {}) or {}
    a6 = results.get("a6_sender", {}) or {}
    errors = [v for v in results.values() if isinstance(v, dict) and v.get("error")]

    acted = (
        a4.get("approved", 0) + a4.get("rejected", 0) + a4.get("on_hold", 0) +
        a4.get("modified", 0) + a6.get("sent", 0) + len(errors)
    )
    if acted:
        lines = []
        if a4.get("approved"):
            lines.append(f"✅ {a4['approved']} approved")
        if a4.get("rejected"):
            lines.append(f"❌ {a4['rejected']} rejected")
        if a4.get("on_hold"):
            lines.append(f"⏸️ {a4['on_hold']} put on hold")
        if a6.get("sent"):
            lines.append(f"📧 {a6['sent']} email(s) sent")
        if errors:
            lines.append(f"⚠️ {len(errors)} agent(s) crashed: {'; '.join(e['error'][:80] for e in errors)}")
        try:
            post_chat_message(" · ".join(lines), subject="")
        except Exception:
            pass
