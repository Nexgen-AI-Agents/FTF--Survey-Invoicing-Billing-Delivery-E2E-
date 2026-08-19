"""miro_build_estimator_board.py — build the 'FTF-AI invoicing estimator' Miro board.

TWO workflows, one board:
  • Left  — TECH WORKFLOW: 6 phase bands (DETECT -> COLLECT -> PRICE -> APPROVE ->
    DELIVER -> LEARN), the external systems each step talks to in a column on the far
    left, exceptions branching right, and reference panels (status machine, guardrails,
    schedule, failure handling, legend) on the far right. Status transitions ride on the
    ARROWS rather than inside the boxes, so the state machine reads at a glance.
  • Right — CLIENT WORKFLOW: the same story in plain words a 5th grader can follow.

Every tech box mirrors an agent docstring / crontab entry in this repo — the board is
generated from the code so it cannot quietly drift from reality.

Safe by design: touches ONLY Miro. No FTF, no Excel, no email, no client contact.

Usage:
    python scripts/miro_build_estimator_board.py                    # create a new board
    python scripts/miro_build_estimator_board.py --force            # ignore name clash
    python scripts/miro_build_estimator_board.py --dry-run          # plan only, no calls
    python scripts/miro_build_estimator_board.py --rebuild-tech ID  # redraw tech side only
    python scripts/miro_build_estimator_board.py --move-only ID     # put board in the Space
"""
import json
import os
import sys
import time

import requests
from dotenv import dotenv_values

API = "https://api.miro.com/v2"
BOARD_NAME = "FTF-AI invoicing estimator"
SPACE_NAME = "Land Solutions"       # Miro Space the board belongs in (a "project" in the API)
SPACE_ID   = "3458764680746478006"  # id of that Space; not listable without projects:read
BOARD_ID_HINT = "uXjVHwLvWsU="      # the board this script already built
BOARD_DESC = ("AI Invoicing Estimator - two views of one pipeline: TECH (left) and "
              "CLIENT / plain-English (right). Generated from the repo by "
              "scripts/miro_build_estimator_board.py")

_ENV = os.path.join(os.path.dirname(__file__), "..", ".env")
TOKEN = (dotenv_values(_ENV).get("MIRO_ACCESS_TOKEN") or os.getenv("MIRO_ACCESS_TOKEN") or "").strip()
H = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}

# ---------------------------------------------------------------- palette
BLUE   = "#2d9bf0"      # AI agent step
GREY   = "#7b92a8"      # scheduled job / IO
YELLOW = "#f5d128"      # decision
ORANGE = "#ff9d48"      # human-only step
RED    = "#f24726"      # stop / exception
PURPLE = "#9510ac"      # learn + report
GREEN  = "#8fd14f"      # client-facing step
SLATE  = "#414bb2"      # external system chip
PANEL  = "#ffffff"      # reference panel
DARK   = "#1a1a1a"
WHITE  = "#ffffff"


def _req(method: str, path: str, body: dict = None) -> dict:
    """One Miro call. Raises with the server's own message so failures are debuggable."""
    r = requests.request(method, API + path, headers=H,
                         data=json.dumps(body) if body else None, timeout=40)
    if r.status_code >= 300:
        raise RuntimeError("%s %s -> %s %s" % (method, path, r.status_code, r.text[:400]))
    time.sleep(0.12)                      # stay well inside Miro's rate limit
    return r.json() if r.text else {}


def _p(x, y):
    return {"x": x, "y": y, "origin": "center"}


