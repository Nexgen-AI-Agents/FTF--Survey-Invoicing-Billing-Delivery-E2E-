"""
create_demo_video.py — FTF Agentic AI OS demo video generator
Produces docs/demo_sprint_0_6.mp4 with narration and annotated slides.

Requirements (already installed):
    pip install edge-tts moviepy pillow

Usage:
    set PYTHONUTF8=1 && python scripts/create_demo_video.py
"""

import asyncio
import os
import sys
import tempfile
import textwrap
from pathlib import Path

# ── dependency guard ──────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Run: pip install Pillow")
try:
    import edge_tts
except ImportError:
    sys.exit("Run: pip install edge-tts")
try:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
except ImportError:
    sys.exit("Run: pip install moviepy")

# ── output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR   = Path("docs")
OUTPUT_PATH  = OUTPUT_DIR / "demo_sprint_0_6.mp4"
WORK_DIR     = Path(tempfile.mkdtemp(prefix="ftf_demo_"))

# ── video settings ────────────────────────────────────────────────────────────
W, H    = 1280, 720
FPS     = 24
VOICE   = "en-US-JennyNeural"   # Microsoft Neural — warm, professional female

# ── colour palette (GitHub dark) ─────────────────────────────────────────────
BG       = (13,  17,  23)
PANEL    = (22,  27,  34)
BORDER   = (48,  54,  61)
WHITE    = (201, 209, 217)
CYAN     = (79,  192, 255)
GREEN    = (63,  185, 80)
YELLOW   = (210, 153, 34)
RED      = (248, 81,  73)
GRAY     = (139, 148, 158)
BLUE     = (88,  166, 255)
DIM      = (80,  90,  100)

# ── fonts ─────────────────────────────────────────────────────────────────────
_FD = Path("C:/Windows/Fonts")

def _ttf(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        _FD / name,
        _FD / name.lower(),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)

def _fonts():
    return {
        "title":   _ttf("calibrib.ttf", 46),
        "h2":      _ttf("calibrib.ttf", 30),
        "h3":      _ttf("calibrib.ttf", 22),
        "body":    _ttf("consola.ttf",  20),
        "small":   _ttf("calibri.ttf",  17),
        "badge":   _ttf("calibrib.ttf", 17),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  SLIDE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_header(draw: ImageDraw.ImageDraw, fonts: dict, right_text: str = "Sprint 0-6") -> int:
    """Draw NexGen header bar, return y offset after header."""
    draw.rectangle([0, 0, W, 70], fill=PANEL)
    draw.line([0, 70, W, 70], fill=BORDER, width=1)
    draw.text((24, 18), "NexGen  FTF Agentic AI OS", font=fonts["h2"], fill=CYAN)
    draw.text((W - 160, 24), right_text, font=fonts["small"], fill=GRAY)
    return 90


def _draw_footer(draw: ImageDraw.ImageDraw, fonts: dict) -> None:
    """Draw status bar at bottom."""
    draw.rectangle([0, H - 44, W, H], fill=PANEL)
    draw.line([0, H - 44, W, H - 44], fill=BORDER, width=1)
    draw.text((24, H - 30), "186 unit tests  |  0 failures  |  6 sprints", font=fonts["small"], fill=DIM)
    draw.text((W - 200, H - 30), "2026-05-26", font=fonts["small"], fill=DIM)


def _agent_badge(draw: ImageDraw.ImageDraw, fonts: dict, x: int, y: int,
                 num: int, name: str, color: tuple) -> int:
    label = f"  AGENT {num} — {name}  "
    bbox = draw.textbbox((0, 0), label, font=fonts["badge"])
    bw = bbox[2] - bbox[0] + 16
    bh = bbox[3] - bbox[1] + 10
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=6, fill=color)
    draw.text((x + 8, y + 5), label, font=fonts["badge"], fill=BG)
    return y + bh + 16


def _status_badge(draw: ImageDraw.ImageDraw, fonts: dict, x: int, y: int,
                  label: str, color: tuple) -> None:
    text = f"  {label.upper()}  "
    bbox = draw.textbbox((0, 0), text, font=fonts["badge"])
    bw = bbox[2] - bbox[0] + 16
    bh = bbox[3] - bbox[1] + 10
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=5, fill=color)
    draw.text((x + 8, y + 5), text, font=fonts["badge"], fill=BG)


