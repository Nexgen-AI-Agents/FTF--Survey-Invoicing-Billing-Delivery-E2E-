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

    # Delivery health: of the invoices SENT in this window, how many carry a Pay Now payment
    # link (A6 records the FTF pay link on each send), plus the dollar value delivered.
    sent_rows      = [o for o in recent if str(o.get("status") or "") == "invoice_sent"]
    sent_count     = len(sent_rows)
    sent_with_link = sum(1 for o in sent_rows if str(o.get("pay_link") or "").startswith("http"))
    sent_amount    = round(sum(_amt(o) for o in sent_rows), 2)

    return {
        "window_hours": window_hours,
        "recent_total": len(recent),
        "activity_counts": activity_counts,      # {status: n}
        "activity_examples": activity_examples,  # {status: [ex,...]}
        "by_whom": by_whom,                       # {approver: n}
        "snapshot": snapshot,                     # {status: n} across ALL orders
        "orders_total": len(orders),
        "sent_count": sent_count,
        "sent_with_link": sent_with_link,
        "sent_amount": sent_amount,
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


# ── Clean report helpers ──────────────────────────────────────────────────────
# Simple, kid-friendly labels + emojis for the tables. Emojis as HTML entities so the
# text survives any encoding on the way to Teams.
_ACTIVITY_SIMPLE = {
    "invoice_needed":       "&#127381; Found new orders",
    "data_collected":       "&#128270; Collected details",
    "invoice_draft_posted": "&#128181; Priced &amp; sent for your OK",
    "pricing_needed":        "&#9995; Needs a price from you",
    "invoice_approved":      "&#128077; Approved",
    "invoice_finalized":     "&#129534; Invoice made",
    "invoice_sent":          "&#128231; Invoice emailed",
    "invoice_rejected":      "&#10060; Rejected",
    "on_hold":               "&#9208; On hold",
    "condo_rejected":        "&#127970; Skipped: condo",
    "canceled_flagged":      "&#128683; Skipped: canceled",
    "delivered_flagged":     "&#128230; Skipped: already delivered",
    "details_missing":       "&#10067; Missing details",
}
_SNAPSHOT_SIMPLE = {
    "invoice_needed":                 "Waiting for details",
    "data_collected":                 "Ready to price",
    "pricing_needed":                 "Needs a price",
    "invoice_draft_posted":           "Waiting for your OK",
    "invoice_modification_requested": "Change asked for",
    "on_hold":                        "On hold",
    "invoice_approved":               "Making the invoice",
    "invoice_finalized":              "Ready to email",
    "invoice_sending":                "Send unsure",
    "invoice_sent":                   "Emailed &#9989;",
    "invoice_rejected":               "Rejected",
    "condo_rejected":                 "Condo (skipped)",
    "delivered_flagged":              "Already delivered",
    "canceled_flagged":               "Canceled",
    "details_missing":                "Missing details",
    "already_invoiced":               "Already billed",
    "permanently_excluded":           "Left out on purpose",
}


def _table(headers: list, rows: list) -> str:
    """Minimal HTML table (no CSS — Teams strips inline styles, keeps structure)."""
    head = "".join(f'<th align="left">{h}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table border="1" cellpadding="6" cellspacing="0"><tr>{head}</tr>{body}</table>'


def _build_metrics_html(m: dict) -> str:
    """Big Picture table — the whole-business headline counts."""
    if not m:
        return ""
    ani, ani_r = m.get("active_not_invoiced"), m.get("active_not_invoiced_recent30")
    oq, oq_r = m.get("open_quotes"), m.get("open_quotes_recent30")
    rows = []
    if ani is not None:
        note = f" <i>({ani_r} new in 30 days)</i>" if ani_r is not None else ""
        rows.append([f"&#128193; Orders not billed yet{note}", f"<b>{ani}</b>"])
    if oq is not None:
        note = f" <i>({oq_r} new in 30 days)</i>" if oq_r is not None else ""
        rows.append([f"&#128221; Quotes waiting to be sent{note}", f"<b>{oq}</b>"])
    if not rows:
        return ""
    return ("<p>&#128200; <b>Big Picture</b> <i>(whole business)</i></p>"
            + _table(["What", "How many"], rows))


def _build_questions_html(state: dict, metrics: dict) -> str:
    """A short list of questions for the team to answer next work day — helps train the AI.

    Data-driven where possible (real pending items) + a standing learning prompt + a
    scope-clarifier for the new EOD metrics (per Ryan: 'ask questions … to keep training it')."""
    qs = []
    mp = state.get("need_manual_price_count", 0)
    if mp:
        egs = ", ".join("#" + x["order"] for x in state.get("need_manual_price", [])[:3] if x.get("order"))
        qs.append(f"What price for the <b>{mp}</b> order(s) that need one?{(' e.g. ' + egs) if egs else ''}")
    esc = state.get("escalated_for_review_count", 0)
    if esc:
        egs = ", ".join("#" + x["order"] for x in state.get("escalated_for_review", [])[:3] if x.get("order"))
        qs.append(f"Approve, change, or reject the <b>{esc}</b> flagged order(s)?{(' e.g. ' + egs) if egs else ''}")
    qs.append("Fixed a price today? Write it in the <b>'Learning provided by user'</b> column so I can learn.")
    oq = metrics.get("open_quotes")
    if oq:
        qs.append(f"Should <b>'quotes waiting'</b> mean all {oq}, or only the last 30 days?")
    lis = "".join(f"<li>{q}</li>" for q in qs[:4])
    return ("<p>&#10067; <b>Questions for you</b> "
            "<i>(please reply in the chat)</i></p>"
            f"<ul>{lis}</ul>")


def _build_activity_html(activity: dict, label: str) -> str:
    """DETERMINISTIC 'What I did' table + delivery line + who (no hallucinated numbers)."""
    wh = int(round(activity.get("window_hours", 0)))
    lines = [f"<p>&#9989; <b>What I did</b> <i>(last {wh} hours)</i></p>"]

    counts = activity.get("activity_counts", {})
    examples = activity.get("activity_examples", {})
    if not counts:
        lines.append("<p>&#128564; Nothing happened in this time.</p>")
    else:
        rows = []
        for status, _blabel in _ACTIVITY_BUCKETS:
            n = counts.get(status)
            if not n:
                continue
            ex = examples.get(status, [])
            samples = ", ".join("#" + e["order"] for e in ex[:2] if e["order"])
            more = f" +{n - 2} more" if n > 2 else ""
            eg = (samples + more) if samples else "&mdash;"
            rows.append([_ACTIVITY_SIMPLE.get(status, status), f"<b>{n}</b>", eg])
        lines.append(_table(["What", "Count", "Examples"], rows))

    # Delivery health — invoices sent this window + Pay Now link coverage + $ delivered.
    sc = activity.get("sent_count", 0)
    if sc:
        swl = activity.get("sent_with_link", 0)
        amt = activity.get("sent_amount", 0.0)
        if swl == sc:
            cover = "all had a <b>Pay Now</b> button &#9989;"
        elif swl == 0:
            cover = "&#9888; <b>none</b> had a Pay Now button"
        else:
            cover = f"<b>{swl} of {sc}</b> had a Pay Now button"
        lines.append(f"<p>&#128179; <b>Invoices emailed:</b> {sc} &mdash; {cover} "
                     f"&middot; total <b>${amt:,.2f}</b></p>")

    # Who approved (human decisions) — simple line.
    by = activity.get("by_whom", {})
    if by:
        who = ", ".join(f"{k} (<b>{v}</b>)" for k, v in sorted(by.items(), key=lambda x: -x[1]))
        lines.append(f"<p>&#128100; <b>Who approved:</b> {who}. <i>I did the automatic steps.</i></p>")
    return "".join(lines)


def _build_snapshot_html(activity: dict) -> str:
    """'Where all orders are now' table — the full pipeline at a glance."""
    snap = activity.get("snapshot", {})
    if not snap:
        return ""
    label_map = dict(_FUNNEL)
    ordered = [s for s, _ in _FUNNEL if snap.get(s)] + \
              [s for s in snap if s not in label_map and snap.get(s)]
    rows = [[_SNAPSHOT_SIMPLE.get(s, label_map.get(s, s)), f"<b>{snap[s]}</b>"] for s in ordered]
    return (f"<p>&#128449; <b>Where all orders are now</b> "
            f"<i>({activity.get('orders_total', 0)} total)</i></p>"
            + _table(["Stage", "Count"], rows))


def _build_todo_html(state: dict, backlog: dict) -> str:
    """DETERMINISTIC 'Please help with' table — exactly what a human needs to do."""
    lines = ["<p>&#128587; <b>Please help with</b></p>"]
    confirm_n = backlog.get("needs_send_confirmation_count", 0)
    if confirm_n:
        lines.append(f"<p>&#9888; <b>{confirm_n} invoice(s) need a check</b> &mdash; we tried to send "
                     f"but are not sure it worked. Please check in FTF.</p>")

    def egs(key):
        s = ", ".join("#" + x["order"] for x in state.get(key, [])[:3] if x.get("order"))
        return s or "&mdash;"

    rows = []
    if state.get("ready_to_approve_count"):
        rows.append(["&#128077; Approve ready invoices",
                     f"<b>{state['ready_to_approve_count']}</b>", egs("ready_to_approve")])
    if state.get("need_manual_price_count"):
        rows.append(["&#9995; Set a price",
                     f"<b>{state['need_manual_price_count']}</b>", egs("need_manual_price")])
    if state.get("escalated_for_review_count"):
        rows.append(["&#128269; Check flagged orders",
                     f"<b>{state['escalated_for_review_count']}</b>", egs("escalated_for_review")])
    if rows:
        lines.append(_table(["Task", "How many", "Examples"], rows))
    elif not confirm_n:
        lines.append("<p>&#127881; <b>All caught up &mdash; nothing needs you right now.</b></p>")
    return "".join(lines)


def _build_learned_html(learn: dict) -> str:
    """Short 'What I learned' bullets — kid-simple. LLM-written, safe plain fallback."""
    prices = learn.get("learned_prices", [])
    payload = json.dumps({"learned_prices": prices,
                          "operator_notes_recent": learn.get("operator_notes_recent", [])}, default=str)
    system = (
        "You are the AI Invoicing Agent. From the data, write what you have learned as 2-3 VERY "
        "SHORT bullets a 5th grader can understand. Simple words. Each bullet 12 words or fewer. "
        "Output ONLY <li>...</li> items (NO <ul>, no other tags, no markdown, no code fences). "
        "Use only the data given; do not invent numbers. If there is little to report, output one "
        "<li> saying you are still learning."
    )
    inner = ""
    try:
        out = llm_call(model=HUMAN_GATE_MODEL, system=system, user=payload, max_tokens=200).strip()
        out = re.sub(r"^```[a-z]*\n?", "", out).rstrip("`").strip()
        inner = "".join(re.findall(r"<li>.*?</li>", out, re.S))
    except Exception as exc:
        log.warning("daily_report: learned bullets LLM failed (%s) — plain fallback", exc)
    if not inner:
        n = len(prices)
        inner = (f"<li>I now know {n} price pattern(s) well.</li>" if n
                 else "<li>Still learning &mdash; not enough data yet.</li>")
    return "<p>&#128161; <b>What I learned</b></p><ul>" + inner + "</ul>"


def build_message(context: dict | None = None) -> str:
    context = context or _report_context([])
    activity = _gather_activity(context["window_hours"])
    state = _gather_state()
    backlog = _gather_stuck_sends()
    learn = _gather_learnings()
    metrics = _gather_ftf_metrics()
    header = (f"<p>&#129302; <b>AI Invoicing Agent</b> &mdash; <b>{context['label']}</b><br>"
              f"&#128197; <i>{context['now_et_str']}</i></p>")
    link = (f"<p>&#128203; <b>Approvals sheet:</b> "
            f"<a href=\"{ONEDRIVE_SHARE_URL}\">open the sheet</a> "
            f"&mdash; <i>please edit the blue columns only.</i></p>")
    # Order: title -> sheet link -> big picture -> what I did -> where orders are ->
    # what to do -> what I learned -> questions.
    return (header + link
            + _build_metrics_html(metrics)
            + _build_activity_html(activity, context["label"])
            + _build_snapshot_html(activity)
            + _build_todo_html(state, backlog)
            + _build_learned_html(learn)
            + _build_questions_html(state, metrics))


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