class Board:
    def __init__(self, bid):
        self.bid = bid

    def frame(self, title, x, y, w, h, fill="#ffffff"):
        return _req("POST", "/boards/%s/frames" % self.bid, {
            "data": {"title": title, "format": "custom", "type": "freeform"},
            "style": {"fillColor": fill},
            "position": _p(x, y), "geometry": {"width": w, "height": h},
        })["id"]

    def shape(self, content, x, y, w, h, fill=BLUE, color=WHITE, size="13",
              shape="round_rectangle", align="center", valign="middle", border=None):
        return _req("POST", "/boards/%s/shapes" % self.bid, {
            "data": {"shape": shape, "content": content},
            "style": {"fillColor": fill, "color": color, "fontSize": size,
                      "textAlign": align, "textAlignVertical": valign,
                      "borderColor": border or fill,
                      "borderWidth": "2" if border else "1"},
            "position": _p(x, y), "geometry": {"width": w, "height": h},
        })["id"]

    def text(self, content, x, y, w, size="30", color=DARK, align="center"):
        return _req("POST", "/boards/%s/texts" % self.bid, {
            "data": {"content": content},
            "style": {"fontSize": size, "color": color, "textAlign": align},
            "position": _p(x, y), "geometry": {"width": w},
        })["id"]

    def sticky(self, content, x, y, w=260, fill="light_yellow"):
        return _req("POST", "/boards/%s/sticky_notes" % self.bid, {
            "data": {"content": content, "shape": "square"},
            "style": {"fillColor": fill, "textAlign": "center",
                      "textAlignVertical": "middle"},
            "position": _p(x, y), "geometry": {"width": w},
        })["id"]

    def link(self, a, b, label="", color=DARK, dashed=False, width="2"):
        body = {
            "startItem": {"id": a}, "endItem": {"id": b}, "shape": "elbowed",
            "style": {"strokeColor": color, "strokeWidth": width,
                      "strokeStyle": "dashed" if dashed else "normal",
                      "startStrokeCap": "none", "endStrokeCap": "arrow",
                      "fontSize": "11", "textOrientation": "horizontal"},
        }
        if label:
            body["captions"] = [{"content": label, "position": "50%"}]
        return _req("POST", "/boards/%s/connectors" % self.bid, body)["id"]

    def delete(self, item_id):
        _req("DELETE", "/boards/%s/items/%s" % (self.bid, item_id))


# ================================================================ TECH workflow
# Three columns: systems (far left) | flow (centre) | exceptions + reference (right)
T_FRAME_X, T_FRAME_Y, T_FRAME_W, T_FRAME_H = -1750, 250, 2900, 3900
COL_SYS, COL_FLOW, COL_EXC, COL_PANEL = -2900, -1900, -1330, -700
BOX_W, BOX_H, PITCH, PHASE_GAP = 660, 150, 190, 110

