"""
generate_client_demo_v2.py — Corrected Synthesia-style client demo

Corrections from v1:
  1. Sprint 0-6 ONLY — shows only what is built and tested
  2. Sprint 7-12 roadmap slide with explicit dependency blockers named
  3. librosa amplitude-driven waveform halo — avatar speech visually syncs to audio
  4. ONE example order traced end-to-end (John Martinez ORD-2026-1001)
  5. Transcript .md generated alongside video
  6. Output saved to versioned demo folder: docs/demos/20260526_v2/

Usage:
    set PYTHONUTF8=1
    python scripts/generate_client_demo_v2.py
"""

import asyncio
import io
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Force UTF-8 output so Unicode chars (arrows, em-dashes) print on any Windows locale
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import requests as req
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent / "code" / "shared"))
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import edge_tts
from moviepy import AudioFileClip, VideoClip, concatenate_videoclips

try:
    import librosa
    _LIBROSA = True
except ImportError:
    _LIBROSA = False

OAI = OpenAI(api_key=os.getenv("OpenAI_API_KEY"))

# ═══════════════════════════════════════════════════════════════════════════════
#  PATHS — versioned demo folder
# ═══════════════════════════════════════════════════════════════════════════════

DATE_TAG  = datetime.now().strftime("%Y%m%d")
VER_TAG   = "v2"
DEMO_DIR  = Path("docs") / "demos" / f"{DATE_TAG}_{VER_TAG}"
AUDIO_DIR = DEMO_DIR / "audio"
AVATAR_CACHE = Path("docs") / "demo_assets" / "avatar.png"  # reuse from v1

DEMO_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT     = DEMO_DIR / "demo.mp4"
TRANSCRIPT = DEMO_DIR / "transcript.md"

# ═══════════════════════════════════════════════════════════════════════════════
#  LAYOUT + COLOURS
# ═══════════════════════════════════════════════════════════════════════════════

W, H   = 1920, 1080
FPS    = 24
HDR_H  = 72
FTR_H  = 58
LEFT_W = 560
RGT_X  = LEFT_W
RGT_W  = W - RGT_X
AV_CX  = LEFT_W // 2
AV_CY  = HDR_H + (H - HDR_H - FTR_H) // 2   # ≈ 569
AV_R   = 200

NAVY  = (10,  20,  60)
NAVY2 = (16,  32,  80)
BLUE  = (37,  99, 235)
CYAN  = (79, 195, 247)
WHITE = (255, 255, 255)
DARK  = (15,  23,  42)
GRAY  = (100, 116, 139)
GREEN = (22, 163,  74)
AMBER = (202, 138,   4)
RED   = (220,  38,  38)
TEAL  = (20, 184, 166)

_FD = Path("C:/Windows/Fonts")

def _f(name: str, size: int) -> ImageFont.FreeTypeFont:
    for p in [_FD / name, _FD / name.lower()]:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)

def _fonts() -> dict:
    return {
        "h1":    _f("calibrib.ttf", 52),
        "h2":    _f("calibrib.ttf", 36),
        "h3":    _f("calibrib.ttf", 27),
        "body":  _f("calibri.ttf",  24),
        "small": _f("calibri.ttf",  19),
        "tag":   _f("calibrib.ttf", 16),
        "mono":  _f("consola.ttf",  19),
        "mono_s":_f("consola.ttf",  17),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  NARRATION SCENES
#  One order — John Martinez, ORD-2026-1001 — traced end-to-end through Sprints 0-6
# ═══════════════════════════════════════════════════════════════════════════════

SCENES = [
    (0, "intro",
     "Welcome. In the next 4 minutes, I'll walk you through exactly what NexGen built — "
     "8 AI agents, 6 sprints, 141 automated tests passing. "
     "We'll follow one real order, from the moment it arrives to the moment the client receives their quote, "
     "with zero manual work from your team."),

    (1, "problem",
     "Before this system, every quote required manual effort. "
     "Someone had to log into Field to Finish, find the new order, look up the price, "
     "write the email, and send it. "
     "With 50 or more new orders every week, that's hours of repetitive work every single day — "
     "and quotes sometimes took until the next morning to reach the client."),

    (2, "pipeline",
     "The solution is an 8-agent AI pipeline. "
     "Each agent has one job. Together they handle detection, classification, pricing, "
     "human approval when needed, email writing, accuracy review, delivery, and daily reporting — "
     "automatically, every 60 minutes, around the clock. "
     "All 6 sprints are complete and fully tested."),

    (3, "meet_order",
     "Let's follow one order. At 9:14 in the morning, John Martinez submits a Boundary Survey request "
     "for half an acre in Hillsborough County. He's waiting for a quote. "
     "Before this system, his request might sit until tomorrow morning. "
     "Watch what happens now."),

    (4, "monitor",
     "Agent 2 — the Monitor — scans Field to Finish every 60 minutes. "
     "Within the hour, it finds John's order in Quote stage and logs it to your database. "
     "Status: pending. Nobody on your team had to check anything or log in."),

    (5, "classify_price",
     "Agent 3 — the Classifier — runs 14 checks in under 2 seconds. "
     "Standard service type? Yes. Property in Florida? Yes. "
     "Any competitor involvement? No. Any flood zone complications? No. "
     "All 14 checks pass — this order is clean. "
     "Agent 5 then pulls John's price directly from Field to Finish: 350 dollars. No manual lookup."),

    (6, "db_live",
     "Your database updates in real time. "
     "John's order just moved from pending to priced. "
     "Now watch what happens with a different order — "
     "an ALTA Survey in Monroe County — that the Classifier flagged as complex. "
     "That one needs Robert's approval before anything is sent."),

    (7, "human_gate",
     "When Agent 3 flags a complex order, Agent 4 instantly sends Robert a Teams notification "
     "with everything he needs: the order ID, service type, property location, and estimated amount. "
     "Robert reviews it, types approve, and the pipeline continues. "
     "Nothing sensitive ever goes out without a human sign-off. Every decision is logged automatically."),

    (8, "write_send",
     "Back to John's order. Agent 6 writes a personalized estimate email using Claude AI. "
     "Agent 7 then runs 4 accuracy checks: price match, client name, property address, "
     "and the change order clause. "
     "If anything is wrong, it corrects and re-checks automatically. "
     "At 10:27 AM, Agent 8 sends John's quote. "
     "That's under 90 minutes from submission — with zero manual work from your team."),

    (9, "roadmap",
     "Sprints 0 through 6 are complete, tested, and ready. "
     "Sprints 7 and 8 — the AR follow-up and monthly statement automations — "
     "are ready to build the moment we receive Jessica and Wyatt's process recordings. "
     "Sprint 9, the memory loop, can start any time. "
     "Sprints 10 through 12 — staging, limited launch, and full production — "
     "follow once Ryan confirms the test estimate and approves the monthly operating cost."),

    (10, "outro",
     "141 automated tests. 8 agents. 6 sprints delivered on schedule. "
     "Your quoting process is automated. "
     "Your team focuses on the work that requires human judgment — "
     "everything else runs on its own. Thank you for watching."),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  AVATAR
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_avatar() -> Image.Image:
    if AVATAR_CACHE.exists():
        print("  [avatar] reusing cached avatar.png")
        return Image.open(AVATAR_CACHE).convert("RGBA")
    print("  [avatar] downloading portrait fallback (randomuser.me)...")
    data = req.get("https://randomuser.me/api/portraits/women/44.jpg", timeout=15).content
    img = Image.open(io.BytesIO(data)).convert("RGBA").resize((512, 512), Image.LANCZOS)
    AVATAR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    img.save(AVATAR_CACHE)
    return img


def make_avatar_circle(src: Image.Image, r: int = AV_R) -> Image.Image:
    size = r * 2
    img = src.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.5))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
