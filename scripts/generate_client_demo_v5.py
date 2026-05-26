"""
generate_client_demo_v5.py — Client demo v5

Changes from v4:
  1. Sprint 9 (Memory Loop) complete — marked in sidebar
  2. New scene: Sprint 9 story (real-time listener + nightly memory + 7-day reflection)
  3. Stats updated: 8 sprints complete, 203 tests passing
  4. LISTEN/NOTIFY headline: order-to-estimate now <2 min instead of 73 min
  5. Roadmap updated: Sprint 9 done, next is 7 & 8 (blocked on recordings)
  6. Header tag: Sprint 0-9 Phase 1

Output: docs/demos/YYYYMMDD_v5/demo.mp4 + transcript.md
"""

import asyncio
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent / "code" / "shared"))
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import edge_tts
from moviepy import AudioFileClip, VideoClip, concatenate_videoclips

OAI = OpenAI(api_key=os.getenv("OpenAI_API_KEY"))

# ═══════════════════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════════════════

DATE_TAG  = datetime.now().strftime("%Y%m%d")
DEMO_DIR  = Path("docs") / "demos" / f"{DATE_TAG}_v5"
AUDIO_DIR = DEMO_DIR / "audio"
TS_DIR    = DEMO_DIR / "timestamps"

for d in [DEMO_DIR, AUDIO_DIR, TS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

OUTPUT     = DEMO_DIR / "demo.mp4"
TRANSCRIPT = DEMO_DIR / "transcript.md"

# ═══════════════════════════════════════════════════════════════════════════
#  LAYOUT
# ═══════════════════════════════════════════════════════════════════════════

W, H       = 1920, 1080
FPS        = 24
HDR_H      = 68
SBTL_H     = 80
WORKFLOW_W = 420
CONTENT_W  = W - WORKFLOW_W   # 1500
CONTENT_X  = 0
WORKFLOW_X = CONTENT_W        # 1500

NAVY   = (10,  20,  60)
NAVY2  = (16,  32,  80)
BLUE   = (37,  99, 235)
CYAN   = (79, 195, 247)
WHITE  = (255, 255, 255)
DARK   = (15,  23,  42)
GRAY   = (100, 116, 139)
GREEN  = (22, 163,  74)
AMBER  = (202, 138,   4)
RED    = (220,  38,  38)
PURPLE = (139,  92, 246)

_FD = Path("C:/Windows/Fonts")

def _f(name: str, size: int) -> ImageFont.FreeTypeFont:
    for p in [_FD / name, _FD / name.lower()]:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)

def _fonts() -> dict:
    return {
        "h1":    _f("calibrib.ttf", 48),
        "h2":    _f("calibrib.ttf", 34),
        "h3":    _f("calibrib.ttf", 26),
        "body":  _f("calibri.ttf",  22),
        "small": _f("calibri.ttf",  18),
        "tag":   _f("calibrib.ttf", 15),
        "mono":  _f("consola.ttf",  18),
        "sbtl":  _f("calibrib.ttf", 30),
        "wf":    _f("calibrib.ttf", 13),
    }

# ═══════════════════════════════════════════════════════════════════════════
#  SCENES  (11 scenes — v5 adds Sprint 9 story between write_send and roadmap)
# ═══════════════════════════════════════════════════════════════════════════

SCENES = [
    (0,  "intro",
     "Welcome. Let me show you exactly what we built — "
     "9 AI agents that automate your entire quoting process. "
     "We'll follow one real order, start to finish."),

    (1,  "problem",
     "Before: your team had to manually check Field to Finish for new orders, "
     "look up the price, write the email, and send it. "
     "50 new orders a week — hours of repetitive work every day."),

    (2,  "pipeline",
     "The solution: 9 AI agents running around the clock. "
     "Detect, classify, price, approve if needed, write, review, send, report — "
     "and now: a real-time listener that eliminates the wait between every step. "
     "8 complete sprints, 203 automated tests."),

    (3,  "meet_order",
     "Let's follow John Martinez. He submits a Boundary Survey request at 9:14 AM. "
     "Half an acre, Hillsborough County. He's waiting for a quote. "
     "Before this system — he might wait until tomorrow."),

    (4,  "monitor",
     "Agent 2 scans Field to Finish every 60 minutes. "
     "It finds John's order, confirms it's new, and logs it to the database. "
     "Status: pending. Nobody on your team did anything."),

    (5,  "classify",
     "Agent 3 runs 14 checks in under 2 seconds. "
     "Standard service, Florida property, no competitor, no flood zone issues — "
     "all 14 checks pass. Agent 5 pulls the price from Field to Finish: 350 dollars."),

    (6,  "human_gate",
     "For complex orders — like this ALTA Survey in Monroe County — "
     "Agent 4 sends Robert a Teams alert instantly. "
     "Robert reviews it, types approve, and the pipeline continues. "
     "Nothing sensitive goes out without a human sign-off."),

    (7,  "write_send",
     "Back to John. Agent 6 writes a personalized estimate email. "
     "Agent 7 runs 4 accuracy checks: price, name, address, change order clause. "
     "Agent 8 sends the quote. "
     "With our new real-time listener, that entire sequence completes in under 2 minutes."),

    (8,  "sprint9",
     "Sprint 9 adds three things the pipeline was missing. "
     "A real-time database listener: the instant Agent 2 saves an order, "
     "a PostgreSQL trigger fires and the full pipeline runs immediately. "
     "A nightly memory log: every decision every agent made, written to a structured file. "
     "And a 7-day pattern analyzer that flags any agent falling below 90 percent accuracy. "
     "The system now watches itself."),

    (9,  "roadmap",
     "8 sprints are complete. Sprint 9 delivered real-time processing and self-monitoring. "
     "Sprints 7 and 8 are the AR follow-up loop and monthly statements — "
     "both need process recordings from Jessica and Wyatt. "
     "Once those arrive, we build them. Sprint 10 is the full staging test."),

    (10, "outro",
     "203 automated tests. 9 agents. 8 sprints delivered. "
     "Orders that used to take 5 hours now process in under 2 minutes. "
     "The system monitors its own health every night. "
     "Your quoting process runs automatically. Thank you."),
]