# (key, kind, html) — kind drives colour/shape so the visual language stays consistent
PHASES = [
    ("1 &middot; DETECT", "#e8eef6", [
        ("trigger", "io",
         "<p><b>&#9201; TRIGGER</b> &mdash; cron <b>*/5</b> on EC2 (prod)<br>"
         "<i>A0 orchestrator runs A1&rarr;A7 in sequence</i></p>"),
        ("a1", "agent",
         "<p><b>A1 &middot; Flag Hunter</b><br>MySQL scan <b>filter_by_flag=invoice_needed</b><br>"
         "<i>any FTF status &mdash; the $ symbol in Track Flow</i></p>"),
    ]),
    ("2 &middot; COLLECT", "#e8eef6", [
        ("a2", "agent",
         "<p><b>A2 &middot; Data Collector</b> &mdash; 4 sources in parallel<br>"
         "<i>order + client + service + property facts</i></p>"),
        ("gate", "decision",
         "<p><b>client_email<br>+ services<br>&ge; MEDIUM?</b></p>"),
    ]),
    ("3 &middot; PRICE", "#e6f0fa", [
        ("gates", "agent",
         "<p><b>A3 &middot; pre-flight gates</b> <i>(deterministic, before any AI)</i><br>"
         "condo &rarr; <b>reject</b> &bull; duplicate &rarr; <b>flag for human</b></p>"),
        ("tier", "agent",
         "<p><b>A3 &middot; client tier</b> <i>(deterministic)</i><br>"
         "individual / new_title / old_title<br>"
         "<i>from ng_company.company_type + volume</i></p>"),
        ("ai", "agent",
         "<p><b>A3 &middot; AI pricing</b> &mdash; <b>Opus 5</b> + extended thinking<br>"
         "reasons over rate, aerial, appraiser, FEMA, lot size, county<br>"
         "reads <b>[OPERATOR GUIDANCE]</b> + learned_rules.json<br>"
         "<i>constants are guidelines, NOT a lookup table</i></p>"),
        ("excel", "io",
         "<p><b>&#128203; Draft row &rarr; OneDrive Excel</b><br>"
         "FTF-Invoicing Agent.xlsx &mdash; <i>price, services, reasoning</i></p>"),
    ]),
    ("4 &middot; APPROVE &mdash; humans only", "#fdf0e4", [
        ("human", "human",
         "<p><b>&#128587; HUMAN GATE</b><br>a person sets Action: "
         "<b>Approve</b> / <b>Reject</b> / <b>Hold</b><br>"
         "<i>the AI never approves its own price</i></p>"),
        ("watcher", "io",
         "<p><b>&#128064; Excel Watcher</b> &mdash; cron <b>5,10&hellip;55</b> (flock)<br>"
         "&rarr; <b>A4</b> records the decision, stamps Processed At<br>"
         "<i>alt path: Power Automate &rarr; workflow_dispatch</i></p>"),
    ]),
    ("5 &middot; DELIVER", "#e6f0fa", [
        ("a5", "agent",
         "<p><b>A5 &middot; Invoice Finalizer</b><br><b>POST /invoices</b> &rarr; verify the $ flag "
         "cleared<br><i>3 retries, then logged for a human</i></p>"),
        ("a6", "agent",
         "<p><b>A6 &middot; Sender</b> &mdash; as <b>nesa</b> (real FTF audit trail)<br>"
         "/admin/login &rarr; /order/invoice &rarr; <b>scrape paynow token</b><br>"
         "&rarr; /order/deliver_invoice &mdash; email carries <b>Pay Now</b></p>"),
    ]),
    ("6 &middot; LEARN &amp; REPORT", "#f3e8f7", [
        ("a7", "learn",
         "<p><b>A7 &middot; Feedback Learner</b><br>approved prices &rarr; learned_rules.json<br>"
         "<i>2+ approvals within &plusmn;5% &rarr; promoted to active</i></p>"),
        ("report", "learn",
         "<p><b>&#128202; Daily Report</b> &mdash; 12:00 &amp; 19:00 ET<br>"
         "Teams via Power Automate<br><i>numbers, my thinking, numbered questions</i><br>"
         "hides pre-cutoff backlog &mdash; <b>count disclosed</b></p>"),
        ("watch2", "learn",
         "<p><b>&#128260; Teams Watcher</b> &mdash; cron <b>:07</b> &amp; <b>:37</b><br>"
         "reads the team's replies &rarr; writes <b>user_guidance</b><br>"
         "<i>asks, then commits: max <b>2</b> follow-ups per question</i></p>"),
    ]),
]

KIND = {"io": (GREY, WHITE, "round_rectangle"), "agent": (BLUE, WHITE, "round_rectangle"),
        "decision": (YELLOW, DARK, "rhombus"), "human": (ORANGE, DARK, "round_rectangle"),
        "learn": (PURPLE, WHITE, "round_rectangle")}

# main path: (from, to, arrow label) — statuses live on the arrows
EDGES = [
    ("trigger", "a1", ""), ("a1", "a2", "invoice_needed"), ("a2", "gate", ""),
    ("gate", "gates", "YES &middot; data_collected"), ("gates", "tier", ""),
    ("tier", "ai", ""), ("ai", "excel", ""), ("excel", "human", "invoice_draft_posted"),
    ("human", "watcher", "Action set in the sheet"),
    ("watcher", "a5", "invoice_approved"), ("a5", "a6", "invoice_finalized"),
    ("a6", "a7", "invoice_sent"), ("a7", "report", ""), ("report", "watch2", ""),
]