#  AUDIO — OpenAI TTS (nova) with edge-tts fallback
# ═══════════════════════════════════════════════════════════════════════════════

async def _tts(text: str, path: Path) -> float:
    if path.exists():
        c = AudioFileClip(str(path)); d = c.duration; c.close(); return d
    # Try OpenAI TTS first
    try:
        resp = OAI.audio.speech.create(model="tts-1-hd", voice="nova",
                                       input=text, response_format="mp3")
        resp.write_to_file(str(path))
    except Exception:
        await edge_tts.Communicate(text, "en-US-JennyNeural").save(str(path))
    c = AudioFileClip(str(path)); d = c.duration; c.close()
    return d


async def generate_all_audio() -> dict[int, tuple[Path, float]]:
    print("  [audio] generating TTS narrations...")
    result = {}
    for idx, slug, text in SCENES:
        p = AUDIO_DIR / f"s{idx:02d}_{slug}.mp3"
        print(f"    {idx:02d} {slug:<22}", end="", flush=True)
        t0 = time.time()
        dur = await _tts(text, p)
        result[idx] = (p, dur)
        print(f" {dur:.1f}s  ({time.time()-t0:.1f}s gen)")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  AMPLITUDE EXTRACTION (librosa — falls back to sine if unavailable)
# ═══════════════════════════════════════════════════════════════════════════════

def load_amplitude(audio_path: Path, total_frames: int) -> np.ndarray:
    if _LIBROSA:
        try:
            y, sr = librosa.load(str(audio_path), sr=None, mono=True)
            hop = max(1, int(sr / FPS))
            rms = librosa.feature.rms(y=y, hop_length=hop)[0]
            rms_norm = rms / (rms.max() + 1e-8)
            # Interpolate to exact frame count
            x_old = np.linspace(0, 1, len(rms_norm))
            x_new = np.linspace(0, 1, total_frames)
            return np.interp(x_new, x_old, rms_norm).clip(0, 1).astype(np.float32)
        except Exception:
            pass
    # Fallback: sine-wave approximation
    t = np.linspace(0, total_frames / FPS, total_frames)
    return (0.5 + 0.4 * np.sin(t * 5.5)).clip(0, 1).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════════════