SCENE_SPRINTS = {
    0:  [],
    1:  [],
    2:  list(range(10)),
    3:  [1],
    4:  [1],
    5:  [2],
    6:  [3],
    7:  [4, 5, 6],
    8:  [9],
    9:  list(range(10, 13)),
    10: list(range(10)),
}

SPRINT_LABELS = [
    (0,  "Foundation",    True),
    (1,  "Monitor",       True),
    (2,  "Classifier",    True),
    (3,  "Human Gate",    True),
    (4,  "Writer",        True),
    (5,  "Reviewer",      True),
    (6,  "Sender",        True),
    (7,  "AR Follow-Up",  False),
    (8,  "Statements",    False),
    (9,  "Memory Loop",   True),
    (10, "Staging Tests", False),
    (11, "Ltd Launch",    False),
    (12, "Full Prod",     False),
]

# ═══════════════════════════════════════════════════════════════════════════
#  SUBTITLE CHUNKS
# ═══════════════════════════════════════════════════════════════════════════

def make_subtitle_chunks(words: list[dict], words_per_chunk: int = 8) -> list[dict]:
    chunks = []
    n = len(words)
    i = 0
    while i < n:
        cw = words[i:i + words_per_chunk]
        text = " ".join(w["word"] for w in cw)
        start = cw[0]["start"]
        end = words[i + words_per_chunk]["start"] if i + words_per_chunk < n else cw[-1]["end"] + 0.5
        chunks.append({"text": text, "start": start, "end": end})
        i += words_per_chunk
    return chunks


def subtitle_at(t: float, chunks: list[dict]) -> str:
    for chunk in chunks:
        if chunk["start"] <= t < chunk["end"]:
            return chunk["text"]
    return ""


# ═══════════════════════════════════════════════════════════════════════════
#  WORD TIMESTAMPS (Whisper — cached)
# ═══════════════════════════════════════════════════════════════════════════

def get_word_timestamps(audio_path: Path, text: str, scene_slug: str) -> list[dict]:
    cache_path = TS_DIR / f"{scene_slug}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    try:
        with open(audio_path, "rb") as f:
            result = OAI.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word"],
                prompt=text[:200],
            )
        words = [{"word": w.word.strip(), "start": float(w.start), "end": float(w.end)}
                 for w in result.words if w.word.strip()]
        cache_path.write_text(json.dumps(words, indent=2), encoding="utf-8")
        return words
    except Exception as e:
        print(f"    [whisper] fallback for {scene_slug}: {e}")
        clip = AudioFileClip(str(audio_path))
        dur = clip.duration
        clip.close()
        ws = text.split()
        dt = dur / max(len(ws), 1)
        words = [{"word": w, "start": i * dt, "end": (i + 1) * dt} for i, w in enumerate(ws)]
        cache_path.write_text(json.dumps(words, indent=2), encoding="utf-8")
        return words


# ═══════════════════════════════════════════════════════════════════════════
#  WORKFLOW SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