# exceptions: (anchor_step, html, arrow label)
EXCEPTIONS = [
    ("gate", "<p><b>&#9888; details_missing</b><br>Teams alert:<br>"
             "<i>client details not found</i><br>stops &mdash; a human looks</p>", "NO"),
    ("gates", "<p><b>&#9888; condo &rarr; rejected</b><br>"
              "<i>no land parcel to survey</i></p>", "gate hit"),
    ("watcher", "<p><b>&#9888; invoice_rejected<br>/ on_hold</b><br>"
                "<i>nothing is sent</i></p>", "reject / hold"),
    # Added after the 2026-08-19 outage: the row append is a real failure branch, not a
    # detail. If it is ever silent again, orders exist but no human can see them.
    ("excel", "<p><b>&#9888; row write fails</b><br>"
              "order stays <b>data_collected</b><br>&rarr; retried next run, never lost<br>"
              "<i>rows are padded to the table's real width;<br>"
              "a populated sheet is NEVER recreated</i></p>", "400 / locked"),
]

# feedback: (from, to, label) — dashed, this is the self-learning loop
FEEDBACK = [("a7", "ai", "learned prices"), ("watch2", "ai", "[OPERATOR GUIDANCE]")]

# external systems: (html, anchor_step, y_offset)
SYSTEMS = [
    ("<p><b>&#128451; FTF MySQL</b><br><i>ng_orders &middot; ng_company &middot; "
     "ng_email_delivered</i></p>", "a1", 0),
    ("<p><b>&#127760; FTF portal + API</b><br><i>/order/* &middot; /invoices</i></p>", "a2", -150),
    ("<p><b>&#128231; nesa@ inbox</b><br><i>order emails, 90 days</i></p>", "a2", -50),
    ("<p><b>&#127963; County appraiser</b><br><i>legal desc, lot size, parcel</i></p>", "a2", 50),
    ("<p><b>&#128752; Google aerial</b><br><i>satellite &rarr; Claude vision</i></p>", "a2", 150),
    ("<p><b>&#129302; Anthropic API</b><br><i>Opus 5, thinking on</i></p>", "ai", 0),
    ("<p><b>&#128202; OneDrive Excel</b><br><i>approvals + learning columns</i></p>", "excel", 95),
    ("<p><b>&#128172; Teams</b> <i>(one-way, via Power Automate)</i></p>", "report", 0),
]
SYS_LINKS = {0: ["a1"], 1: ["a2"], 2: ["a2"], 3: ["a2"], 4: ["a2"],
             5: ["ai"], 6: ["excel"], 7: ["report"]}