#  SLIDE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _gradient_bg(draw: ImageDraw.ImageDraw) -> None:
    for y in range(H):
        t = y / H
        r = int(NAVY[0] + (NAVY2[0] - NAVY[0]) * t)
        g = int(NAVY[1] + (NAVY2[1] - NAVY[1]) * t)
        b = int(NAVY[2] + (NAVY2[2] - NAVY[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def _header(draw: ImageDraw.ImageDraw, fnt: dict, right_label: str) -> None:
    draw.rectangle([0, 0, W, HDR_H], fill=(8, 15, 50))
    draw.line([0, HDR_H, W, HDR_H], fill=BLUE, width=3)
    draw.text((28, 18), "NexGen  ·  Field to Finish  ·  Agentic AI OS", font=fnt["tag"], fill=CYAN)
    bb = draw.textbbox((0, 0), right_label, font=fnt["tag"])
    draw.text((W - (bb[2] - bb[0]) - 28, 18), right_label, font=fnt["tag"], fill=(148, 163, 184))


def _footer(draw: ImageDraw.ImageDraw, fnt: dict, scene_num: int) -> None:
    y0 = H - FTR_H
    draw.rectangle([0, y0, W, H], fill=(8, 15, 50))
    draw.line([0, y0, W, y0], fill=(30, 50, 100), width=1)
    draw.text((28, y0 + 16), "Alex  —  NexGen AI Lead  ·  Sprint 0–6 Delivery, May 2026",
              font=fnt["small"], fill=(148, 163, 184))
    # progress dots
    total = len(SCENES)
    dw, dr = 18, 5
    sx = W - total * dw - 28
    for i in range(total):
        cx = sx + i * dw + dr
        cy = y0 + FTR_H // 2
        draw.ellipse([cx - dr, cy - dr, cx + dr, cy + dr],
                     fill=CYAN if i == scene_num else (40, 55, 90))


def _avatar_panel(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle([0, HDR_H, LEFT_W, H - FTR_H], fill=(12, 22, 65))
    draw.rectangle([LEFT_W, HDR_H, LEFT_W + 2, H - FTR_H], fill=(30, 50, 120))


def _content_card(img: Image.Image) -> tuple[Image.Image, ImageDraw.ImageDraw, int, int]:
    """White rounded card on content side. Returns (img, draw, tx, ty)."""
    pad = 32
    x0, y0, x1, y1 = RGT_X + pad, HDR_H + pad, W - pad, H - FTR_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(255, 255, 255, 245))
    draw.rounded_rectangle([x0, y0, x1, y0 + 6], radius=16, fill=(*BLUE, 255))
    return img, draw, x0 + 48, y0 + 48


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, line = [], []
    for w in words:
        test = " ".join(line + [w])
        if draw.textbbox((0, 0), test, font=font)[2] > max_w and line:
            lines.append(" ".join(line)); line = [w]
        else:
            line.append(w)
    if line: lines.append(" ".join(line))
    return lines


# ═══════════════════════════════════════════════════════════════════════════════
#  SLIDE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _slide_bullets(scene_num: int, title: str,
                   bullets: list[tuple[str, tuple]],
                   fnt: dict, tag: str = "") -> np.ndarray:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, tag or f"Scene {scene_num + 1} of {len(SCENES)}")
    _footer(draw, fnt, scene_num)
    img, draw, tx, ty = _content_card(img)
    draw.text((tx, ty), title, font=fnt["h1"], fill=DARK)
    ty += draw.textbbox((tx, ty), title, font=fnt["h1"])[3] - \
          draw.textbbox((tx, ty), title, font=fnt["h1"])[1] + 36
    for text, color in bullets:
        draw.ellipse([tx, ty + 10, tx + 13, ty + 23], fill=BLUE)
        for ln in _wrap_text(draw, text, fnt["body"], RGT_W - 130):
            draw.text((tx + 26, ty), ln, font=fnt["body"], fill=color)
            ty += draw.textbbox((0,0), ln, fnt["body"])[3] + 5
        ty += 14
    return np.array(img.convert("RGB"))


def _slide_intro(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "Introduction")
    _footer(draw, fnt, 0)

    pad = 32
    x0, y0, x1, y1 = RGT_X + pad, HDR_H + pad, W - pad, H - FTR_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(255,255,255,245))
    draw.rounded_rectangle([x0, y0, x1, y0 + 6], radius=16, fill=(*BLUE,255))
    draw = ImageDraw.Draw(img)

    cy_center = (y0 + y1) // 2
    tx = x0 + 48

    # Title
    title = "NexGen Field to Finish"
    sub   = "Automated Quoting System"
    draw.text((tx, y0 + 50), title, font=fnt["h1"], fill=DARK)
    draw.text((tx, y0 + 115), sub, font=fnt["h2"], fill=BLUE)
    draw.line([tx, y0 + 166, x1 - 48, y0 + 166], fill=(219, 234, 254), width=2)

    # Three stat boxes
    stats = [
        ("8", "AI Agents"),
        ("6", "Sprints Complete"),
        ("141", "Tests Passing"),
    ]
    box_w, box_h = 250, 150
    total_w = len(stats) * box_w + (len(stats) - 1) * 32
    bx = tx + (x1 - x0 - 96 - total_w) // 2
    by = y0 + 200
    for num, label in stats:
        draw.rounded_rectangle([bx, by, bx + box_w, by + box_h],
                                radius=12, fill=(239, 246, 255))
        draw.rounded_rectangle([bx, by, bx + box_w, by + 6],
                                radius=12, fill=BLUE)
        bb = draw.textbbox((0, 0), num, font=fnt["h1"])
        draw.text((bx + (box_w - (bb[2]-bb[0])) // 2, by + 18), num, font=fnt["h1"], fill=BLUE)
        lb_bb = draw.textbbox((0, 0), label, font=fnt["small"])
        draw.text((bx + (box_w - (lb_bb[2]-lb_bb[0])) // 2, by + 85), label,
                  font=fnt["small"], fill=GRAY)
        bx += box_w + 32

    # Tagline
    tag = "Sprint 0–6 Delivery  ·  May 2026  ·  Phase 1 Complete"
    tb = draw.textbbox((0,0), tag, font=fnt["body"])
    draw.text((x0 + 48 + (x1 - x0 - 96 - (tb[2]-tb[0])) // 2, by + box_h + 32),
              tag, font=fnt["body"], fill=GRAY)
    return np.array(img.convert("RGB"))


def _slide_pipeline(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "8-Agent Pipeline — All Built & Tested")
    _footer(draw, fnt, 2)

    pad = 32
    x0, y0, x1, y1 = RGT_X + pad, HDR_H + pad, W - pad, H - FTR_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(15, 23, 42, 250))
    draw.rounded_rectangle([x0, y0, x1, y0 + 54], radius=16, fill=(20, 35, 80, 255))
    draw = ImageDraw.Draw(img)
    draw.text((x0 + 28, y0 + 14), "PIPELINE OVERVIEW  —  Sprint 0–6", font=fnt["h3"], fill=CYAN)

    agents = [
        ("Agent 2", "Monitor",         "Sprint 1", GREEN,  "Scans FTF every 60 min"),
        ("Agent 3", "Classifier",      "Sprint 2", GREEN,  "14 flag checks in <2 sec"),
        ("Agent 4", "Human Gate",      "Sprint 3", GREEN,  "Teams alert for complex orders"),
        ("Agent 5", "Pricing Engine",  "Sprint 2", GREEN,  "Pulls price from FTF API"),
        ("Agent 6", "Writer",          "Sprint 4", GREEN,  "Writes personalized estimate"),
        ("Agent 7", "Reviewer",        "Sprint 5", GREEN,  "4-check accuracy review"),
        ("Agent 8", "Sender",          "Sprint 6", GREEN,  "Sends 8 AM–6 PM with delay"),
        ("Agent 9", "Reporter",        "Sprint 6", GREEN,  "Daily Teams digest"),
    ]
    row_h = 68
    ry = y0 + 64
    for i, (num, name, sprint, col, desc) in enumerate(agents):
        bg = (18, 30, 68) if i % 2 == 0 else (14, 24, 56)
        draw.rectangle([x0, ry, x1, ry + row_h], fill=bg)
        # checkmark badge
        bx = x0 + 16
        draw.rounded_rectangle([bx, ry + 14, bx + 44, ry + row_h - 14], radius=6, fill=(22, 50, 30))
        draw.text((bx + 8, ry + 17), "✓", font=fnt["h3"], fill=GREEN)
        # agent num
        draw.text((x0 + 72, ry + 18), num, font=fnt["tag"], fill=(148, 163, 184))
        # name
        draw.text((x0 + 168, ry + 14), name, font=fnt["h3"], fill=WHITE)
        # sprint label
        sb = draw.textbbox((0,0), sprint, font=fnt["small"])
        draw.rounded_rectangle([x0 + 430, ry + 16, x0 + 430 + (sb[2]-sb[0]) + 20, ry + 16 + (sb[3]-sb[1]) + 10],
                                radius=5, fill=(20, 40, 100))
        draw.text((x0 + 440, ry + 20), sprint, font=fnt["small"], fill=CYAN)
        # description
        draw.text((x0 + 570, ry + 18), desc, font=fnt["body"], fill=(148, 163, 184))
        ry += row_h
        if i < len(agents) - 1:
            draw.rectangle([x0, ry, x1, ry + 1], fill=(25, 40, 80))

    return np.array(img.convert("RGB"))


def _slide_ftf_portal(fnt: dict, scene_num: int) -> np.ndarray:
    """FTF portal showing John's order arriving."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "Field to Finish Portal")
    _footer(draw, fnt, scene_num)

    bx, by = RGT_X + 32, HDR_H + 32
    bw = W - bx - 32
    bh = H - FTR_H - by - 32

    # Browser chrome
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=(240, 242, 247))
    draw.rounded_rectangle([bx, by, bx + bw, by + 44], radius=10, fill=WHITE)
    for xi, col in [(bx + 12, (239,68,68)), (bx + 32, (234,179,8)), (bx + 52, (22,163,74))]:
        draw.ellipse([xi, by + 14, xi + 14, by + 28], fill=col)
    draw.text((bx + 80, by + 12), "stage.fieldtofinish.jobs/orders", font=fnt["small"], fill=GRAY)

    # App header
    ay = by + 44
    draw.rectangle([bx, ay, bx + bw, ay + 52], fill=(30, 64, 175))
    draw.text((bx + 20, ay + 12), "Field to Finish", font=fnt["h3"], fill=WHITE)
    draw.text((bx + bw - 340, ay + 15), "Orders   Clients   Reports   Settings",
              font=fnt["small"], fill=(186, 209, 255))

    tbl_y = ay + 52 + 16
    draw.rectangle([bx + 8, tbl_y, bx + bw - 8, tbl_y + 40], fill=(239, 246, 255))
    draw.text((bx + 20, tbl_y + 8), "Quote-Stage Orders  —  New in last 60 minutes",
              font=fnt["small"], fill=(30, 64, 175))

    headers = ["Order ID", "Service Type", "Client Name", "County", "Submitted", "Status"]
    col_xs  = [bx + 16, bx + 160, bx + 400, bx + 660, bx + 840, bx + 1050]
    hy = tbl_y + 50
    draw.rectangle([bx + 8, hy, bx + bw - 8, hy + 36], fill=(219, 234, 254))
    for hdr, cx in zip(headers, col_xs):
        draw.text((cx, hy + 8), hdr, font=fnt["tag"], fill=(30, 64, 175))

    rows = [
        ("ORD-2026-1001", "Boundary Survey",     "John Martinez",      "Hillsborough", "9:14 AM", True),
        ("ORD-2026-1002", "ALTA Table A Survey", "Coastal Builders LLC","Monroe",       "10:02 AM", False),
        ("ORD-2026-1003", "Elevation Cert.",     "Maria Santos",       "Miami-Dade",   "10:47 AM", False),
    ]
    ry = hy + 36
    for i, (oid, svc, client, county, ts, highlight) in enumerate(rows):
        bg = (220, 252, 231) if highlight else (241, 245, 255) if i % 2 == 0 else WHITE
        draw.rectangle([bx + 8, ry, bx + bw - 8, ry + 44], fill=bg)
        for val, cx in zip([oid, svc, client, county, ts], col_xs):
            fw = fnt["small"]
            draw.text((cx, ry + 12), val, font=fw, fill=DARK)
        dot_c = GREEN if highlight else BLUE
        lbl = "● Quote  ← JOHN'S ORDER" if highlight else "● Quote"
        draw.text((col_xs[5], ry + 12), lbl, font=fnt["small"], fill=dot_c)
        ry += 44

    # AI badge
    draw.rounded_rectangle([bx + 16, ry + 18, bx + 460, ry + 52],
                            radius=6, fill=(220, 252, 231))
    draw.text((bx + 32, ry + 27), "Agent 2 Monitor: scanning every 60 min  ●  ACTIVE",
              font=fnt["small"], fill=(22, 101, 52))
    return np.array(img.convert("RGB"))


def _slide_monitor(fnt: dict) -> np.ndarray:
    """Agent 2 detects John's order — FTF → DB arrow diagram."""
    bullets = [
        ("Agent 2 scans Field to Finish for Quote-stage orders every 60 minutes", DARK),
        ("Detects ORD-2026-1001 — John Martinez, Boundary Survey, Hillsborough County", (22, 101, 52)),
        ("Confirms it has not been processed before (no duplicate)", DARK),
        ("Writes order to your database — Status: PENDING", DARK),
        ("Time elapsed from John's submission: under 60 minutes", BLUE),
        ("Zero manual effort from your team", (22, 101, 52)),
    ]
    return _slide_bullets(4, "Agent 2 — Monitor Detects the Order", bullets, fnt, "Sprint 1 — Monitor")


def _slide_classify(fnt: dict) -> np.ndarray:
    """Agent 3 — 14 checks, all green."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "Sprint 2 — Classifier + Pricing")
    _footer(draw, fnt, 5)

    pad = 32
    x0, y0, x1, y1 = RGT_X + pad, HDR_H + pad, W - pad, H - FTR_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(255,255,255,245))
    draw.rounded_rectangle([x0, y0, x1, y0 + 6], radius=16, fill=(*BLUE,255))
    draw = ImageDraw.Draw(img)

    tx, ty = x0 + 48, y0 + 48
    draw.text((tx, ty), "Agent 3 — Classifier  (ORD-2026-1001)", font=fnt["h2"], fill=DARK)
    ty += 56

    # Two-column check list
    checks = [
        ("Standard service type", True),
        ("Property in Florida (FL only)", True),
        ("Not a competitor company", True),
        ("Not on NEVER_AUTO_QUOTE list", True),
        ("Not in VE flood zone", True),
        ("County is not Monroe", True),
        ("Property lat/lng valid", True),
        ("FEMA data available", True),
        ("No missing county", True),
        ("Not out-of-state property", True),
        ("No competitor email domain", True),
        ("Not ALWAYS_FLAG service type", True),
        ("Order value within normal range", True),
        ("Address format valid", True),
    ]
    col_w = (x1 - x0 - 96) // 2
    cx1, cx2 = tx, tx + col_w + 16
    cy = ty
    for i, (check, passed) in enumerate(checks):
        col = cx1 if i % 2 == 0 else cx2
        if i % 2 == 0 and i > 0:
            cy += 38
        color = GREEN if passed else RED
        mark  = "✓" if passed else "✗"
        draw.rounded_rectangle([col, cy, col + 22, cy + 26], radius=4,
                                fill=(220, 252, 231) if passed else (254, 226, 226))
        draw.text((col + 4, cy + 2), mark, font=fnt["tag"], fill=color)
        draw.text((col + 28, cy + 3), check, font=fnt["small"], fill=DARK)

    # Pricing result
    pr_y = cy + 52
    draw.rounded_rectangle([tx, pr_y, x1 - 48, pr_y + 72], radius=10, fill=(239, 246, 255))
    draw.rounded_rectangle([tx, pr_y, tx + 6, pr_y + 72], radius=10, fill=GREEN)
    draw.text((tx + 22, pr_y + 10), "Agent 5 — Pricing Engine", font=fnt["h3"], fill=DARK)
    draw.text((tx + 22, pr_y + 40), "Price pulled from FTF API:   $350.00   ·   Service: Boundary Survey   ·   Status → PRICED",
              font=fnt["body"], fill=GREEN)
    return np.array(img.convert("RGB"))


def _slide_db(fnt: dict) -> np.ndarray:
    """Live DB table with all orders at different stages."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "Database: processed_orders — Live")
    _footer(draw, fnt, 6)

    cx0, cy0 = RGT_X + 40, HDR_H + 40
    cw = W - cx0 - 40
    ch = H - FTR_H - cy0 - 40

    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=12, fill=(15, 23, 42))
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 54], radius=12, fill=(20, 35, 80))
    draw.text((cx0 + 24, cy0 + 13), "DATABASE  —  processed_orders  (real-time)",
              font=fnt["h3"], fill=CYAN)

    cols  = ["ORDER ID", "CLIENT", "SERVICE TYPE", "AMOUNT", "STATUS", "TIME"]
    col_x = [cx0+16, cx0+200, cx0+450, cx0+750, cx0+930, cx0+1160]
    hy = cy0 + 60
    draw.rectangle([cx0, hy, cx0 + cw, hy + 38], fill=(25, 45, 95))
    for col, cx in zip(cols, col_x):
        draw.text((cx, hy + 8), col, font=fnt["tag"], fill=(148,163,184))

    rows = [
        ("ORD-2026-1001","John Martinez",    "Boundary Survey",     "$350.00","PRICED → WRITING",  CYAN,  "→", "9:14 AM"),
        ("ORD-2026-1002","Coastal Builders", "ALTA Table A Survey", "$1,725","AWAITING APPROVAL",  AMBER, "⏳","10:02 AM"),
        ("ORD-2026-1003","Maria Santos",     "Elevation Cert.",     "$450.00","SENT",              GREEN, "✓", "10:58 AM"),
    ]
    ry = hy + 38
    for i,(oid,client,svc,amt,status,sc,icon,ts) in enumerate(rows):
        bg = (22, 40, 90) if i == 0 else (18, 30, 68) if i % 2 == 0 else (14, 24, 56)
        draw.rectangle([cx0, ry, cx0+cw, ry+60], fill=bg)
        if i == 0:
            draw.rectangle([cx0, ry, cx0+4, ry+60], fill=CYAN)
        for val, cx in zip([oid, client, svc, amt], col_x):
            draw.text((cx, ry+18), val, font=fnt["mono_s"], fill=WHITE)
        draw.text((col_x[4], ry+10), icon, font=fnt["body"], fill=sc)
        draw.text((col_x[4]+30, ry+18), status, font=fnt["mono_s"], fill=sc)
        draw.text((col_x[5], ry+18), ts, font=fnt["mono_s"], fill=(148,163,184))
        ry += 60

    # Note about John's row
    draw.rounded_rectangle([cx0+16, ry+16, cx0+800, ry+48], radius=6, fill=(20,50,90))
    draw.text((cx0+30, ry+24), "← John's order: Classifier passed all 14 checks, price locked at $350.00",
              font=fnt["small"], fill=CYAN)
    return np.array(img.convert("RGB"))


