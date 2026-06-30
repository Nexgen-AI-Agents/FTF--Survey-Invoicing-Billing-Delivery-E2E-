"""daily_report.py — morning report to the 'AI Invoicing Agent' Teams group chat.

Pulls LIVE state from the Approvals sheet + the AI's learning store, then asks Claude to
WRITE the report itself (no hardcoded copy — the AI states, in its own words, what the team
should do today and what it has learned). Posts the result to the group chat via Graph
(Chat.ReadWrite.All). Run by cron at 06:00 ET. Never raises fatally.

Usage:
    python daily_report.py            # build + post to the chat
    python daily_report.py --dry-run  # build + print only (no post)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import httpx  # noqa: E402
from config.models import HUMAN_GATE_MODEL  # noqa: E402
from config.settings import ONEDRIVE_SHARE_URL  # noqa: E402
from core import onedrive_excel_client as oc  # noqa: E402
from core.claude_client import call as llm_call  # noqa: E402
from core.logger import get_logger  # noqa: E402

log = get_logger("daily_report")

# Delivery is via a Power Automate "When an HTTP request is received" flow (app-only Graph
# cannot post chat messages — it 403s with "requires Teamwork.Migrate.All"). The server POSTs
# {"message": "<html>"} to TEAMS_FLOW_URL; the flow posts it into the 'AI - Invoicing Agent'
# chat. Set TEAMS_FLOW_URL in .env to the flow's HTTP trigger URL.
_RULES_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "learned_rules.json")
)


def _gather_state() -> dict:
    """Read the live Approvals table and bucket the rows the approver still has to act on."""
    base = oc._wb_base()
    resp = oc._graph_get_retry(
        f"{base}/worksheets/{oc.ONEDRIVE_SHEET_NAME}/tables/{oc.ONEDRIVE_TABLE_NAME}/rows",
        headers=oc._headers(), timeout=20.0,
    )
    rows = resp.json().get("value", []) if (resp is not None and resp.is_success) else []
    ready, manual, escalated = [], [], []
    sent_total = 0
    for r in rows:
        v = r.get("values", [[]])[0]
        if len(v) < oc._COL_COUNT:
            v = list(v) + [""] * (oc._COL_COUNT - len(v))
        oid    = str(v[oc._COL_ORDER_ID]).strip()
        client = str(v[oc._COL_CLIENT]).strip()
        notes  = str(v[oc._COL_NOTES]).strip()
        proc   = str(v[oc._COL_PROCESSED_AT]).strip()
        action = str(v[oc._COL_ACTION]).strip()
        esc    = str(v[oc._COL_ESCALATE]).strip().lower() == "yes"
        try:
            amt = float(v[oc._COL_AMOUNT_AI] or 0)
        except (TypeError, ValueError):
            amt = 0.0
        if proc:
            sent_total += 1
            continue
        if action:
            continue  # already decided, just awaiting the pipeline to process it
        if "MANUAL PRICING" in notes.upper() or amt <= 0:
            manual.append({"order": oid, "client": client})
        elif esc:
            escalated.append({"order": oid, "client": client, "why": notes[:140]})
        else:
            ready.append({"order": oid, "client": client, "amount": round(amt, 2)})
    return {
        "awaiting_total": len(ready) + len(manual) + len(escalated),
        "ready_to_approve_count": len(ready),
        "need_manual_price_count": len(manual),
        "escalated_for_review_count": len(escalated),
        "ready_to_approve": ready[:6],          # examples only; *_count holds the true totals
        "need_manual_price": manual[:6],
        "escalated_for_review": escalated[:6],
        "already_processed_total": sent_total,
        "total_rows_on_sheet": len(rows),
    }


def _gather_stuck_sends() -> dict:
    """Orders the pipeline cannot complete on its own — read from the state store.

    'needs_send_confirmation' = a delivery was ATTEMPTED but its outcome is unknown
    (status invoice_sending): the AI will NOT auto-resend it (to avoid a duplicate
    email); a human must confirm in FTF and run scripts/resolve_stuck_send.py.
    The waiting_* counts are orders A5/A6 are still retrying (FTF likely down)."""
    try:
        from core.excel_db import get_orders_by_status
        sending   = get_orders_by_status("invoice_sending")
        approved  = get_orders_by_status("invoice_approved")
        finalized = get_orders_by_status("invoice_finalized")
    except Exception as exc:
        log.warning("daily_report: stuck-send gather failed (%s)", exc)
        return {}
    ids = lambda rows: [str(r.get("order_id")) for r in rows][:6]
    return {
        "needs_send_confirmation_count": len(sending),
        "needs_send_confirmation": ids(sending),
        "waiting_to_create_count": len(approved),   # A5 not yet created (retrying)
        "waiting_to_send_count": len(finalized),     # A6 not yet sent (retrying)
    }


def _gather_learnings() -> dict:
    """Pull the AI's actual learning signals so it can summarise them itself (no hardcoding)."""
    try:
        with open(_RULES_FILE, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    learned = []
    for b in d.get("observations", {}).values():
        try:
            price = float(b.get("learned_price", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0
        if b.get("status") == "active" and price > 0:
            scored = [s for s in b.get("samples", []) if s.get("scored")]
            learned.append({"service": b.get("service"), "county": b.get("county"),
                            "tier": b.get("tier"), "learned_price": round(price),
                            "from_orders": len(scored)})
    operator_notes = [g.get("note") for g in d.get("user_guidance", [])[-6:] if isinstance(g, dict)]
    return {"learned_prices": learned[:8], "operator_notes_recent": operator_notes}


def _build_body_html(state: dict, learn: dict, backlog: dict) -> str:
    """Claude writes the report from the live data. Falls back to a plain summary on error."""
    payload = json.dumps(
        {"sheet_state": state, "pipeline_backlog": backlog, "ai_learnings": learn},
        indent=2, default=str,
    )
    system = (
        "You are the AI Invoicing Agent for NexGen Surveying. Write a SHORT morning report for "
        "the survey team about the invoice Approvals sheet. Be precise and action-first. Output "
        "CLEAN minimal HTML only (use <p>, <b>, <ul>, <li>; NO <html>/<head>, NO markdown, NO code "
        "fences). Exactly two sections, each led by a bold header: "
        "(1) 'What to do today' — tell them exactly what to act on, with the counts and a few "
        "example order numbers; if nothing is pending, say so plainly and reassuringly. "
        "If pipeline_backlog.needs_send_confirmation_count > 0, call it out FIRST and clearly: "
        "those invoices were sent-attempted but delivery is UNCONFIRMED — a human must verify in "
        "FTF and will not be auto-resent. "
        "(2) 'What I learned' — state, in your own words, YOUR takeaways from the learned prices "
        "and operator notes; if there is little yet, say you are still learning. "
        "The *_count fields are the true totals; the matching lists hold only a few example orders. "
        "Under 150 words total. Never invent numbers — use only the data provided."
    )
    try:
        html = llm_call(model=HUMAN_GATE_MODEL, system=system, user=payload, max_tokens=500).strip()
        if html.startswith("```"):
            html = re.sub(r"^```[a-z]*\n?", "", html).rstrip("`").strip()
        if html:
            return html
    except Exception as exc:
        log.warning("daily_report: LLM write failed (%s) — using plain fallback", exc)
    confirm_n = backlog.get("needs_send_confirmation_count", 0)
    confirm_html = (
        f"<p>&#9888; <b>{confirm_n} invoice(s) need send confirmation</b> — delivery was attempted "
        f"but unconfirmed; verify in FTF (they will NOT be auto-resent).</p>" if confirm_n else ""
    )
    return (
        "<p><b>What to do today</b></p>"
        + confirm_html +
        f"<p>{state['awaiting_total']} order(s) awaiting your review — "
        f"{state['ready_to_approve_count']} ready to approve, "
        f"{state['need_manual_price_count']} need a price, "
        f"{state['escalated_for_review_count']} escalated for review.</p>"
        "<p><b>What I learned</b></p>"
        f"<p>{len(learn['learned_prices'])} learned price pattern(s) active so far.</p>"
    )


def build_message() -> str:
    state = _gather_state()
    backlog = _gather_stuck_sends()
    learn = _gather_learnings()
    body = _build_body_html(state, learn, backlog)
    header = "<p><b>&#129302; AI Invoicing Agent &mdash; Daily Report</b></p>"
    link = (f"<p>&#128203; <b>Approvals sheet:</b> "
            f"<a href=\"{ONEDRIVE_SHARE_URL}\">open FTF-Invoicing Agent.xlsx</a> "
            f"&mdash; edit the <b>blue</b> columns only; the <b>gray</b> ones are mine.</p>")
    return header + link + body


def post(html: str) -> int:
    """Deliver the report to the Teams chat via a Power Automate HTTP-trigger flow.
    The flow receives {"message": "<html>"} and posts it into the chat."""
    url = os.getenv("TEAMS_FLOW_URL", "").strip()
    if not url:
        log.warning("daily_report: TEAMS_FLOW_URL not set — report built but NOT delivered. "
                    "Add the Power Automate HTTP-trigger URL to .env to enable Teams posting.")
        print("NOT_POSTED: TEAMS_FLOW_URL not configured")
        return 0
    r = httpx.post(url, json={"message": html}, timeout=30.0)
    log.info("daily_report -> Power Automate HTTP %s", r.status_code)
    if not r.is_success:
        log.error("daily_report flow post failed: %s", r.text[:300])
    return r.status_code


def main(argv=None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    html = build_message()
    if "--dry-run" in argv:
        print(html)
        return
    code = post(html)
    print(f"POSTED status={code}")


if __name__ == "__main__":
    main()