# reference panels: (title, html_body, height)
PANELS = [
    ("&#128260; STATUS MACHINE",
     "invoice_needed<br>&nbsp;&nbsp;&rarr; data_collected<br>"
     "&nbsp;&nbsp;&rarr; invoice_draft_posted<br>&nbsp;&nbsp;&rarr; invoice_approved<br>"
     "&nbsp;&nbsp;&rarr; invoice_finalized<br>&nbsp;&nbsp;&rarr; <b>invoice_sent</b><br><br>"
     "<i>dead ends:</i> details_missing &middot; condo rejected &middot; "
     "invoice_rejected &middot; on_hold", 330),
    ("&#128737; GUARDRAILS",
     "&bull; the AI <b>never</b> approves its own price<br>"
     "&bull; no client email without a human <b>Approve</b><br>"
     "&bull; exactly-once send: flock + tombstone <i>before</i> the POST<br>"
     "&bull; EMAIL_OVERRIDE_ALL redirects all mail on stage<br>"
     "&bull; the sheet is appended/updated, never wiped<br>"
     "&bull; never asks the same question twice: topic-key dedup + hard cap of "
     "<b>2</b> follow-ups per question<br>"
     "&bull; <b>REPORT_MIN_ORDER_NUMBER</b> hides the old backlog from the report ONLY &mdash; "
     "those orders stay billable and the hidden count is always shown", 420),
    ("&#9201; SCHEDULE <i>(cron, EC2 prod)</i>",
     "<b>*/5</b> &mdash; pipeline A1&rarr;A3<br>"
     "<b>5,10&hellip;55</b> &mdash; Excel approval watcher<br>"
     "<b>:07, :37</b> &mdash; Teams chat watcher<br>"
     "<b>12:00 &amp; 19:00 ET</b> &mdash; Teams report", 250),
    ("&#128295; WHEN THINGS FAIL",
     "&bull; A5 API error &rarr; 3 retries, then logged<br>"
     "&bull; no paynow token &rarr; falls back to the plain message, "
     "<i>the send still succeeds</i><br>"
     "&bull; LLM/JSON error &rarr; messages left unprocessed, retried next tick<br>"
     "&bull; logs: logs/*.log, 14-day rotation", 300),
    ("&#127912; LEGEND",
     "<b>blue</b> AI agent step &nbsp; <b>grey</b> scheduled job / IO<br>"
     "<b>yellow</b> decision &nbsp; <b>orange</b> human only<br>"
     "<b>red</b> stop / exception &nbsp; <b>purple</b> learn &amp; report<br>"
     "<b>navy</b> external system &nbsp; <i>dashed</i> = feedback loop<br>"
     "<i>arrow labels = the status after that step</i>", 260),
]


def build_tech(b: "Board") -> None:
    """Draw the tech workflow: phase bands, flow, systems column, reference panels."""
    b.frame("TECH WORKFLOW - A1 to A7, systems and guardrails",
            T_FRAME_X, T_FRAME_Y, T_FRAME_W, T_FRAME_H, "#f5f6f8")
    b.text("<p><b>&#128295; For the tech team</b></p>", COL_FLOW, -1590, 900, size="26")
    b.text("<p><i>systems it talks to</i></p>", COL_SYS, -1590, 380, size="16", color="#5a6570")
    b.text("<p><i>reference</i></p>", COL_PANEL, -1590, 420, size="16", color="#5a6570")

    # phase bands first so every step draws on top of them
    ids, ys, cursor = {}, {}, -1430
    for title, band_fill, steps in PHASES:
        top = cursor - 100
        bottom = cursor + (len(steps) - 1) * PITCH + 100
        b.shape("", COL_FLOW, (top + bottom) / 2.0, BOX_W + 200, bottom - top,
                band_fill, DARK, "12", "rectangle")
        b.text("<p><b>%s</b></p>" % title, COL_FLOW - 250, top + 26, 460,
               size="15", color="#42526e", align="left")
        for key, kind, html in steps:
            fill, color, shp = KIND[kind]
            w, h = (400, 175) if kind == "decision" else (BOX_W, BOX_H)
            ids[key] = b.shape(html, COL_FLOW, cursor, w, h, fill, color, "12", shp)
            ys[key] = cursor
            cursor += PITCH
        cursor += PHASE_GAP

    for a, c, label in EDGES:
        b.link(ids[a], ids[c], label, "#42526e", width="3")

    for anchor, html, label in EXCEPTIONS:
        eid = b.shape(html, COL_EXC, ys[anchor], 300, 140, RED, WHITE, "11")
        b.link(ids[anchor], eid, label, RED)

    for a, c, label in FEEDBACK:
        b.link(ids[a], ids[c], label, PURPLE, dashed=True, width="3")

    for i, (html, anchor, dy) in enumerate(SYSTEMS):
        sid = b.shape(html, COL_SYS, ys[anchor] + dy, 380, 86, SLATE, WHITE, "11")
        for target in SYS_LINKS.get(i, []):
            b.link(sid, ids[target], "", "#8b95a6", dashed=True, width="1")

    py = -1400
    for title, body, height in PANELS:
        b.shape("<p><b>%s</b></p><p>%s</p>" % (title, body), COL_PANEL, py + height / 2.0,
                460, height, PANEL, DARK, "11", "round_rectangle",
                align="left", valign="top", border="#c8cfd8")
        py += height + 60