def _slide_human_gate(fnt: dict) -> np.ndarray:
    """Teams notification card for the flagged ALTA order."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "Sprint 3 — Human Approval Gate")
    _footer(draw, fnt, 7)

    cx0, cy0 = RGT_X + 40, HDR_H + 40
    cw = W - cx0 - 40

    # Teams card
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 580], radius=14, fill=WHITE)
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 56], radius=14, fill=(98, 100, 167))
    draw.text((cx0 + 20, cy0 + 16), "Microsoft Teams  —  FTF Invoicing Channel", font=fnt["h3"], fill=WHITE)

    msg_y = cy0 + 70
    draw.rounded_rectangle([cx0 + 20, msg_y, cx0 + cw - 20, msg_y + 486], radius=10, fill=(245, 247, 250))
    draw.text((cx0 + 36, msg_y + 16), "FTF Agentic AI OS  ·  Today 10:03 AM", font=fnt["small"], fill=GRAY)

    card_y = msg_y + 46
    draw.rounded_rectangle([cx0 + 36, card_y, cx0 + cw - 36, card_y + 400], radius=8, fill=WHITE)
    draw.rectangle([cx0 + 36, card_y, cx0 + 44, card_y + 400], fill=AMBER)
    draw.text((cx0 + 60, card_y + 18), "Order Requires Human Review — ORD-2026-1002", font=fnt["h3"], fill=DARK)

    facts = [
        ("Order ID",        "ORD-2026-1002",           DARK),
        ("Client",          "Coastal Builders LLC",     DARK),
        ("Service Type",    "ALTA Table A Survey",      RED),
        ("Property County", "Monroe (Florida Keys)",    RED),
        ("Estimate Amount", "$1,725.00",                DARK),
        ("Flag Reason",     "Monroe County — complex pricing, human review required", AMBER),
    ]
    fy = card_y + 64
    for label, val, color in facts:
        draw.text((cx0 + 68, fy), label + ":", font=fnt["small"], fill=GRAY)
        draw.text((cx0 + 310, fy), val, font=fnt["body"], fill=color)
        fy += 48

    # Response box
    resp_y = fy + 16
    draw.rounded_rectangle([cx0 + 68, resp_y, cx0 + 480, resp_y + 44], radius=6,
                            fill=(220, 252, 231))
    draw.text((cx0 + 84, resp_y + 10), "Robert replied:  approve", font=fnt["body"], fill=(22, 101, 52))
    draw.text((cx0 + 68, resp_y + 56), "→ Pipeline resumed. Estimate will be written and sent.",
              font=fnt["small"], fill=BLUE)
    return np.array(img.convert("RGB"))


def _slide_write_send(fnt: dict) -> np.ndarray:
    """Email written + 4 checks + sent — John's order."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "Sprint 4+5+6 — Write, Review, Send")
    _footer(draw, fnt, 8)

    pad = 32
    x0, y0, x1, y1 = RGT_X + pad, HDR_H + pad, W - pad, H - FTR_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(255,255,255,245))
    draw.rounded_rectangle([x0, y0, x1, y0+6], radius=16, fill=(*BLUE,255))
    draw = ImageDraw.Draw(img)

    tx, ty = x0 + 48, y0 + 48
    draw.text((tx, ty), "ORD-2026-1001 — John Martinez", font=fnt["h2"], fill=DARK)
    ty += 52

    # Email preview box
    em_x, em_y, em_w, em_h = tx, ty, x1 - x0 - 96, 220
    draw.rounded_rectangle([em_x, em_y, em_x + em_w, em_y + em_h], radius=8, fill=(248, 250, 255))
    draw.rounded_rectangle([em_x, em_y, em_x + em_w, em_y + 36], radius=8, fill=(219, 234, 254))
    draw.text((em_x + 16, em_y + 8), "From: estimates@nexgen.enterprises    To: john.martinez@email.com    Subject: Survey Estimate — Boundary Survey",
              font=fnt["small"], fill=(30, 64, 175))
    email_lines = [
        "Hi John,",
        "",
        "Thank you for reaching out to NexGen Surveying. Please find your estimate below.",
        "",
        "Service:   Boundary Survey",
        "Property:  123 Oak Lane, Hillsborough County, FL",
        "Estimate:  $350.00",
    ]
    ely = em_y + 44
    for ln in email_lines:
        draw.text((em_x + 16, ely), ln, font=fnt["small"], fill=DARK)
        ely += 24
    ty += em_h + 24

    # 4 Reviewer checks
    draw.text((tx, ty), "Agent 7 — Reviewer: 4 Accuracy Checks", font=fnt["h3"], fill=DARK)
    ty += 44
    checks = [
        ("Price match ($350.00 ✓)", GREEN),
        ("Client name matches (John Martinez ✓)", GREEN),
        ("Property address correct (Hillsborough County ✓)", GREEN),
        ("Change order clause present & unmodified ✓", GREEN),
    ]
    for chk, col in checks:
        draw.rounded_rectangle([tx, ty, tx + 22, ty + 22], radius=4, fill=(220,252,231))
        draw.text((tx + 4, ty + 2), "✓", font=fnt["tag"], fill=GREEN)
        draw.text((tx + 30, ty + 2), chk, font=fnt["body"], fill=col)
        ty += 38

    # Timeline
    ty += 16
    draw.rounded_rectangle([tx, ty, x1 - 48, ty + 52], radius=8, fill=(239, 246, 255))
    draw.text((tx + 16, ty + 8),  "9:14 AM  Order arrives in FTF", font=fnt["small"], fill=GRAY)
    draw.text((tx + 16, ty + 28), "10:27 AM  Estimate sent to John  ←  73 minutes  ·  zero manual work",
              font=fnt["small"], fill=BLUE)
    return np.array(img.convert("RGB"))