def render_workflow_sidebar(fnt: dict, active_sprints: list[int]) -> np.ndarray:
    img  = Image.new("RGBA", (WORKFLOW_W, H), (8, 14, 48, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, WORKFLOW_W, HDR_H], fill=(12, 20, 58))
    draw.line([0, HDR_H, WORKFLOW_W, HDR_H], fill=BLUE, width=2)
    draw.text((16, 22), "SPRINT PROGRESS", font=fnt["wf"], fill=CYAN)

    content_h = H - HDR_H - SBTL_H
    row_h = content_h // len(SPRINT_LABELS)
    ry = HDR_H

    for num, label, done in SPRINT_LABELS:
        active = num in active_sprints
        if done:
            bg = (12, 44, 26) if active else (10, 30, 18)
        else:
            bg = (50, 14, 14) if active else (28, 12, 12)
        draw.rectangle([0, ry, WORKFLOW_W, ry + row_h], fill=bg)
        bar_col = GREEN if done else RED
        draw.rectangle([0, ry, 5, ry + row_h], fill=bar_col)
        if active:
            draw.rectangle([5, ry, WORKFLOW_W, ry + 2], fill=bar_col)

        draw.text((14, ry + row_h // 2 - 10), f"S{num:02d}", font=fnt["wf"], fill=GRAY)
        label_color = (180, 255, 190) if (done and active) else \
                      (140, 200, 150) if done else \
                      (255, 160, 160) if active else \
                      (200, 120, 120)
        draw.text((50, ry + row_h // 2 - 10), label, font=fnt["wf"], fill=label_color)
        mark = "✓" if done else "✗"
        mark_col = GREEN if done else RED
        if active:
            draw.ellipse([WORKFLOW_W - 32, ry + row_h // 2 - 12,
                          WORKFLOW_W - 8,  ry + row_h // 2 + 12],
                         fill=(*mark_col, 60))
        draw.text((WORKFLOW_W - 28, ry + row_h // 2 - 9), mark, font=fnt["wf"], fill=mark_col)
        draw.line([0, ry + row_h, WORKFLOW_W, ry + row_h], fill=(20, 30, 70), width=1)
        ry += row_h

    leg_y = H - SBTL_H - 28
    draw.text((12, leg_y), "✓ Complete  ✗ Pending", font=fnt["wf"], fill=(80, 100, 130))
    return np.array(img.convert("RGB"))


def build_sidebar_cache(fnt: dict) -> dict:
    print("  [sidebar] pre-rendering workflow panels per scene...")
    cache = {}
    for idx, slug, _ in SCENES:
        cache[idx] = render_workflow_sidebar(fnt, SCENE_SPRINTS.get(idx, []))
    return cache


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def _content_bg(draw: ImageDraw.ImageDraw, w: int = CONTENT_W, h: int = H) -> None:
    for y in range(h):
        t = y / h
        r = int(NAVY[0] * (1 - t) + NAVY2[0] * t)
        g = int(NAVY[1] * (1 - t) + NAVY2[1] * t)
        b = int(NAVY[2] * (1 - t) + NAVY2[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _content_header(draw: ImageDraw.ImageDraw, fnt: dict, title: str,
                    scene_num: int, w: int = CONTENT_W) -> None:
    draw.rectangle([0, 0, w, HDR_H], fill=(8, 15, 50))
    draw.line([0, HDR_H, w, HDR_H], fill=BLUE, width=3)
    draw.text((20, 18), "FTF  ·  Agentic AI OS  ·  Sprint 0–9  ·  Phase 1", font=fnt["tag"], fill=CYAN)
    total = len(SCENES)
    dot_w, dot_r = 16, 4
    sx = w - total * dot_w - 16
    for i in range(total):
        cx2 = sx + i * dot_w + dot_r
        cy2 = HDR_H // 2
        draw.ellipse([cx2 - dot_r, cy2 - dot_r, cx2 + dot_r, cy2 + dot_r],
                     fill=CYAN if i == scene_num else (40, 55, 90))


def _white_card(img: Image.Image, w: int = CONTENT_W) -> tuple:
    pad = 36
    x0, y0 = pad, HDR_H + pad
    x1, y1 = w - pad, H - SBTL_H - pad
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(255, 255, 255, 245))
    d.rounded_rectangle([x0, y0, x1, y0 + 7], radius=16, fill=(*BLUE, 255))
    return img, d, x0 + 48, y0 + 48


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, line = text.split(), [], []
    for w in words:
        test = " ".join(line + [w])
        if draw.textbbox((0, 0), test, font=font)[2] > max_w and line:
            lines.append(" ".join(line)); line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return lines


def slide_bullets(scene_num: int, title: str, bullets: list[tuple], fnt: dict,
                  tag: str = "") -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, tag, scene_num)
    img, draw, tx, ty = _white_card(img)
    draw.text((tx, ty), title, font=fnt["h1"], fill=DARK)
    ty += draw.textbbox((0, 0), title, font=fnt["h1"])[3] + 36
    for text, color in bullets:
        draw.ellipse([tx, ty + 10, tx + 14, ty + 24], fill=BLUE)
        for ln in _wrap(draw, text, fnt["body"], CONTENT_W - 140):
            draw.text((tx + 28, ty), ln, font=fnt["body"], fill=color)
            ty += draw.textbbox((0, 0), ln, font=fnt["body"])[3] + 4
        ty += 18
    return np.array(img.convert("RGB"))


def slide_intro(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Introduction", 0)
    img, draw, tx, ty = _white_card(img)

    draw.text((tx, ty),      "Field to Finish",          font=fnt["h1"], fill=DARK)
    draw.text((tx, ty + 62), "Automated Quoting System", font=fnt["h2"], fill=BLUE)
    draw.line([tx, ty + 114, CONTENT_W - 72, ty + 114], fill=(219, 234, 254), width=2)

    stats = [("9", "AI Agents"), ("8", "Sprints"), ("203", "Tests Passing")]
    bx = tx; by = ty + 138; bw, bh = 270, 140
    for num, lbl in stats:
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=12, fill=(239, 246, 255))
        draw.rounded_rectangle([bx, by, bx + bw, by + 7], radius=12, fill=BLUE)
        nb = draw.textbbox((0, 0), num, font=fnt["h1"])
        draw.text((bx + (bw - (nb[2] - nb[0])) // 2, by + 18), num, font=fnt["h1"], fill=BLUE)
        lb = draw.textbbox((0, 0), lbl, font=fnt["small"])
        draw.text((bx + (bw - (lb[2] - lb[0])) // 2, by + 92), lbl, font=fnt["small"], fill=GRAY)
        bx += bw + 40

    tag_str = "Sprint 0-9 Delivery  ·  May 2026  ·  Phase 1 Complete"
    tb = draw.textbbox((0, 0), tag_str, font=fnt["body"])
    draw.text((tx + (CONTENT_W - tx * 2 - (tb[2] - tb[0])) // 2, by + bh + 36),
              tag_str, font=fnt["body"], fill=GRAY)
    return np.array(img.convert("RGB"))


def slide_pipeline(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Pipeline", 2)

    pad = 36
    x0, y0 = pad, HDR_H + pad
    x1, y1 = CONTENT_W - pad, H - SBTL_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(15, 23, 42, 250))
    draw.rounded_rectangle([x0, y0, x1, y0 + 54], radius=16, fill=(20, 35, 80, 255))
    draw = ImageDraw.Draw(img)
    draw.text((x0 + 24, y0 + 14), "9-AGENT PIPELINE  —  ALL BUILT & TESTED", font=fnt["h3"], fill=CYAN)

    rows = [
        ("Agent 0", "Listener",       "S9", PURPLE, "Real-time NOTIFY → pipeline in <2 min"),
        ("Agent 2", "Monitor",        "S1", GREEN,  "Scans FTF every 60 min"),
        ("Agent 3", "Classifier",     "S2", GREEN,  "14 flag checks in <2s"),
        ("Agent 4", "Human Gate",     "S3", GREEN,  "Teams alert for complex orders"),
        ("Agent 5", "Pricing Engine", "S2", GREEN,  "Pulls price from FTF API"),
        ("Agent 6", "Writer",         "S4", GREEN,  "Personalized estimate email"),
        ("Agent 7", "Reviewer",       "S5", GREEN,  "4-check accuracy review"),
        ("Agent 8", "Sender",         "S6", GREEN,  "Sends 8 AM–6 PM"),
        ("Agent 9", "Reporter",       "S6", GREEN,  "Daily Teams digest"),
    ]
    rh = (y1 - y0 - 60) // len(rows)
    ry = y0 + 60
    for i, (num, name, sprint, col, desc) in enumerate(rows):
        bg = (18, 30, 68) if i % 2 == 0 else (14, 24, 56)
        draw.rectangle([x0, ry, x1, ry + rh], fill=bg)
        draw.rounded_rectangle([x0 + 10, ry + rh // 2 - 13, x0 + 44, ry + rh // 2 + 13],
                                radius=5, fill=(18, 48, 26))
        draw.text((x0 + 16, ry + rh // 2 - 10), "✓", font=fnt["tag"], fill=GREEN)
        draw.text((x0 + 60,  ry + 9), num,    font=fnt["tag"],  fill=GRAY)
        draw.text((x0 + 200, ry + 7), name,   font=fnt["h3"],   fill=WHITE)
        sb  = draw.textbbox((0, 0), sprint, font=fnt["small"])
        bw2 = sb[2] - sb[0] + 18
        bx2 = x0 + 560
        sprint_bg = (50, 20, 80) if sprint == "S9" else (20, 40, 100)
        draw.rounded_rectangle([bx2, ry + 7, bx2 + bw2, ry + 7 + sb[3] + 10],
                                radius=4, fill=sprint_bg)
        sprint_col = (180, 120, 255) if sprint == "S9" else CYAN
        draw.text((bx2 + 8, ry + 11), sprint, font=fnt["small"], fill=sprint_col)
        draw.text((x0 + 660, ry + 9), desc, font=fnt["body"], fill=(148, 163, 184))
        ry += rh
    return np.array(img.convert("RGB"))


def slide_ftf(fnt: dict, scene_num: int) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Field to Finish Portal", scene_num)

    bx, by = 32, HDR_H + 32
    bw = CONTENT_W - 64
    bh = H - SBTL_H - by - 32

    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=12, fill=(240, 242, 247))
    draw.rounded_rectangle([bx, by, bx + bw, by + 44], radius=12, fill=WHITE)
    for xi, col in [(bx+10,(239,68,68)), (bx+30,(234,179,8)), (bx+50,(22,163,74))]:
        draw.ellipse([xi, by+14, xi+16, by+30], fill=col)
    draw.text((bx+76, by+14), "stage.fieldtofinish.jobs/orders", font=fnt["small"], fill=GRAY)

    ay = by + 44
    draw.rectangle([bx, ay, bx + bw, ay + 52], fill=(30, 64, 175))
    draw.text((bx+20, ay+12), "Field to Finish", font=fnt["h3"], fill=WHITE)
    draw.text((bx+bw-340, ay+14), "Orders   Clients   Reports", font=fnt["small"], fill=(186,209,255))

    ty = ay + 52 + 16
    draw.rectangle([bx+10, ty, bx+bw-10, ty+40], fill=(239,246,255))
    draw.text((bx+22, ty+10), "Quote-Stage Orders  —  New in last 60 minutes",
              font=fnt["small"], fill=(30,64,175))

    hdrs = ["Order ID", "Service Type", "Client", "County", "Time", "Status"]
    cxs  = [bx+14, bx+210, bx+530, bx+820, bx+1020, bx+1200]
    hy = ty + 50
    draw.rectangle([bx+10, hy, bx+bw-10, hy+36], fill=(219,234,254))
    for h2, c in zip(hdrs, cxs):
        draw.text((c, hy+8), h2, font=fnt["tag"], fill=(30,64,175))

    tbl_rows = [
        ("ORD-2026-1001", "Boundary Survey",     "John Martinez",      "Hillsborough", "9:14 AM",  True),
        ("ORD-2026-1002", "ALTA Table A Survey",  "Coastal Builders LLC","Monroe",      "10:02 AM", False),
        ("ORD-2026-1003", "Elevation Cert.",       "Maria Santos",       "Miami-Dade",  "10:47 AM", False),
    ]
    ry = hy + 36
    for i, (oid, svc, cl, co, ts, hi) in enumerate(tbl_rows):
        bg = (220,252,231) if hi else (241,245,255) if i%2==0 else WHITE
        draw.rectangle([bx+10, ry, bx+bw-10, ry+44], fill=bg)
        for v, c in zip([oid, svc, cl, co, ts], cxs):
            draw.text((c, ry+12), v, font=fnt["small"], fill=DARK)
        lbl = "● JOHN'S ORDER" if hi else "● Quote"
        draw.text((cxs[5], ry+12), lbl, font=fnt["small"], fill=GREEN if hi else BLUE)
        ry += 44

    draw.rounded_rectangle([bx+14, ry+18, bx+520, ry+52], radius=6, fill=(220,252,231))
    draw.text((bx+26, ry+26), "Agent 2 Monitor: ACTIVE — scanning every 60 min",
              font=fnt["small"], fill=(22,101,52))
    return np.array(img.convert("RGB"))


def slide_classify(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Classify & Price", 5)
    img, draw, tx, ty = _white_card(img)

    draw.text((tx, ty), "Agent 3 — Classifier  ·  ORD-2026-1001", font=fnt["h2"], fill=DARK)
    ty += 56

    checks = [
        "Standard service type", "Property in Florida", "Not a competitor",
        "Not on NEVER_AUTO_QUOTE list", "Not in VE flood zone", "Not Monroe County",
        "Valid property coordinates", "FEMA data available",
        "No missing county", "Not out-of-state", "No competitor email domain",
        "Not ALWAYS_FLAG type", "Value within range", "Valid address format",
    ]
    col_w = (CONTENT_W - tx * 2 - 20) // 2
    col_y = [ty, ty]
    for i, chk in enumerate(checks):
        col = 0 if i % 2 == 0 else 1
        cx2 = tx if col == 0 else tx + col_w + 16
        cy2 = col_y[col]
        draw.rounded_rectangle([cx2, cy2, cx2 + 24, cy2 + 26], radius=4, fill=(220,252,231))
        draw.text((cx2 + 5, cy2 + 4), "✓", font=fnt["tag"], fill=GREEN)
        draw.text((cx2 + 32, cy2 + 5), chk, font=fnt["small"], fill=DARK)
        col_y[col] += 38

    pr_y = max(col_y) + 20
    draw.rounded_rectangle([tx, pr_y, CONTENT_W - 72, pr_y + 72], radius=10, fill=(239,246,255))
    draw.rectangle([tx, pr_y, tx + 7, pr_y + 72], fill=GREEN)
    draw.text((tx + 22, pr_y + 10), "Agent 5 — Pricing Engine", font=fnt["h3"], fill=DARK)
    draw.text((tx + 22, pr_y + 44),
              "FTF API price:  $350.00   ·   Boundary Survey  ·   Status → PRICED",
              font=fnt["body"], fill=GREEN)
    return np.array(img.convert("RGB"))


def slide_human_gate(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Human Approval Gate", 6)

    cx0 = 32; cy0 = HDR_H + 32
    cw = CONTENT_W - 64

    draw.rounded_rectangle([cx0, cy0, cx0+cw, cy0+560], radius=14, fill=WHITE)
    draw.rounded_rectangle([cx0, cy0, cx0+cw, cy0+56], radius=14, fill=(98,100,167))
    draw.text((cx0+20, cy0+16), "Microsoft Teams  —  FTF Invoicing Channel", font=fnt["h3"], fill=WHITE)

    my = cy0 + 70
    draw.rounded_rectangle([cx0+18, my, cx0+cw-18, my+480], radius=10, fill=(245,247,250))
    draw.text((cx0+34, my+16), "FTF Agentic AI OS  ·  10:03 AM", font=fnt["small"], fill=GRAY)

    cy2 = my + 50
    draw.rounded_rectangle([cx0+34, cy2, cx0+cw-34, cy2+400], radius=8, fill=WHITE)
    draw.rectangle([cx0+34, cy2, cx0+44, cy2+400], fill=AMBER)
    draw.text((cx0+58, cy2+18), "Order Requires Human Review — ORD-2026-1002", font=fnt["h3"], fill=DARK)

    facts = [
        ("Service Type", "ALTA Table A Survey",          RED),
        ("Client",       "Coastal Builders LLC",          DARK),
        ("County",       "Monroe (Florida Keys)",         RED),
        ("Estimate",     "$1,725.00",                     DARK),
        ("Flag Reason",  "Monroe County — complex pricing", AMBER),
    ]
    fy = cy2 + 68
    for lbl, val, col in facts:
        draw.text((cx0+64, fy), lbl+":", font=fnt["small"], fill=GRAY)
        draw.text((cx0+290, fy), val, font=fnt["body"], fill=col)
        fy += 50

    draw.rounded_rectangle([cx0+64, fy+16, cx0+600, fy+58], radius=6, fill=(220,252,231))
    draw.text((cx0+80, fy+24), "Robert replied:  approve  →  pipeline resumed",
              font=fnt["body"], fill=(22,101,52))
    return np.array(img.convert("RGB"))


def slide_write_send(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Write · Review · Send", 7)
    img, draw, tx, ty = _white_card(img)

    draw.text((tx, ty), "ORD-2026-1001 — John Martinez", font=fnt["h2"], fill=DARK)
    ty += 56

    ew = CONTENT_W - tx * 2 - 10
    draw.rounded_rectangle([tx, ty, tx+ew, ty+218], radius=8, fill=(248,250,255))
    draw.rounded_rectangle([tx, ty, tx+ew, ty+36],  radius=8, fill=(219,234,254))
    draw.text((tx+16, ty+9),
              "From: estimates@nexgen.enterprises    To: john.martinez@email.com",
              font=fnt["small"], fill=(30,64,175))
    for ln, txt in enumerate([
        "Hi John,",
        "Thank you for reaching out to NexGen Surveying.",
        "Service: Boundary Survey  ·  Property: Hillsborough County  ·  Estimate: $350.00",
    ]):
        draw.text((tx+16, ty+44+ln*42), txt, font=fnt["small"], fill=DARK)
    ty += 236

    draw.text((tx, ty+10), "Agent 7 — 4 Accuracy Checks", font=fnt["h3"], fill=DARK)
    ty += 50
    for chk in ["Price match ($350.00 ✓)", "Client name: John Martinez ✓",
                "Address: Hillsborough County ✓", "Change order clause present ✓"]:
        draw.rounded_rectangle([tx, ty, tx+24, ty+24], radius=4, fill=(220,252,231))
        draw.text((tx+5, ty+4), "✓", font=fnt["tag"], fill=GREEN)
        draw.text((tx+32, ty+4), chk, font=fnt["body"], fill=GREEN)
        ty += 38

    ty += 16
    draw.rounded_rectangle([tx, ty, tx+ew, ty+72], radius=8, fill=(239,246,255))
    draw.text((tx+16, ty+10), "Without LISTEN/NOTIFY:  9:14 AM order → 10:27 AM quote  (73 minutes)",
              font=fnt["small"], fill=GRAY)
    draw.text((tx+16, ty+36), "With LISTEN/NOTIFY (Sprint 9):  order detected → quote sent  < 2 minutes",
              font=fnt["small"], fill=GREEN)
    return np.array(img.convert("RGB"))


def slide_sprint9(fnt: dict) -> np.ndarray:
    """Sprint 9 — Memory Loop + Real-Time Listener architecture slide."""
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Sprint 9 — Memory Loop", 8)

    pad = 36
    x0, y0 = pad, HDR_H + pad
    x1, y1 = CONTENT_W - pad, H - SBTL_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(15, 23, 42, 250))
    draw.rounded_rectangle([x0, y0, x1, y0 + 58], radius=16, fill=(40, 20, 80, 255))
    draw = ImageDraw.Draw(img)
    draw.text((x0+24, y0+16), "SPRINT 9 — MEMORY LOOP  ·  3 NEW COMPONENTS", font=fnt["h3"], fill=(180, 120, 255))

    components = [
        (
            "Agent 0 — Real-Time Listener",
            PURPLE,
            [
                "PostgreSQL NOTIFY fires the instant Agent 2 saves an order",
                "Full pipeline (agents 2–8) runs in < 2 minutes",
                "Before: 60-min wait between every step = 5+ hours",
                "GitHub Actions: listener runs 24/7, restarts every 6 hours",
            ],
        ),
        (
            "Memory Manager — Nightly Log",
            CYAN,
            [
                "Runs at midnight: reads today's 300+ agent decisions",
                "Writes docs/memory/YYYY-MM-DD.md — permanent audit trail",
                "Health dashboard: each agent gets 🟢 🟡 or 🔴 status",
                "Nightly GitHub Actions commit — always up to date",
            ],
        ),
        (
            "Dream Processor — 7-Day Reflection",
            AMBER,
            [
                "Analyzes last 7 days of pipeline decisions",
                "Flags any agent above 10% error rate: NEEDS ATTENTION",
                "Appends to docs/reflection.md — full history preserved",
                "The system monitors its own health, automatically",
            ],
        ),
    ]

    box_h = (y1 - y0 - 68) // 3
    by2 = y0 + 68

    for title, color, bullets in components:
        draw.rounded_rectangle([x0+10, by2+6, x1-10, by2+box_h-6], radius=10,
                                fill=(18, 30, 68))
        draw.rectangle([x0+10, by2+6, x0+18, by2+box_h-6], fill=color)
        draw.text((x0+28, by2+16), title, font=fnt["h3"], fill=color)
        bly = by2 + 52
        for bullet in bullets:
            draw.text((x0+36, bly), "·  " + bullet, font=fnt["small"], fill=(180, 200, 230))
            bly += 30
        by2 += box_h

    return np.array(img.convert("RGB"))


def slide_roadmap(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Sprint 10-12 Roadmap", 9)

    cx0 = 32; cy0 = HDR_H + 32
    cw = CONTENT_W - 64
    draw.rounded_rectangle([cx0, cy0, cx0+cw, cy0+54], radius=12, fill=(20,35,80))
    draw.text((cx0+20, cy0+14), "WHAT COMES NEXT — AND WHAT EACH SPRINT NEEDS",
              font=fnt["h3"], fill=CYAN)

    roadmap = [
        ("Sprint 7",  "AR Follow-Up",       "READY TO BUILD", AMBER, "Needs: Jessica's process recording"),
        ("Sprint 8",  "Monthly Statements",  "READY TO BUILD", AMBER, "Needs: Wyatt + Jessica recording"),
        ("Sprint 10", "Staging Tests",       "MILESTONE",      BLUE,  "Needs: Ryan cost approval + stakeholder demo"),
        ("Sprint 11", "Limited Launch",      "BLOCKED",        GRAY,  "Needs: Sprint 10 + Ryan GO"),
        ("Sprint 12", "Full Production",     "BLOCKED",        GRAY,  "Needs: Sprint 11 + Robert/Mark sign-off"),
    ]
    rh = (H - SBTL_H - cy0 - 64) // len(roadmap)
    ry = cy0 + 60
    for i, (sp, ttl, status, sc, dep) in enumerate(roadmap):
        bg = (18,30,68) if i%2==0 else (14,24,56)
        draw.rectangle([cx0, ry, cx0+cw, ry+rh], fill=bg)
        draw.text((cx0+16, ry+rh//2-11), sp, font=fnt["tag"], fill=GRAY)
        draw.text((cx0+150, ry+rh//2-13), ttl, font=fnt["h3"], fill=WHITE)
        sb  = draw.textbbox((0,0), status, font=fnt["small"])
        bw2 = sb[2]-sb[0]+20
        bx2 = cx0+760
        draw.rounded_rectangle([bx2, ry+rh//2-15, bx2+bw2, ry+rh//2+15], radius=5,
                                fill=(40,55,90) if sc==GRAY else (sc[0]//5, sc[1]//5, sc[2]//5))
        draw.text((bx2+9, ry+rh//2-10), status, font=fnt["small"], fill=sc)
        draw.text((cx0+870+bw2, ry+rh//2-10), dep, font=fnt["small"], fill=(148,163,184))
        ry += rh
    return np.array(img.convert("RGB"))


def slide_outro(fnt: dict) -> np.ndarray:
    return slide_bullets(10, "Sprint 0-9: Complete", [
        ("203 automated tests — all passing", GREEN),
        ("9 AI agents — fully built and tested", GREEN),
        ("8 sprints — delivered on schedule", GREEN),
        ("Orders now process end-to-end in under 2 minutes", GREEN),
        ("System monitors its own health every night", DARK),
        ("Next: Sprints 7 & 8 once Jessica + Wyatt recordings arrive", GRAY),
    ], fnt, "Summary")


def build_all_slides(fnt: dict) -> dict:
    print("  [slides] rendering content panels...")
    s = {}
    s[0]  = slide_intro(fnt)
    s[1]  = slide_bullets(1, "The Manual Process — Before", [
               ("Check Field to Finish for new orders manually",   RED),
               ("Look up price for each service type manually",    RED),
               ("Write estimate email from scratch — every order", RED),
               ("50+ orders/week = hours of work every single day",RED),
               ("Now: fully automated, real-time, zero lag",       GREEN),
           ], fnt, "The Problem")
    s[2]  = slide_pipeline(fnt)
    s[3]  = slide_ftf(fnt, 3)
    s[4]  = slide_bullets(4, "Agent 2 — Monitor", [
               ("Scans Field to Finish every 60 minutes",                  DARK),
               ("Finds ORD-2026-1001: John Martinez, Boundary Survey",     GREEN),
               ("Confirms it has not been processed before",               DARK),
               ("Writes to database — triggers real-time listener",        DARK),
               ("Agent 0 listener wakes up instantly via PostgreSQL NOTIFY",PURPLE),
               ("Your team: zero effort, zero log-ins",                    GREEN),
           ], fnt, "Sprint 1 — Monitor")
    s[5]  = slide_classify(fnt)
    s[6]  = slide_human_gate(fnt)
    s[7]  = slide_write_send(fnt)
    s[8]  = slide_sprint9(fnt)
    s[9]  = slide_roadmap(fnt)
    s[10] = slide_outro(fnt)
    print(f"  {len(s)} slides rendered")
    return s


# ═══════════════════════════════════════════════════════════════════════════
#  FRAME RENDERER
# ═══════════════════════════════════════════════════════════════════════════

_MEASURE_IMG  = Image.new("RGB", (1, 1))
_MEASURE_DRAW = ImageDraw.Draw(_MEASURE_IMG)


def _wrap_text(text: str, font, max_w: int) -> list[str]:
    words, lines, line = text.split(), [], []
    for w in words:
        test = " ".join(line + [w])
        if _MEASURE_DRAW.textbbox((0, 0), test, font=font)[2] > max_w and line:
            lines.append(" ".join(line)); line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return lines


def build_make_frame(
    content_np: np.ndarray,
    sidebar_np: np.ndarray,
    chunks: list[dict],
    fnt: dict,
) -> callable:
    bg = Image.new("RGB", (W, H))
    bg.paste(Image.fromarray(content_np), (CONTENT_X, 0))
    bg.paste(Image.fromarray(sidebar_np), (WORKFLOW_X, 0))
    d = ImageDraw.Draw(bg)
    d.rectangle([0, H - SBTL_H, W, H], fill=(6, 12, 40))
    d.line([0, H - SBTL_H, W, H - SBTL_H], fill=(30, 50, 100), width=1)
    bg_np = np.array(bg)

    sbtl_font = fnt["sbtl"]
    line_h    = 42

    frame_cache: dict[str, np.ndarray] = {}

    def _render_sub(text: str) -> np.ndarray:
        img = Image.fromarray(bg_np)
        d2  = ImageDraw.Draw(img)
        lines   = _wrap_text(text, sbtl_font, CONTENT_W - 120)
        total_h = len(lines) * line_h
        sy = H - SBTL_H + (SBTL_H - total_h) // 2
        for line in lines:
            lb = d2.textbbox((0, 0), line, font=sbtl_font)
            sw = lb[2] - lb[0]
            sx = (CONTENT_W - sw) // 2
            d2.text((sx + 1, sy + 1), line, font=sbtl_font, fill=(0, 0, 20))
            d2.text((sx,     sy),     line, font=sbtl_font, fill=WHITE)
            sy += line_h
        return np.array(img)

    def make_frame(t: float) -> np.ndarray:
        sub = subtitle_at(t, chunks)
        if not sub:
            return bg_np
        if sub not in frame_cache:
            frame_cache[sub] = _render_sub(sub)
        return frame_cache[sub]

    return make_frame


# ═══════════════════════════════════════════════════════════════════════════
#  AUDIO
# ═══════════════════════════════════════════════════════════════════════════

async def _tts(text: str, path: Path) -> float:
    if path.exists():
        c = AudioFileClip(str(path)); d = c.duration; c.close(); return d
    try:
        r = OAI.audio.speech.create(
            model="tts-1-hd", voice="nova",
            input=text, response_format="mp3",
            speed=0.85,
        )
        r.write_to_file(str(path))
    except Exception:
        await edge_tts.Communicate(text, "en-US-JennyNeural").save(str(path))
    c = AudioFileClip(str(path)); d = c.duration; c.close()
    return d


async def generate_all_audio() -> dict:
    print("  [audio] generating TTS narrations (speed=0.85)...")
    result = {}
    for idx, slug, text in SCENES:
        p = AUDIO_DIR / f"s{idx:02d}_{slug}.mp3"
        print(f"    {idx:02d} {slug:<22}", end="", flush=True)
        t0 = time.time()
        dur = await _tts(text, p)
        result[idx] = (p, dur)
        print(f" {dur:.1f}s  ({time.time()-t0:.1f}s)")
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  TRANSCRIPT
# ═══════════════════════════════════════════════════════════════════════════

def write_transcript(audio_map: dict) -> None:
    labels = {
        0: "Introduction", 1: "The Problem", 2: "Pipeline Overview",
        3: "Meet the Order", 4: "Agent 2 — Monitor", 5: "Classify & Price",
        6: "Human Approval Gate", 7: "Write, Review & Send",
        8: "Sprint 9 — Memory Loop", 9: "Sprint 10-12 Roadmap", 10: "Summary",
    }
    lines = [
        "# FTF Agentic AI — Client Demo v5",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d')}  |  **Voice:** OpenAI TTS nova (0.85×)  |  **Sprint 0-9**",
        "", "---", "",
    ]
    t = 0.0
    for idx, slug, narration in SCENES:
        _, dur = audio_map[idx]
        s = int(t); e = int(t + dur)
        mm_s, ss_s = divmod(s, 60); mm_e, ss_e = divmod(e, 60)
        lines += [
            f"## Scene {idx+1} — {labels.get(idx, slug)}  [{mm_s:02d}:{ss_s:02d} – {mm_e:02d}:{ss_e:02d}]",
            "", f"> {narration}", "", "---", "",
        ]
        t += dur + 0.4
    total_mm, total_ss = divmod(int(t), 60)
    lines.insert(1, f"**Total duration:** {total_mm}m {total_ss}s")
    TRANSCRIPT.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [transcript] → {TRANSCRIPT}")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

async def build_video() -> None:
    print("\nNexGen Client Demo v5 — Sprint 0-9 Phase 1 Complete")
    print("=" * 58)
    print(f"Output: {DEMO_DIR}")

    print("\n[1/5] Audio")
    audio_map = await generate_all_audio()

    print("\n[2/5] Word timestamps (Whisper)")
    word_map = {}
    for idx, slug, text in SCENES:
        path, _ = audio_map[idx]
        print(f"  {idx:02d} {slug:<22}", end="", flush=True)
        t0 = time.time()
        words = get_word_timestamps(path, text, f"s{idx:02d}_{slug}")
        word_map[idx] = words
        print(f" {len(words)} words ({time.time()-t0:.1f}s)")

    chunk_map = {idx: make_subtitle_chunks(word_map[idx]) for idx, _, _ in SCENES}

    print("\n[3/5] Slides + Sidebar")
    fnt     = _fonts()
    slides  = build_all_slides(fnt)
    sidebar = build_sidebar_cache(fnt)

    print("\n[4/5] Transcript")
    write_transcript(audio_map)

    print("\n[5/5] Assembling video...")
    clips = []
    for idx, slug, _ in SCENES:
        path, duration = audio_map[idx]
        make_frame = build_make_frame(slides[idx], sidebar[idx], chunk_map[idx], fnt)
        print(f"  scene {idx:02d} {slug:<22} {duration:.1f}s")
        video = VideoClip(make_frame, duration=duration + 0.4)
        audio = AudioFileClip(str(path))
        clips.append(video.with_audio(audio))

    final = concatenate_videoclips(clips, method="compose")
    print(f"\nRendering → {OUTPUT}")
    print(f"Duration:   {final.duration:.0f}s  ({final.duration/60:.1f} min)")
    print("(3-7 minutes at 1920x1080 24fps...)\n")

    final.write_videofile(
        str(OUTPUT), fps=FPS,
        codec="libx264", audio_codec="aac",
        preset="medium", bitrate="6000k",
        logger=None,
    )

    total_dur = final.duration
    for c in clips:
        try: c.close()
        except: pass
    final.close()

    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"\nDone:  {OUTPUT}  ({size_mb:.1f} MB)")
    print(f"Total: {total_dur:.0f}s  ({total_dur/60:.1f} min)")
    print(f"Transcript: {TRANSCRIPT}")


if __name__ == "__main__":
    asyncio.run(build_video())