# ================================================================ CLIENT workflow
CLIENT = [
    "<p><b>1. &#128176; A job is marked &ldquo;time to bill&rdquo;</b><br><br>"
    "Someone puts a <b>$</b> mark on the job in FTF.<br>"
    "That is the helper&rsquo;s signal to start.</p>",
    "<p><b>2. &#128269; The helper gathers the facts</b><br><br>"
    "It looks up the job, reads past emails, checks<br>"
    "county records, and looks at a satellite photo<br>"
    "of the land.</p>",
    "<p><b>3. &#129504; It works out a fair price</b><br><br>"
    "Like a careful new hire, it thinks it through<br>"
    "step by step and checks what you approved<br>"
    "for similar jobs before.</p>",
    "<p><b>4. &#128221; It writes a draft in your Excel sheet</b><br><br>"
    "<b>Nothing has been sent to the client yet.</b><br>"
    "It is only a suggestion waiting for you.</p>",
    "<p><b>5. &#128587; You decide</b><br><br>"
    "You type <b>Approve</b> &#9989; &nbsp; <b>Reject</b> &#10060; &nbsp; or <b>Hold</b> &#9208;<br>"
    "<b>The helper never decides for you.</b></p>",
    "<p><b>6. &#128231; Only then, the bill goes out</b><br><br>"
    "It creates the invoice and emails the client,<br>"
    "with a <b>Pay Now</b> button so they can pay<br>"
    "in one click.</p>",
    "<p><b>7. &#128218; It learns for next time</b><br><br>"
    "It remembers what you approved. When it is<br>"
    "unsure, it asks you in Teams and waits<br>"
    "for your answer.</p>",
]

CLIENT_NOTES = [
    ("It checks for new jobs every 5 minutes, day and night.", "light_blue"),
    ("It can NEVER email a client on its own. A person must approve first.", "light_pink"),
    ("If it is confused, it stops and asks instead of guessing.", "light_green"),
]


def build_client(b: "Board") -> None:
    b.frame("CLIENT VIEW - plain English", 1050, 150, 1400, 3300, "#f2fbf4")
    b.text("<p><b>&#128172; For everyone else</b></p>", 1050, -1400, 700, size="26")
    cids, y = [], -1150
    for html in CLIENT:
        cids.append(b.shape(html, 1050, y, 900, 230, GREEN, DARK, "16"))
        y += 300
    for a, c in zip(cids, cids[1:]):
        b.link(a, c)
    for i, (note, fill) in enumerate(CLIENT_NOTES):
        b.sticky(note, 680 + i * 370, 1400, 300, fill)


# ================================================================ operations
def move_to_space(board_id: str, space_id: str = SPACE_ID) -> bool:
    """Put the board inside a Miro Space. Needs only boards:write.

    The trick (verified 2026-08-20) is that the writable field is the FLAT integer
    `projectId` on PATCH /v2/boards/{id} — not the nested `project` object the GET
    returns. Getting this wrong is quiet, not loud:
      • PATCH {"project": {...}} or {"spaceId": ...} -> 200 and SILENTLY DISCARDED.
        A 200 proves nothing here; always re-GET and check board.project.
      • PATCH {"projectId": "not-a-number"} -> 400 "Has illegal integer number value"
        (that error is the tell that the field is real).
    The Projects API (/orgs/{o}/teams/{t}/projects) is a red herring: it needs a
    projects:read scope this plan does not offer. It is not needed for this.

    Space ids are not listable without that scope, so SPACE_ID is recorded as config;
    it was read off a board already sitting in the Space. Never raises."""
    try:
        _req("PATCH", "/boards/%s" % board_id, {"projectId": space_id})
        got = ((_req("GET", "/boards/%s" % board_id).get("project") or {}).get("id") or "")
    except RuntimeError as exc:
        print("SPACE: move failed -> %s" % exc)
        return False
    if got != space_id:
        print("SPACE: move did not stick (board.project=%r) - left in team root" % got)
        return False
    print("SPACE: board %s is in Space %s (%s)" % (board_id, SPACE_NAME, space_id))
    return True