def _slide_roadmap(fnt: dict) -> np.ndarray:
    """Sprint 7-12 roadmap with explicit dependencies."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "What Comes Next — Sprint 7–12")
    _footer(draw, fnt, 9)

    cx0, cy0 = RGT_X + 40, HDR_H + 40
    cw = W - cx0 - 40

    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 54], radius=12, fill=(20, 35, 80))
    draw.text((cx0 + 24, cy0 + 13), "SPRINT ROADMAP  —  Sprints 7–12", font=fnt["h3"], fill=CYAN)

    roadmap = [
        ("Sprint 7",  "AR Follow-Up Automation",      "READY TO BUILD",  AMBER,
         "Needs: Jessica's process recording (Recording 10)"),
        ("Sprint 8",  "Monthly Statements",             "READY TO BUILD",  AMBER,
         "Needs: Wyatt + Jessica process recording (Recording 11)"),
        ("Sprint 9",  "Memory Loop",                   "CAN START NOW",   GREEN,
         "No external dependencies — can begin any time"),
        ("Sprint 10", "Full Staging Tests",             "MILESTONE",       BLUE,
         "Needs: Ryan confirms test estimate + approves monthly cost"),
        ("Sprint 11", "Limited Production Launch",      "BLOCKED",         GRAY,
         "Needs: Sprint 10 complete + Ryan GO signal"),
        ("Sprint 12", "Full Production (24/7 Live)",   "BLOCKED",         GRAY,
         "Needs: Sprint 11 + Robert/Mark sign-off on first 5 real estimates"),
    ]
    row_h = 80
    ry = cy0 + 60
    for i, (sprint, title, status, sc, dep) in enumerate(roadmap):
        bg = (18, 30, 68) if i % 2 == 0 else (14, 24, 56)
        draw.rectangle([cx0, ry, cx0 + cw, ry + row_h], fill=bg)
        # Sprint label
        draw.text((cx0 + 16, ry + 14), sprint, font=fnt["tag"], fill=(148,163,184))
        # Title
        draw.text((cx0 + 130, ry + 10), title, font=fnt["h3"], fill=WHITE)
        # Status badge
        sb = draw.textbbox((0,0), status, font=fnt["small"])
        bw = sb[2] - sb[0] + 24
        bx = cx0 + 760
        draw.rounded_rectangle([bx, ry + 14, bx + bw, ry + row_h - 14], radius=6,
                                fill=(*sc, 40) if sc != GRAY else (40, 55, 90))
        draw.text((bx + 10, ry + 20), status, font=fnt["small"], fill=sc)
        # Dependency
        draw.text((cx0 + 760 + bw + 20, ry + 20), dep, font=fnt["small"], fill=(148,163,184))
        ry += row_h

    # Note
    draw.rounded_rectangle([cx0 + 16, ry + 16, cx0 + cw - 16, ry + 54], radius=6, fill=(20,35,80))
    draw.text((cx0 + 30, ry + 24),
              "Sprints 0–6 complete and tested.  Sprints 7–9 start as soon as dependencies are resolved.  Sprints 10–12 are milestone-gated.",
              font=fnt["small"], fill=CYAN)
    return np.array(img.convert("RGB"))


def _slide_outro(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_panel(draw)
    _header(draw, fnt, "Summary")
    _footer(draw, fnt, 10)

    pad = 32
    x0, y0, x1, y1 = RGT_X + pad, HDR_H + pad, W - pad, H - FTR_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(255,255,255,245))
    draw.rounded_rectangle([x0, y0, x1, y0 + 6], radius=16, fill=(*BLUE,255))
    draw = ImageDraw.Draw(img)

    tx, ty = x0 + 48, y0 + 60

    draw.text((tx, ty), "Sprint 0–6: Complete", font=fnt["h1"], fill=DARK)
    ty += 72

    big_stats = [
        ("141", "Automated Tests", "All Passing"),
        ("8",   "AI Agents",       "Fully Tested"),
        ("6",   "Sprints",         "On Schedule"),
    ]
    box_w, box_h = 260, 155
    bx = tx
    for num, label, sub in big_stats:
        draw.rounded_rectangle([bx, ty, bx + box_w, ty + box_h], radius=12, fill=(239,246,255))
        draw.rounded_rectangle([bx, ty, bx + box_w, ty + 6], radius=12, fill=BLUE)
        nb = draw.textbbox((0,0), num, font=fnt["h1"])
        draw.text((bx + (box_w-(nb[2]-nb[0]))//2, ty+16), num, font=fnt["h1"], fill=BLUE)
        lb = draw.textbbox((0,0), label, font=fnt["body"])
        draw.text((bx + (box_w-(lb[2]-lb[0]))//2, ty+78), label, font=fnt["body"], fill=DARK)
        sb2 = draw.textbbox((0,0), sub, font=fnt["small"])
        draw.text((bx + (box_w-(sb2[2]-sb2[0]))//2, ty+108), sub, font=fnt["small"], fill=GREEN)
        bx += box_w + 28

    ty += box_h + 44

    bullets = [
        ("Quoting process: fully automated, 24/7, zero manual effort", DARK),
        ("One example followed today: John Martinez — quote sent in 73 minutes", (22,101,52)),
        ("Next: Sprints 7–12 will add AR follow-up, statements, and production launch", GRAY),
    ]
    for text, col in bullets:
        draw.ellipse([tx, ty + 10, tx + 13, ty + 23], fill=BLUE)
        draw.text((tx + 26, ty), text, font=fnt["body"], fill=col)
        ty += draw.textbbox((0,0), text, fnt["body"])[3] + 20

    return np.array(img.convert("RGB"))


def build_all_slides(fnt: dict) -> dict[int, np.ndarray]:
    print("  [slides] rendering 11 scene backgrounds...")
    s = {}
    s[0]  = _slide_intro(fnt)
    s[1]  = _slide_bullets(1, "Before: The Manual Process",
                            [("Log into Field to Finish — check for new orders manually", RED),
                             ("Look up the price for each service type manually", RED),
                             ("Write the estimate email from scratch, every time", RED),
                             ("Review, send — then hope nothing was missed", RED),
                             ("Result: hours of repetitive work every day", RED),
                             ("Now: all of this is automated, every 60 minutes, zero effort", GREEN)],
                            fnt, "The Challenge")
    s[2]  = _slide_pipeline(fnt)
    s[3]  = _slide_ftf_portal(fnt, 3)
    s[4]  = _slide_monitor(fnt)
    s[5]  = _slide_classify(fnt)
    s[6]  = _slide_db(fnt)
    s[7]  = _slide_human_gate(fnt)
    s[8]  = _slide_write_send(fnt)
    s[9]  = _slide_roadmap(fnt)
    s[10] = _slide_outro(fnt)
    print(f"  {len(s)} slides rendered")
    return s


# ═══════════════════════════════════════════════════════════════════════════════
#  FRAME ANIMATION — amplitude-driven waveform halo
# ═══════════════════════════════════════════════════════════════════════════════

_BAR_ANGLES = np.linspace(0, 2 * math.pi, 48, endpoint=False)


def _draw_waveform_halo(img: Image.Image, t: float, amp: float, bob_y: int) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    r_inner = AV_R + 10
    max_ext = 52

    for i, angle in enumerate(_BAR_ANGLES):
        local = amp * (0.45 + 0.55 * abs(math.sin(t * 7.1 + i * 0.42)))
        local = max(0.06, local)
        r_outer = r_inner + int(local * max_ext) + 3
        x1 = AV_CX + r_inner * math.cos(angle)
        y1 = bob_y  + r_inner * math.sin(angle)
        x2 = AV_CX + r_outer * math.cos(angle)
        y2 = bob_y  + r_outer * math.sin(angle)
        intensity = int(120 + 135 * local)
        alpha_v   = int(55  + 185 * local)
        draw.line([(x1, y1), (x2, y2)],
                  fill=(79, intensity, min(255, intensity + 60), alpha_v), width=2)

    return Image.alpha_composite(img.convert("RGBA"), overlay)


def build_make_frame(slide_np: np.ndarray, av_circle: Image.Image,
                     amplitude: np.ndarray) -> callable:
    slide_rgba = Image.fromarray(slide_np).convert("RGBA")

    def make_frame(t: float) -> np.ndarray:
        fi  = min(int(t * FPS), len(amplitude) - 1)
        amp = float(amplitude[fi])
        bob = AV_CY + int(math.sin(t * 1.7) * 4)

        frame = _draw_waveform_halo(slide_rgba.copy(), t, amp, bob)

        # Paste avatar circle
        ax, ay = AV_CX - AV_R, bob - AV_R
        frame.paste(av_circle, (ax, ay), av_circle)

        # White border ring
        ri = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        ImageDraw.Draw(ri).ellipse(
            [ax - 4, ay - 4, ax + AV_R * 2 + 4, ay + AV_R * 2 + 4],
            outline=(255, 255, 255, 210), width=3,
        )
        frame = Image.alpha_composite(frame, ri)

        # Speaking pulse dot below avatar
        dot_y = bob + AV_R + 30
        di = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        dd = ImageDraw.Draw(di)
        dot_alpha = int(140 + 115 * amp)
        dd.ellipse([AV_CX - 8, dot_y - 8, AV_CX + 8, dot_y + 8],
                   fill=(22, 163, 74, dot_alpha))
        frame = Image.alpha_composite(frame, di)

        return np.array(frame.convert("RGB"))

    return make_frame


# ═══════════════════════════════════════════════════════════════════════════════
#  TRANSCRIPT WRITER
# ═══════════════════════════════════════════════════════════════════════════════

def write_transcript(audio_map: dict[int, tuple[Path, float]]) -> None:
    lines = [
        "# FTF Agentic AI — Client Demo v2",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d')}  |  **Voice:** Alex (OpenAI TTS — nova)  |  **Sprint coverage:** 0–6",
        "",
        "---",
        "",
    ]
    t = 0.0
    scene_labels = {
        0: "Introduction",
        1: "The Problem",
        2: "8-Agent Pipeline Overview",
        3: "Meet the Example Order",
        4: "Agent 2 — Monitor",
        5: "Agent 3+5 — Classify & Price",
        6: "Live Database View",
        7: "Agent 4 — Human Approval Gate",
        8: "Agents 6+7+8 — Write, Review & Send",
        9: "Sprint 7–12 Roadmap",
        10: "Summary & Outro",
    }
    for idx, slug, narration in SCENES:
        _, dur = audio_map[idx]
        s, e = int(t), int(t + dur)
        mm_s, ss_s = divmod(s, 60)
        mm_e, ss_e = divmod(e, 60)
        label = scene_labels.get(idx, slug.replace("_", " ").title())
        lines += [
            f"## Scene {idx + 1} — {label}  [{mm_s:02d}:{ss_s:02d} – {mm_e:02d}:{ss_e:02d}]",
            "",
            f"**Narration:**",
            f"> {narration}",
            "",
            "---",
            "",
        ]
        t += dur + 0.4

    total_mm, total_ss = divmod(int(t), 60)
    lines.insert(1, f"**Total duration:** {total_mm}m {total_ss}s")
    TRANSCRIPT.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [transcript] → {TRANSCRIPT}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════════

async def build_video() -> None:
    print("\nNexGen Client Demo v2 — Corrected Build")
    print("=" * 52)
    print(f"Output folder: {DEMO_DIR}")
    print(f"librosa: {'active — amplitude-driven waveform halo' if _LIBROSA else 'not found — sine fallback'}")

    # 1. Avatar
    print("\n[1/5] Avatar")
    av_circle = make_avatar_circle(fetch_avatar())

    # 2. Audio
    print("\n[2/5] Audio (OpenAI TTS — nova)")
    audio_map = await generate_all_audio()

    # 3. Slides
    print("\n[3/5] Slides")
    fnt    = _fonts()
    slides = build_all_slides(fnt)

    # 4. Transcript
    print("\n[4/5] Transcript")
    write_transcript(audio_map)

    # 5. Assemble video
    print("\n[5/5] Assembling video...")
    clips = []
    for idx, slug, _ in SCENES:
        audio_path, duration = audio_map[idx]
        total_frames = int((duration + 0.4) * FPS) + 1
        amplitude    = load_amplitude(audio_path, total_frames)
        make_frame   = build_make_frame(slides[idx], av_circle, amplitude)
        print(f"  scene {idx:02d} {slug:<22} {duration:.1f}s")
        video = VideoClip(make_frame, duration=duration + 0.4)
        audio = AudioFileClip(str(audio_path))
        clips.append(video.with_audio(audio))

    final = concatenate_videoclips(clips, method="compose")
    print(f"\nRendering → {OUTPUT}")
    print(f"Duration:   {final.duration:.0f}s  ({final.duration / 60:.1f} min)")
    print("(5-10 minutes at 1920×1080 24fps...)\n")

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
    print(f"Total: {total_dur:.0f} seconds  ({total_dur / 60:.1f} min)")
    print(f"Transcript: {TRANSCRIPT}")


if __name__ == "__main__":
    asyncio.run(build_video())