def _wrap_text(draw: ImageDraw.ImageDraw, font, text: str, x: int, y: int,
               max_width: int, color: tuple, line_gap: int = 8) -> int:
    words = text.split()
    line, lines = [], []
    for w in words:
        test = " ".join(line + [w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and line:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    for ln in lines:
        draw.text((x, y), ln, font=font, fill=color)
        bbox = draw.textbbox((x, y), ln, font=font)
        y += (bbox[3] - bbox[1]) + line_gap
    return y


def _bullet(draw: ImageDraw.ImageDraw, fonts: dict, x: int, y: int,
            text: str, color: tuple = WHITE, icon: str = "->") -> int:
    draw.text((x, y), icon, font=fonts["body"], fill=CYAN)
    return _wrap_text(draw, fonts["body"], text, x + 36, y, W - x - 60, color, line_gap=6) + 6


def build_slide(scene: dict, path: str) -> None:
    fonts  = _fonts()
    img    = Image.new("RGB", (W, H), BG)
    draw   = ImageDraw.Draw(img)

    right  = scene.get("header_right", "Sprint 0-6")
    y      = _draw_header(draw, fonts, right)
    _draw_footer(draw, fonts)

    y += 16

    # Optional scenario banner
    if sc := scene.get("scenario"):
        sc_colors = {"1": GREEN, "2": YELLOW, "3": CYAN}
        c = sc_colors.get(str(sc), GRAY)
        draw.text((24, y), f"SCENARIO {sc}", font=fonts["badge"], fill=c)
        y += 28

    # Agent badge
    if (anum := scene.get("agent_num")) is not None:
        badge_colors = {2: CYAN, 3: YELLOW, 4: RED, 5: (170, 80, 240),
                        6: GREEN, 7: YELLOW, 8: BLUE, 9: CYAN}
        bc = badge_colors.get(anum, GRAY)
        y = _agent_badge(draw, fonts, 24, y, anum, scene.get("agent_name", ""), bc)
    else:
        y += 8

    # Title
    if title := scene.get("title"):
        draw.text((24, y), title, font=fonts["title"], fill=WHITE)
        bbox = draw.textbbox((24, y), title, font=fonts["title"])
        y += (bbox[3] - bbox[1]) + 12

    # Subtitle
    if sub := scene.get("subtitle"):
        draw.text((24, y), sub, font=fonts["h3"], fill=GRAY)
        y += 32

    y += 4

    # Bullet lines
    for item in scene.get("bullets", []):
        color = item.get("color", WHITE)
        icon  = item.get("icon", "->")
        text  = item["text"]
        y = _bullet(draw, fonts, 24, y, text, color, icon)

    # Table (list of rows: [label, value, color])
    if table := scene.get("table"):
        col1_w = 320
        for row in table:
            label, value, color = row[0], row[1], row[2] if len(row) > 2 else WHITE
            draw.text((40, y), label, font=fonts["body"], fill=GRAY)
            draw.text((40 + col1_w, y), value, font=fonts["body"], fill=color)
            bbox = draw.textbbox((40, y), label, font=fonts["body"])
            y += (bbox[3] - bbox[1]) + 8

    # Status badge at bottom-left of content
    if status := scene.get("status"):
        status_colors = {
            "PENDING": YELLOW, "CLASSIFIED": GREEN, "PRICED": GREEN,
            "FLAGGED": RED, "AWAITING_APPROVAL": YELLOW, "APPROVED": GREEN,
            "WRITTEN": CYAN, "REVIEWED": GREEN, "SENT": GREEN,
        }
        sc = status_colors.get(status.upper(), GRAY)
        sy = H - 90
        draw.text((24, sy), "DB Status:", font=fonts["small"], fill=DIM)
        _status_badge(draw, fonts, 24 + 100, sy - 2, status, sc)

    img.save(path)


# ═══════════════════════════════════════════════════════════════════════════════
#  NARRATION SCENES
# ═══════════════════════════════════════════════════════════════════════════════

SCENES = [
    # ── 0: Intro ──────────────────────────────────────────────────────────────
    {
        "title":    "FTF Agentic AI Operating System",
        "subtitle": "Automated Estimate Generation Pipeline — Sprints 0 through 6",
        "bullets": [
            {"text": "9 AI agents working in sequence, every 60 minutes, automatically", "color": CYAN, "icon": "->"},
            {"text": "From new order in FTF CRM to estimate email sent — zero human touches on routine orders", "color": WHITE, "icon": "->"},
            {"text": "186 unit tests, 0 failures across 6 completed sprints", "color": GREEN, "icon": "->"},
            {"text": "Built for NexGen Land Surveying, Florida", "color": GRAY, "icon": "->"},
        ],
        "narration": (
            "Welcome to the NexGen FTF Agentic AI demo. "
            "Over the past 6 sprints, we've built a fully automated estimate generation pipeline for NexGen Land Surveying. "
            "This system detects new survey orders from the FTF CRM, classifies them, prices them, writes personalized estimate emails using Claude AI, "
            "reviews them for accuracy, and sends them automatically — every 60 minutes, around the clock. "
            "Let's see it in action."
        ),
    },
    # ── 1: Pipeline overview ──────────────────────────────────────────────────
    {
        "title":   "The 8-Step Pipeline",
        "subtitle": "Every Quote-stage order runs through all 8 steps automatically",
        "table": [
            ["Agent 2  Monitor",   "Scan FTF CRM for new Quote orders",         CYAN],
            ["Agent 3  Classifier","Service type, flood zone, 9 flag triggers", YELLOW],
            ["Agent 4  Human Gate","Route flagged orders to Robert via Teams",   RED],
            ["Agent 5  Pricing",   "FTF API price + elevation cert add-on",      (170,80,240)],
            ["Agent 6  Writer",    "Claude AI writes personalized estimate email",GREEN],
            ["Agent 7  Reviewer",  "4 accuracy checks — self-corrects if needed",YELLOW],
            ["Agent 8  Sender",    "8 AM-6 PM window, 6-13 min human-like delay",BLUE],
            ["Agent 9  Reporter",  "Daily Teams digest — sent, flagged, pipeline",CYAN],
        ],
        "narration": (
            "The pipeline has 8 agents. "
            "Agent 2 scans the FTF CRM. Agent 3 classifies the order. Agent 4 handles any orders that need human review. "
            "Agent 5 prices the estimate. Agent 6 writes the email using Claude AI. Agent 7 reviews it for accuracy. "
            "Agent 8 sends it to the client. And Agent 9 posts a daily summary to Teams. "
            "Now let's walk through 3 real scenarios."
        ),
    },
    # ── 2: Scenario 1 intro ───────────────────────────────────────────────────
    {
        "scenario": 1,
        "title":    "Standard Auto-Quote",
        "subtitle": "Boundary Survey · John Smith · Boca Raton FL · Broward County · Zone X",
        "bullets": [
            {"text": "Routine FL order — standard service, no flags expected", "color": GRAY, "icon": "->"},
            {"text": "Result: full auto-quote, zero human touches", "color": GREEN, "icon": "->"},
        ],
        "narration": "Scenario 1. A standard Boundary Survey order from John Smith in Boca Raton, Florida. This is the most common order type. Let's watch the pipeline handle it automatically.",
    },
    # ── 3: Agent 2 – Monitor ──────────────────────────────────────────────────
    {
        "scenario": 1,
        "agent_num":  2,
        "agent_name": "CRM Monitor",
        "title":   "New order detected in FTF CRM",
        "bullets": [
            {"text": "GET /orders?status=Quote&limit=500 — 275,705 total orders, 12 new", "color": CYAN, "icon": "->"},
            {"text": "Order ORD-2026-1001 found: Boundary Survey, John Smith, Boca Raton FL", "color": WHITE, "icon": "->"},
            {"text": "estimate_sent = False — not yet processed", "color": GRAY, "icon": "->"},
        ],
        "status": "PENDING",
        "narration": (
            "Agent 2, the CRM Monitor, connects to the FTF staging API and scans for new Quote-stage orders. "
            "Out of 275 thousand total orders, 12 are new since the last run. "
            "John's Boundary Survey order is detected and saved to the pipeline database as pending."
        ),
    },
    # ── 4: Agent 3 – Classifier clean ─────────────────────────────────────────
    {
        "scenario": 1,
        "agent_num":  3,
        "agent_name": "Classifier",
        "title":   "9 flag triggers evaluated — all clear",
        "bullets": [
            {"text": 'Service: "Boundary Survey" — canonical FTF name, not in ALWAYS_FLAG or NEVER_AUTO_QUOTE', "color": GREEN, "icon": "[OK]"},
            {"text": "Customer: individual tier, not a competitor email domain", "color": GREEN, "icon": "[OK]"},
            {"text": "Location: FL (in-state), Broward County (no Monroe flag)", "color": GREEN, "icon": "[OK]"},
            {"text": "Flood zone: X — no elevation certificate required", "color": GREEN, "icon": "[OK]"},
            {"text": "All 9 triggers clear — order approved for auto-quote", "color": GREEN, "icon": "[OK]"},
        ],
        "status": "CLASSIFIED",
        "narration": (
            "Agent 3, the Classifier, runs 9 flag triggers against the order. "
            "Boundary Survey is a standard service — not on the always-flag or never-auto-quote lists. "
            "John is an individual customer in Florida, in-state, Broward County. No flood zone concerns. "
            "None of the 9 triggers fire. The order is classified as auto-quoteable."
        ),
    },
    # ── 5: Agent 5 – Pricing ──────────────────────────────────────────────────
    {
        "scenario": 1,
        "agent_num":  5,
        "agent_name": "Pricing Engine",
        "title":   "FTF API pricing confirmed",
        "table": [
            ["Service",              "Boundary Survey",  WHITE],
            ["Tier",                 "individual",       WHITE],
            ["Base amount",          "$350.00",          GREEN],
            ["Elevation cert add-on","$0.00 (Zone X)",   GRAY],
            ["TOTAL ESTIMATE",       "$350.00",          GREEN],
        ],
        "status": "PRICED",
        "narration": (
            "Agent 5, the Pricing Engine, queries the FTF API for the Boundary Survey price at the individual tier. "
            "That returns $350. "
            "No elevation certificate is needed for Zone X. "
            "Total estimate: $350."
        ),
    },
    # ── 6: Agent 6 – Writer ───────────────────────────────────────────────────
    {
        "scenario": 1,
        "agent_num":  6,
        "agent_name": "Estimate Writer",
        "title":   "Claude AI generates personalized estimate email",
        "bullets": [
            {"text": "Model: claude-sonnet-4-6 | Tone: warm, friendly (individual client)", "color": GRAY, "icon": "->"},
            {"text": "Email includes: service name, address, total price ($350.00)", "color": WHITE, "icon": "->"},
            {"text": "Change order clause auto-appended (new language — not in prior estimates)", "color": YELLOW, "icon": "->"},
        ],
        "status": "WRITTEN",
        "narration": (
            "Agent 6, the Estimate Writer, sends the order details to Claude AI. "
            "The system uses a warm, friendly tone for individual clients — not corporate. "
            "Claude generates a personalized estimate email in seconds. "
            "Critically, the change order clause is automatically appended to every estimate. "
            "This is new language that NexGen didn't previously include in their estimates."
        ),
    },
    # ── 7: Agent 7 – Reviewer pass ────────────────────────────────────────────
    {
        "scenario": 1,
        "agent_num":  7,
        "agent_name": "Estimate Reviewer",
        "title":   "4 accuracy checks — all passed",
        "table": [
            ["Total price ($350.00)",      "PASS — matches estimate",      GREEN],
            ["Customer name (John)",       "PASS — present in email",      GREEN],
            ["Property address",           "PASS — 1234 Palm Ave correct", GREEN],
            ["Change order clause",        "PASS — present and complete",  GREEN],
        ],
        "status": "REVIEWED",
        "narration": (
            "Agent 7, the Estimate Reviewer, runs 4 deterministic accuracy checks on the draft. "
            "Is the total price correct? Is the customer name in the email? Is the property address correct? Is the change order clause included? "
            "All 4 pass on the first attempt. No correction loop needed."
        ),
    },
    # ── 8: Agent 8 – Sender ───────────────────────────────────────────────────
    {
        "scenario": 1,
        "agent_num":  8,
        "agent_name": "Sender",
        "title":   "Estimate sent to client",
        "bullets": [
            {"text": "Send window: 8 AM - 6 PM ET — current time 10:32 AM, window open", "color": GREEN, "icon": "->"},
            {"text": "Human-like delay: 9 minutes applied (6-13 min random range)", "color": GRAY, "icon": "->"},
            {"text": "POST /invoices — FTF invoice INV-2026-1001 created", "color": CYAN, "icon": "->"},
            {"text": "Estimate email sent to j.smith@gmail.com", "color": GREEN, "icon": "->"},
        ],
        "status": "SENT",
        "narration": (
            "Agent 8, the Sender, checks the send window — estimates are only sent between 8 AM and 6 PM Eastern time. "
            "It creates the FTF invoice via API and sends the estimate email to John. "
            "A human-like delay of 6 to 13 minutes is applied so the email doesn't appear robotic."
        ),
    },
    # ── 9: Scenario 1 complete ────────────────────────────────────────────────
    {
        "scenario": 1,
        "title":    "Scenario 1 Complete",
        "subtitle": "Zero human touches — full auto-quote delivered",
        "bullets": [
            {"text": "ORD-2026-1001  |  $350.00  |  John Smith  |  Boundary Survey", "color": WHITE, "icon": "->"},
            {"text": "Every agent decision logged to audit database (agent_decision_log)", "color": GRAY, "icon": "->"},
            {"text": "Total pipeline time: under 2 minutes compute (plus send delay)", "color": GREEN, "icon": "->"},
        ],
        "narration": (
            "John's estimate was processed and sent with zero human involvement. "
            "Every step is logged to the audit database. "
            "Now let's see how the system handles an order that requires Robert's judgment."
        ),
    },
    # ── 10: Scenario 2 intro ──────────────────────────────────────────────────
    {
        "scenario": 2,
        "title":    "Flagged Order + Human Gate",
        "subtitle": "ALTA Table A Survey · Coastal Builders LLC · Monroe County FL",
        "bullets": [
            {"text": "ALTA Table A Survey — always requires human review (complex, high-value)", "color": YELLOW, "icon": "!!"},
            {"text": "Monroe County — Florida Keys, non-standard pricing, limited crew", "color": YELLOW, "icon": "!!"},
            {"text": "Result: Human Gate activated, Robert approves in Teams", "color": WHITE, "icon": "->"},
        ],
        "narration": "Scenario 2. Coastal Builders, a B2B client, has requested an ALTA Table A Survey in Monroe County — the Florida Keys. This order will trigger multiple flags.",
    },
    # ── 11: Agent 3 – 2 flags ────────────────────────────────────────────────
    {
        "scenario": 2,
        "agent_num":  3,
        "agent_name": "Classifier",
        "title":   "2 flags fired — routing to Human Gate",
        "bullets": [
            {"text": "TRIGGER 1: ALTA Table A Survey is in ALWAYS_FLAG_SERVICES — mandatory human review", "color": RED, "icon": "!!"},
            {"text": "TRIGGER 10: Monroe County (Florida Keys) — non-standard pricing, limited crew", "color": RED, "icon": "!!"},
            {"text": "Flood zone AE — elevation_cert_required = True (+$225 when priced)", "color": YELLOW, "icon": "->"},
            {"text": "Pricing deferred — Human Gate must approve before estimating ALTA", "color": YELLOW, "icon": "->"},
        ],
        "status": "FLAGGED",
        "narration": (
            "The Classifier fires two flags immediately. "
            "First, ALTA Table A Survey is on the always-flag list — it's a complex, high-value survey that Robert requires human review for every single time. "
            "Second, Monroe County triggers a separate flag for non-standard pricing and limited crew availability in the Florida Keys. "
            "The order is flagged and routed to the Human Gate. Pricing is deferred until Robert approves."
        ),
    },
    # ── 12: Agent 4 – Teams notification ─────────────────────────────────────
    {
        "scenario": 2,
        "agent_num":  4,
        "agent_name": "Human Gate",
        "title":   "Teams notification sent to Robert",
        "table": [
            ["Order ID",        "ORD-2026-1002",              WHITE],
            ["Service",         "ALTA Table A Survey",         YELLOW],
            ["County",          "Monroe",                      YELLOW],
            ["Flag Reason",     "ALWAYS_FLAG + Monroe County", RED],
            ["Elevation Cert",  "Required (Zone AE)",          CYAN],
            ["Estimate Amount", "TBD — pending approval",      GRAY],
        ],
        "status": "AWAITING_APPROVAL",
        "narration": (
            "Agent 4, the Human Gate, sends a detailed notification to Robert in MS Teams. "
            "The card shows the order ID, service type, county, flag reasons, and that an elevation certificate will be needed. "
            "Robert can review the property in the FTF CRM and check it on GIS before making his decision."
        ),
    },
    # ── 13: Robert approves ───────────────────────────────────────────────────
    {
        "scenario": 2,
        "agent_num":  4,
        "agent_name": "Human Gate",
        "title":   "Robert approves — pipeline resumes",
        "bullets": [
            {"text": 'Robert (Teams): "approve"', "color": GREEN, "icon": "->"},
            {"text": "process_approval_reply() records approval — status set to approved", "color": GREEN, "icon": "->"},
            {"text": "Agent 5 prices: $1,500 (ALTA) + $225 (elevation cert) = $1,725", "color": WHITE, "icon": "->"},
            {"text": "Agent 6: B2B estimate (concise, professional tone)", "color": WHITE, "icon": "->"},
            {"text": "Agent 7: 4 checks PASSED | Agent 8: sent to client", "color": GREEN, "icon": "->"},
        ],
        "status": "SENT",
        "narration": (
            "Robert reviews the order and types approve in Teams. "
            "The system immediately picks up the approval. "
            "Agent 5 prices the ALTA at $1,500 plus the $225 elevation certificate add-on, for a total of $1,725. "
            "Agent 6 writes a B2B estimate with concise, professional tone. The reviewer passes. The sender delivers it."
        ),
    },
    # ── 14: Scenario 2 complete ───────────────────────────────────────────────
    {
        "scenario": 2,
        "title":    "Scenario 2 Complete",
        "subtitle": "Every flag triggers human review — nothing bypasses Robert",
        "bullets": [
            {"text": "ORD-2026-1002  |  $1,725.00  |  Coastal Builders LLC  |  Monroe County", "color": WHITE, "icon": "->"},
            {"text": "Robert approved in Teams — full audit trail in agent_decision_log", "color": GRAY, "icon": "->"},
        ],
        "narration": (
            "Every order that needs Robert's judgment gets it. Nothing is auto-sent without his sign-off on flagged orders. "
            "Once he approves, the AI handles everything else. "
            "Now let's see the AI's self-correction capability."
        ),
    },
    # ── 15: Scenario 3 intro ─────────────────────────────────────────────────
    {
        "scenario": 3,
        "title":    "Reviewer Self-Correction Loop",
        "subtitle": "Elevation Certificate · Maria Santos · Miami Beach FL · Zone AE",
        "bullets": [
            {"text": "Zone AE property — elevation certificate required, adds $225 to estimate", "color": CYAN, "icon": "->"},
            {"text": "Writer makes a mistake on attempt 1 — wrong price in email body", "color": RED, "icon": "!!"},
            {"text": "Reviewer catches the error, sends correction note back to Writer", "color": YELLOW, "icon": "->"},
            {"text": "Writer fixes it on attempt 2 — all 4 checks pass", "color": GREEN, "icon": "->"},
        ],
        "narration": "Scenario 3. Maria Santos needs an Elevation Certificate for a property in Miami Beach, which is in a FEMA AE flood zone. Watch how the AI catches and corrects its own mistake.",
    },
    # ── 16: Agents 3+5 elevation ──────────────────────────────────────────────
    {
        "scenario": 3,
        "agent_num":  5,
        "agent_name": "Pricing Engine",
        "title":   "Flood zone AE — elevation cert add-on applied",
        "table": [
            ["Flood zone",           "AE — FEMA flood zone",     CYAN],
            ["elevation_cert_required","True (auto-detected)",   CYAN],
            ["Base amount",          "$225.00",                  WHITE],
            ["Elevation cert add-on","$225.00",                  CYAN],
            ["TOTAL ESTIMATE",       "$450.00",                  GREEN],
        ],
        "status": "PRICED",
        "narration": (
            "The Classifier detects the AE flood zone and marks elevation certificate required as true. "
            "The Pricing Engine adds the $225 elevation certificate surcharge to the $225 base price. "
            "Correct total: $450."
        ),
    },
    # ── 17: Agent 6 bad draft ─────────────────────────────────────────────────
    {
        "scenario": 3,
        "agent_num":  6,
        "agent_name": "Estimate Writer  (Attempt 1 of 3)",
        "title":   "First draft — price error",
        "bullets": [
            {"text": 'Email body shows: Total: $350.00  <-- WRONG (base only, forgot add-on)', "color": RED, "icon": "!!"},
            {"text": "Correct total should be $450.00 ($225 base + $225 elevation cert)", "color": YELLOW, "icon": "->"},
        ],
        "narration": "The Writer generates the first draft — but makes an error. It writes $350 in the email body, which is only the base price. It forgot to include the elevation certificate add-on.",
    },
    # ── 18: Agent 7 catches error ─────────────────────────────────────────────
    {
        "scenario": 3,
        "agent_num":  7,
        "agent_name": "Estimate Reviewer  (Checking Attempt 1)",
        "title":   "Price check FAILED — correction sent to Writer",
        "table": [
            ["Total price",         "FAIL — $350 in email, $450 expected", RED],
            ["Customer name",       "PASS — Maria present",                GREEN],
            ["Property address",    "PASS — 456 Ocean Drive correct",      GREEN],
            ["Change order clause", "PASS — present and complete",         GREEN],
        ],
        "narration": (
            "The Reviewer immediately catches the price mismatch. "
            "The total in the email — $350 — does not match the estimate total of $450. "
            "It generates a specific correction note and sends it back to the Writer for attempt 2."
        ),
    },
    # ── 19: Agent 6 correct draft ────────────────────────────────────────────
    {
        "scenario": 3,
        "agent_num":  6,
        "agent_name": "Estimate Writer  (Attempt 2 of 3)",
        "title":   "Corrected draft — $450 with breakdown",
        "bullets": [
            {"text": "Correction note applied: Total must be $450 = $225 base + $225 elevation cert add-on", "color": CYAN, "icon": "->"},
            {"text": "New draft shows: $450.00 with clear FEMA AE flood zone context", "color": GREEN, "icon": "->"},
        ],
        "narration": "The Writer rewrites the email with the correction applied. This time it shows $450, with a clear breakdown of the base and elevation certificate add-on. The FEMA context is also added to help the client understand the extra charge.",
    },
    # ── 20: Agent 7 all pass ──────────────────────────────────────────────────
    {
        "scenario": 3,
        "agent_num":  7,
        "agent_name": "Estimate Reviewer  (Checking Attempt 2)",
        "title":   "All 4 checks passed on attempt 2",
        "table": [
            ["Total price ($450.00)", "PASS — matches estimate",     GREEN],
            ["Customer name (Maria)", "PASS — present in email",     GREEN],
            ["Property address",      "PASS — 456 Ocean Drive correct", GREEN],
            ["Change order clause",   "PASS — present and complete", GREEN],
        ],
        "status": "SENT",
        "narration": (
            "The Reviewer checks the corrected draft. All 4 accuracy checks pass on the second attempt. "
            "The estimate is sent to Maria. "
            "If the AI had failed 3 times in a row, the order would automatically escalate to the Human Gate — nothing slips through."
        ),
    },
    # ── 21: Agent 9 daily report ─────────────────────────────────────────────
    {
        "agent_num":  9,
        "agent_name": "Reporter",
        "title":   "Daily Teams digest — end of day",
        "table": [
            ["Estimates Sent Today",     "8",   GREEN],
            ["Flagged (Needs Review)",   "2",   YELLOW],
            ["Awaiting Human Approval",  "1",   YELLOW],
            ["Ready to Send",            "3",   CYAN],
            ["Active Pipeline (total)",  "14",  WHITE],
        ],
        "narration": (
            "At the end of each day, Agent 9 posts a digest to the FTF Invoicing channel in MS Teams. "
            "Today: 8 estimates sent, 2 orders flagged for review, 1 awaiting Robert's approval, and 14 orders total in the pipeline. "
            "Ryan, Robert, and the team get this every day automatically."
        ),
    },
    # ── 22: Outro ─────────────────────────────────────────────────────────────
    {
        "title":    "Sprint 0-6 Complete",
        "subtitle": "Estimate generation loop — built, tested, functionally ready",
        "bullets": [
            {"text": "9 agents, 186 unit tests, 0 failures, 6 sprints delivered", "color": GREEN, "icon": "->"},
            {"text": "Sprint 7: AR Follow-Up Loop  (needs Jessica recording to unlock)", "color": YELLOW, "icon": "->"},
            {"text": "Sprint 8: Monthly Statements  (needs Wyatt recording to unlock)", "color": YELLOW, "icon": "->"},
            {"text": "Sprint 9: Orchestrator — full 24/7 autonomous pipeline", "color": CYAN, "icon": "->"},
            {"text": "Sprint 10: Staging test with live FTF data", "color": CYAN, "icon": "->"},
            {"text": "Sprint 11: Limited production go-live", "color": GREEN, "icon": "->"},
        ],
        "narration": (
            "That's the complete Sprint 0 through 6 demo. "
            "The estimate generation loop is built and tested with 186 passing unit tests. "
            "To unlock Sprints 7 and 8, we need the Jessica and Wyatt recordings — those cover the AR follow-up reminders and monthly B2B statements. "
            "Sprint 9 will add the full orchestrator that runs all three loops 24 hours a day, 7 days a week. "
            "Thank you."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  AUDIO GENERATION (edge-tts)
# ═══════════════════════════════════════════════════════════════════════════════

async def _generate_audio(text: str, output_mp3: str, voice: str = VOICE) -> float:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_mp3)
    clip = AudioFileClip(output_mp3)
    dur = clip.duration
    clip.close()
    return dur


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ASSEMBLER
# ═══════════════════════════════════════════════════════════════════════════════

async def build_video() -> None:
    print(f"Building demo video — {len(SCENES)} scenes")
    print(f"Voice: {VOICE}")
    print(f"Work dir: {WORK_DIR}")
    print(f"Output: {OUTPUT_PATH}")
    print()

    clips = []

    for i, scene in enumerate(SCENES):
        narration = scene.get("narration", "")
        slide_path = str(WORK_DIR / f"slide_{i:02d}.png")
        audio_path = str(WORK_DIR / f"audio_{i:02d}.mp3")

        print(f"  [{i+1:02d}/{len(SCENES)}] {scene.get('title', '?')[:50]}")

        # Build slide image
        build_slide(scene, slide_path)

        # Generate narration audio
        duration = await _generate_audio(narration, audio_path)
        duration += 0.5  # small pause after each scene

        # Create video clip: image held for audio duration
        audio_clip = AudioFileClip(audio_path)
        img_clip   = ImageClip(slide_path, duration=duration)
        video_clip = img_clip.with_audio(audio_clip)
        clips.append(video_clip)

    print()
    print("Assembling final video...")
    final = concatenate_videoclips(clips, method="compose")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(OUTPUT_PATH),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )

    # Cleanup
    for clip in clips:
        try:
            clip.close()
        except Exception:
            pass
    final.close()

    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print()
    print(f"Done: {OUTPUT_PATH}  ({size_mb:.1f} MB)")
    print(f"Duration: {final.duration:.0f} seconds")


if __name__ == "__main__":
    asyncio.run(build_video())