def _all_items(bid: str) -> list:
    out, cursor = [], None
    while True:
        q = "/boards/%s/items?limit=50" % bid + (("&cursor=" + cursor) if cursor else "")
        d = _req("GET", q)
        out += d.get("data") or []
        cursor = d.get("cursor")
        if not cursor:
            return out


def clear_tech(bid: str) -> int:
    """Delete ONLY the tech-side items (x < 0), leaving the client frame untouched.

    Every item is created unparented with absolute coordinates, so the sign of x is a
    reliable side marker; the two shared title texts sit at exactly x == 0 and survive.
    Connectors go first so nothing dangles, and frames go last."""
    b = Board(bid)
    items = _all_items(bid)
    tech = {it["id"] for it in items if (it.get("position") or {}).get("x", 0) < 0}
    conns = _req("GET", "/boards/%s/connectors?limit=50" % bid).get("data") or []
    n = 0
    for c in conns:
        if (c.get("startItem") or {}).get("id") in tech or (c.get("endItem") or {}).get("id") in tech:
            _req("DELETE", "/boards/%s/connectors/%s" % (bid, c["id"]))
            n += 1
    for it in sorted((i for i in items if i["id"] in tech),
                     key=lambda i: i["type"] == "frame"):     # frames last
        b.delete(it["id"])
        n += 1
    print("cleared %d tech-side objects (client frame untouched)" % n)
    return n


def build(dry: bool = False) -> str:
    if dry:
        print("PLAN: board '%s' | tech phases=%d steps=%d systems=%d panels=%d | client=%d"
              % (BOARD_NAME, len(PHASES), sum(len(p[2]) for p in PHASES),
                 len(SYSTEMS), len(PANELS), len(CLIENT)))
        return ""
    board = _req("POST", "/boards", {"name": BOARD_NAME, "description": BOARD_DESC})
    b = Board(board["id"])
    print("board created: %s  %s" % (board["id"], board.get("viewLink")))
    b.text("<p><b>FTF &mdash; AI Invoicing Estimator</b></p>", 0, -1850, 1600, size="44")
    b.text("<p><i>the same pipeline told twice: for engineers (left) and for everyone "
           "(right)</i></p>", 0, -1750, 1600, size="20", color="#5a6570")
    build_tech(b)
    build_client(b)
    move_to_space(board["id"])
    print("OPEN: %s" % board.get("viewLink"))
    return board["id"]


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not TOKEN:
        print("ERROR: MIRO_ACCESS_TOKEN missing from .env")
        return 1

    def _arg(flag, default=BOARD_ID_HINT):
        i = argv.index(flag)
        return argv[i + 1] if len(argv) > i + 1 and not argv[i + 1].startswith("--") else default

    if "--dry-run" in argv:
        build(dry=True)
        return 0
    if "--move-only" in argv:
        return 0 if move_to_space(_arg("--move-only")) else 3
    if "--rebuild-tech" in argv:
        bid = _arg("--rebuild-tech")
        clear_tech(bid)
        build_tech(Board(bid))
        print("tech workflow redrawn on %s" % bid)
        return 0
    if "--force" not in argv:
        existing = [x for x in (_req("GET", "/boards?limit=50").get("data") or [])
                    if (x.get("name") or "").strip().lower() == BOARD_NAME.lower()]
        if existing:
            print("ABORT: a board named '%s' already exists (%s). Use --rebuild-tech to "
                  "redraw it, or --force to create another." % (BOARD_NAME, existing[0]["id"]))
            return 2
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
