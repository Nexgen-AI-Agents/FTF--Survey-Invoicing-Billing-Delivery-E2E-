"""daily_report.py — twice-daily report to the 'AI Invoicing Agent' Teams group chat.

Runs 2×/day (12:00 PM and 7:00 PM ET, every day) so the team can MONITOR how the
invoicing agent is working and what it has done. Pulls LIVE state from the Approvals
sheet + the pipeline state store + the AI's learning store, then:
  • builds a DETERMINISTIC activity/audit block — what orders were processed since the
    last report and by whom (AI agents A1–A7 for automated steps; the on-record sheet
    approver for human approve/reject/hold), plus a current pipeline snapshot; and
  • asks Claude to WRITE the narrative (what to act on today + what it has learned).
Posts the result to the group chat via a Power Automate HTTP flow. Never raises fatally.

Which run is which is derived from the current Eastern hour (12 → Midday, else Evening);
the window each report covers is "since the previous report" (Midday ≈ 17h back to the
prior 7 PM; Evening ≈ 7h back to noon). Override with --label / --window-hours for testing.

Usage:
    python daily_report.py                                   # build + post (auto label/window)
    python daily_report.py --dry-run                         # build + print only (no post)
    python daily_report.py --dry-run --label "Evening (7 PM ET)" --window-hours 7
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

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

# Full pipeline funnel (status -> friendly label), used for the current-state snapshot.
_FUNNEL = [
    ("invoice_needed",                "Queued (needs data)"),
    ("data_collected",                "Data collected (awaiting pricing)"),
    ("pricing_needed",                "Needs manual price"),
    ("invoice_draft_posted",          "Draft posted (awaiting approval)"),
    ("invoice_modification_requested", "Change requested"),
    ("on_hold",                       "On hold"),
    ("invoice_approved",              "Approved (creating invoice)"),
    ("invoice_finalized",             "Invoice created (awaiting send)"),
    ("invoice_sending",               "Send attempted (unconfirmed)"),
    ("invoice_sent",                  "Invoice sent"),
    ("invoice_rejected",              "Rejected"),
    ("condo_rejected",                "Condo — rejected"),
    ("delivered_flagged",             "Delivered — flagged"),
    ("canceled_flagged",              "Canceled — flagged"),
    ("details_missing",               "Details missing"),
    ("already_invoiced",              "Already invoiced (skipped)"),
    ("permanently_excluded",          "Permanently excluded"),
]

# Recent-activity buckets: current status -> label (what changed since the last report).
_ACTIVITY_BUCKETS = [
    ("invoice_needed",       "new orders ingested (A1)"),
    ("data_collected",       "data collected (A2)"),
    ("invoice_draft_posted", "priced & posted for approval (A3)"),
    ("pricing_needed",       "flagged for manual pricing (A3)"),
    ("invoice_approved",     "approved by a human"),
    ("invoice_finalized",    "invoices created in FTF (A5)"),
    ("invoice_sent",         "invoices sent to clients (A6)"),
    ("invoice_rejected",     "rejected by a human"),
    ("on_hold",              "put on hold by a human"),
    ("condo_rejected",       "auto-flagged: condo"),
    ("canceled_flagged",     "auto-flagged: canceled in FTF"),
    ("delivered_flagged",    "auto-flagged: already delivered"),
    ("details_missing",      "stalled: details missing"),
]
# Statuses that represent a HUMAN decision (for the "by whom" rollup).
_HUMAN_STATUSES = {"invoice_approved", "invoice_finalized", "invoice_sent",
                   "invoice_rejected", "on_hold"}


def _parse_dt(s):
    """Best-effort parse of an ISO timestamp -> aware UTC datetime, or None."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _amt(o) -> float:
    try:
        return round(float(o.get("estimate_amount") or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _report_context(argv) -> dict:
    """Derive the run label + look-back window. ET hour 12 => Midday, else Evening."""
    label, window = None, None
    for i, a in enumerate(argv):
        if a == "--label" and i + 1 < len(argv):
            label = argv[i + 1]
        elif a == "--window-hours" and i + 1 < len(argv):
            try:
                window = float(argv[i + 1])
            except ValueError:
                pass
    now_et = datetime.now(oc._EASTERN)
    if label is None:
        label = "Midday (12 PM ET)" if now_et.hour == 12 else "Evening / EOD (7 PM ET)"
    if window is None:
        # Midday covers the previous evening report onward (~17h); Evening covers noon (~7h).
        window = 17.0 if now_et.hour == 12 else 7.0
    return {"label": label, "window_hours": window,
            "now_et_str": now_et.strftime("%a %b %-d, %-I:%M %p %Z") if os.name != "nt"
            else now_et.strftime("%a %b %d, %I:%M %p %Z")}


def _gather_activity(window_hours: float) -> dict:
    """What the agent processed in the last `window_hours`, and by whom, + a full snapshot."""
    try:
        from core.excel_db import get_all_orders
        orders = get_all_orders()
    except Exception as exc:  # noqa: BLE001
        log.warning("daily_report: activity gather failed (%s)", exc)
        orders = []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    ts_fields = ("sent_at", "invoice_created_at", "draft_posted_at",
                 "data_collected_at", "updated_at")

    def last_activity(o):
        best = None
        for f in ts_fields:
            dt = _parse_dt(o.get(f))
            if dt and (best is None or dt > best):
                best = dt
        return best

    # Current-state snapshot (all orders, by status).
    snapshot = {}
    for o in orders:
        st = str(o.get("status") or "").strip() or "(none)"
        snapshot[st] = snapshot.get(st, 0) + 1

    # Orders whose latest activity falls within the window.
    recent = [o for o in orders if (la := last_activity(o)) and la >= cutoff]

    def ex(o):
        return {"order": str(o.get("order_id") or "").strip(),
                "client": str(o.get("client_name") or "").strip(),
                "amount": _amt(o),
                "invoice_id": str(o.get("invoice_id") or "").strip(),
                "by": str(o.get("approved_by") or "").strip()}

    activity_counts, activity_examples = {}, {}
    for status, _label in _ACTIVITY_BUCKETS:
        rows = [o for o in recent if str(o.get("status") or "") == status]
        if rows:
            activity_counts[status] = len(rows)
            activity_examples[status] = [ex(o) for o in rows[:5]]

    # "By whom" — human decisions grouped by the on-record approver.
    by_whom = {}
    for o in recent:
        if str(o.get("status") or "") in _HUMAN_STATUSES:
            who = str(o.get("approved_by") or "").strip() or "operator (sheet, unattributed)"
            by_whom[who] = by_whom.get(who, 0) + 1

    return {
        "window_hours": window_hours,
        "recent_total": len(recent),
        "activity_counts": activity_counts,      # {status: n}
        "activity_examples": activity_examples,  # {status: [ex,...]}
        "by_whom": by_whom,                       # {approver: n}
        "snapshot": snapshot,                     # {status: n} across ALL orders
        "orders_total": len(orders),
    }


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


def _gather_ftf_metrics() -> dict:
    """Business-level counts straight from FTF (active-not-invoiced + open quotes)."""
    try:
        from core.ftf_mysql import get_business_metrics
        return get_business_metrics()
    except Exception as exc:  # noqa: BLE001
        log.warning("daily_report: ftf business metrics failed (%s)", exc)
        return {}


def _build_metrics_html(m: dict) -> str:
    """Deterministic 'Business snapshot' block — the headline counts the team asked for."""
    if not m:
        return ""
    ani, ani_r = m.get("active_not_invoiced"), m.get("active_not_invoiced_recent30")
    oq, oq_r = m.get("open_quotes"), m.get("open_quotes_recent30")
    items = []
    if ani is not None:
        recent = f" <i>({ani_r} in the last 30 days)</i>" if ani_r is not None else ""
        items.append(f"<li>&#128193; <b>{ani}</b> active order(s) <b>not yet invoiced</b>{recent} "
                     f"&mdash; open files flagged as needing an invoice.</li>")
    if oq is not None:
        recent = f" <i>({oq_r} in the last 30 days)</i>" if oq_r is not None else ""
        items.append(f"<li>&#128221; <b>{oq}</b> open <b>quote(s) not yet delivered</b>{recent} "
                     f"&mdash; status is <i>Quote</i>, waiting on admin.</li>")
    if not items:
        return ""
    return "<p><b>&#128200; Business snapshot (from FTF)</b></p><ul>" + "".join(items) + "</ul>"


def _build_questions_html(state: dict, metrics: dict) -> str:
    """A short list of questions for the team to answer next work day — helps train the AI.

    Data-driven where possible (real pending items) + a standing learning prompt + a
    scope-clarifier for the new EOD metrics (per Ryan: 'ask questions … to keep training it')."""
    qs = []
    mp = state.get("need_manual_price_count", 0)
    if mp:
        egs = ", ".join("#" + x["order"] for x in state.get("need_manual_price", [])[:3] if x.get("order"))
        qs.append(f"<b>{mp}</b> order(s) need a manual price{(' (e.g. ' + egs + ')') if egs else ''} "
                  f"&mdash; what should we bill?")
    esc = state.get("escalated_for_review_count", 0)
    if esc:
        egs = ", ".join("#" + x["order"] for x in state.get("escalated_for_review", [])[:3] if x.get("order"))
        qs.append(f"<b>{esc}</b> order(s) are escalated{(' (e.g. ' + egs + ')') if egs else ''} "
                  f"&mdash; approve, adjust, or reject?")
    qs.append("Any prices you corrected today I should learn? Add a note in the "
              "<b>'Learning provided by user'</b> column and I'll apply it to similar orders.")
    oq = metrics.get("open_quotes")
    if oq:
        qs.append(f"For these EOD numbers: should <b>'open quotes waiting on admin'</b> be all "
                  f"{oq} open quotes, or only recent ones (e.g. last 30 days)? Confirm the scope you want.")
    lis = "".join(f"<li>{q}</li>" for q in qs[:4])
    return ("<p><b>&#10067; Questions for the team</b> "
            "<i>(please reply in the chat next work day &mdash; it helps train me)</i></p>"
            f"<ul>{lis}</ul>")


def _build_activity_html(activity: dict, label: str) -> str:
    """DETERMINISTIC audit block — exact counts + who. Never LLM-written (no hallucinated numbers)."""
    wh = activity.get("window_hours", 0)
    bucket_label = dict(_ACTIVITY_BUCKETS)
    lines = [f"<p><b>&#128202; What the agent did &mdash; {label}</b> "
             f"<i>(last {int(round(wh))}h)</i></p>"]

    counts = activity.get("activity_counts", {})
    examples = activity.get("activity_examples", {})
    if not counts:
        lines.append("<p>No order activity in this window — the pipeline was idle or "
                     "everything was already processed.</p>")
    else:
        items = []
        for status, blabel in _ACTIVITY_BUCKETS:
            n = counts.get(status)
            if not n:
                continue
            ex = examples.get(status, [])
            samples = ", ".join(
                ("#" + e["order"] + (f" ({e['client']})" if e['client'] else ""))
                for e in ex[:3] if e["order"]
            )
            more = f" +{n - 3} more" if n > 3 else ""
            items.append(f"<li><b>{n}</b> {blabel}{(' — ' + samples + more) if samples else ''}</li>")
        lines.append("<ul>" + "".join(items) + "</ul>")

    # By whom
    by = activity.get("by_whom", {})
    if by:
        who_str = "; ".join(f"{k}: <b>{v}</b>" for k, v in sorted(by.items(), key=lambda x: -x[1]))
        lines.append(f"<p><b>By whom (human decisions):</b> {who_str}. "
                     f"All automated steps (ingest, data collection, pricing, invoice creation, "
                     f"send) were performed by the AI agents A1&ndash;A7.</p>")
    else:
        lines.append("<p><b>By whom:</b> no human decisions in this window — all activity was "
                     "automated by the AI agents A1&ndash;A7.</p>")

    # Current snapshot
    snap = activity.get("snapshot", {})
    snap_items = []
    label_map = dict(_FUNNEL)
    ordered = [s for s, _ in _FUNNEL if snap.get(s)] + \
              [s for s in snap if s not in label_map and snap.get(s)]
    for s in ordered:
        snap_items.append(f"<li>{label_map.get(s, s)}: <b>{snap[s]}</b></li>")
    if snap_items:
        lines.append(f"<p><b>Current pipeline ({activity.get('orders_total', 0)} orders tracked):</b></p>"
                     "<ul>" + "".join(snap_items) + "</ul>")
    return "".join(lines)


def _build_body_html(state: dict, learn: dict, backlog: dict, activity: dict,
                     metrics: dict | None = None) -> str:
    """Claude writes the narrative from the live data. Falls back to a plain summary on error."""
    payload = json.dumps(
        {"sheet_state": state, "pipeline_backlog": backlog, "ai_learnings": learn,
         "business_metrics": metrics or {},
         "activity_summary": {"counts": activity.get("activity_counts", {}),
                              "by_whom": activity.get("by_whom", {}),
                              "window_hours": activity.get("window_hours")}},
        indent=2, default=str,
    )
    system = (
        "You are the AI Invoicing Agent for NexGen Surveying. Write a SHORT, CLEAR status update "
        "for the survey team about the invoice pipeline (a midday or end-of-day report). Plain, "
        "friendly, skimmable, action-first. Output CLEAN minimal HTML only (use <p>, <b>, <ul>, "
        "<li>; NO <html>/<head>, NO markdown, NO code fences). Exactly two sections, each led by a "
        "bold header: "
        "(1) 'What to do today' — tell them exactly what to act on, with the counts and a few "
        "example order numbers; if nothing is pending, say so plainly and reassuringly. "
        "If pipeline_backlog.needs_send_confirmation_count > 0, call it out FIRST and clearly: "
        "those invoices were sent-attempted but delivery is UNCONFIRMED — a human must verify in "
        "FTF and will not be auto-resent. "
        "(2) 'What I learned' — state, in your own words, YOUR takeaways from the learned prices "
        "and operator notes; if there is little yet, say you are still learning. "
        "The *_count fields are the true totals; the matching lists hold only a few example orders. "
        "business_metrics (active-not-invoiced, open quotes) and activity_summary are ALREADY shown "
        "above your text — do NOT repeat their numbers; you may reference them in one short phrase. "
        "Do NOT write your own questions section (one is added separately). "
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


def build_message(context: dict | None = None) -> str:
    context = context or _report_context([])
    activity = _gather_activity(context["window_hours"])
    state = _gather_state()
    backlog = _gather_stuck_sends()
    learn = _gather_learnings()
    metrics = _gather_ftf_metrics()
    metrics_html = _build_metrics_html(metrics)
    activity_html = _build_activity_html(activity, context["label"])
    body = _build_body_html(state, learn, backlog, activity, metrics)
    questions_html = _build_questions_html(state, metrics)
    header = (f"<p><b>&#129302; AI Invoicing Agent &mdash; {context['label']} Report</b><br>"
              f"<i>{context['now_et_str']}</i></p>")
    link = (f"<p>&#128203; <b>Approvals sheet:</b> "
            f"<a href=\"{ONEDRIVE_SHARE_URL}\">open FTF-Invoicing Agent.xlsx</a> "
            f"&mdash; edit the <b>blue</b> columns only; the <b>gray</b> ones are mine.</p>")
    # Order: headline business numbers -> what I did -> what to do / learned -> questions.
    return header + link + metrics_html + activity_html + body + questions_html


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
    context = _report_context(argv)
    html = build_message(context)
    if "--dry-run" in argv:
        print(html)
        return
    code = post(html)
    print(f"POSTED status={code}")


if __name__ == "__main__":
    main()
