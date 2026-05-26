"""
generate_client_demo_v3.py — Client demo v3

Improvements over v2:
  1. Animated 2D female avatar — PIL-drawn face with:
       - 4 mouth states driven by librosa amplitude (lip-sync)
       - Eye blinking every 3-5 seconds
       - Eyebrow microexpressions on amplitude spikes
       - 12 pre-rendered face states cached at startup (perf)
  2. Persistent workflow sidebar — always-visible right panel:
       - Sprint 0-6: GREEN ✓ (complete)
       - Sprint 7-12: RED ✗ (remaining + dependency)
       - Active sprint for current scene highlighted
  3. Word-reveal subtitle bar — narration text appears word-by-word
       at bottom synced with audio (Whisper word timestamps, cached)
  4. Content-first layout (HeyGen/Synthesia pattern):
       - Avatar: LEFT 460px  — large enough to see expressions clearly
       - Content: CENTER 1020px — primary visual
       - Workflow: RIGHT 440px — always visible
  5. Shorter, tighter scenes (~2.5 min total for non-technical audience)

Output: docs/demos/YYYYMMDD_v3/demo.mp4 + transcript.md

Usage:
    set PYTHONUTF8=1
    python scripts/generate_client_demo_v3.py
"""

import asyncio
import io
import json
import math
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

# UTF-8 stdout — prevents UnicodeEncodeError on Windows for arrows/em-dashes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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
#  PATHS
# ═══════════════════════════════════════════════════════════════════════════════

DATE_TAG  = datetime.now().strftime("%Y%m%d")
DEMO_DIR  = Path("docs") / "demos" / f"{DATE_TAG}_v3"
AUDIO_DIR = DEMO_DIR / "audio"
TS_DIR    = DEMO_DIR / "timestamps"   # Whisper word-timestamp JSON cache
AVATAR_CACHE = Path("docs") / "demo_assets" / "avatar.png"

for d in [DEMO_DIR, AUDIO_DIR, TS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

OUTPUT     = DEMO_DIR / "demo.mp4"
TRANSCRIPT = DEMO_DIR / "transcript.md"

# ═══════════════════════════════════════════════════════════════════════════════
#  LAYOUT — content-first (HeyGen/Synthesia pattern)
# ═══════════════════════════════════════════════════════════════════════════════

W, H        = 1920, 1080
FPS         = 24
HDR_H       = 68
FTR_H       = 0          # no footer — subtitle bar replaces it
SBTL_H      = 72         # subtitle bar height at bottom
LEFT_W      = 460        # avatar panel
WORKFLOW_W  = 420        # right workflow sidebar
CONTENT_W   = W - LEFT_W - WORKFLOW_W   # = 1040
CONTENT_X   = LEFT_W
WORKFLOW_X  = LEFT_W + CONTENT_W

AV_R        = 185        # avatar circle radius — 370px diameter (lips clearly visible)
AV_CX       = LEFT_W // 2
AV_CY       = HDR_H + (H - HDR_H - SBTL_H) // 2   # center of avatar panel

# ── Colours ───────────────────────────────────────────────────────────────────
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
TEAL   = (20, 184, 166)
RING   = (99, 179, 255)

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
        "sbtl":  _f("calibri.ttf",  21),
        "wf":    _f("calibrib.ttf", 13),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  SCENES — tighter narration (~2.5 min total for non-technical client)
# ═══════════════════════════════════════════════════════════════════════════════

SCENES = [
    (0,  "intro",
     "Welcome. Let me show you exactly what NexGen built — "
     "8 AI agents that automate your entire quoting process. "
     "We'll follow one real order, start to finish."),

    (1,  "problem",
     "Before: your team had to manually check Field to Finish for new orders, "
     "look up the price, write the email, and send it. "
     "50 new orders a week — hours of repetitive work every day."),

    (2,  "pipeline",
     "The solution: 8 AI agents running every 60 minutes, around the clock. "
     "Detect, classify, price, approve if needed, write, review, send, report. "
     "All 6 sprints are built, tested, and ready."),

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
     "At 10:27 AM, Agent 8 sends the quote. "
     "73 minutes from submission. Zero manual work."),

    (8,  "roadmap",
     "Sprints 0 through 6 are complete. "
     "Sprint 7 and 8 need Jessica and Wyatt's process recordings. "
     "Sprint 9 can start now. "
     "Sprints 10 through 12 follow once Ryan approves the monthly cost."),

    (9,  "outro",
     "141 automated tests. 8 agents. 6 sprints, on schedule. "
     "Your quoting process runs automatically. "
     "Your team focuses on the work that needs a human. Thank you."),
]

# Which sprint(s) to highlight in the sidebar for each scene
SCENE_SPRINTS = {
    0: [],
    1: [],
    2: list(range(7)),
    3: [1],
    4: [1],
    5: [2],
    6: [3],
    7: [4, 5, 6],
    8: list(range(7, 13)),
    9: list(range(7)),
}

SPRINT_LABELS = [
    (0,  "Foundation",       True),
    (1,  "Monitor",          True),
    (2,  "Classifier",       True),
    (3,  "Human Gate",       True),
    (4,  "Writer",           True),
    (5,  "Reviewer",         True),
    (6,  "Sender",           True),
    (7,  "AR Follow-Up",     False),
    (8,  "Statements",       False),
    (9,  "Memory Loop",      False),
    (10, "Staging Tests",    False),
    (11, "Limited Launch",   False),
    (12, "Full Production",  False),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  ANIMATED 2D FACE
#  Pre-rendered in 12 states: 4 mouth × 3 blink levels
#  Drawn at 800×800, scaled to 400×400 for anti-aliasing
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_face_raw(mouth: int, blink: int, eyebrow_raise: float = 0.0) -> Image.Image:
    """
    Draw a professional 2D animated female avatar at 800×800.
    mouth: 0=closed smile, 1=slight open, 2=medium, 3=wide
    blink: 0=open, 1=half-closed, 2=closed
    eyebrow_raise: 0.0-1.0
    """
    S = 800
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx  = S // 2   # 400

    # Palette
    SKIN      = (255, 218, 185)
    SKIN_SH   = (225, 175, 140)
    HAIR      = (45, 28, 14)
    HAIR_HI   = (70, 45, 22)
    BLAZER    = (30, 50, 120)
    SHIRT     = (240, 245, 255)
    BROW_C    = (55, 35, 15)
    EYE_WHITE = (255, 255, 255)
    IRIS_C    = (70, 105, 170)
    PUPIL_C   = (20, 15, 10)
    LIP_UP    = (205, 85, 80)
    LIP_LO    = (215, 100, 90)
    TEETH_C   = (248, 248, 248)
    MOUTH_IN  = (90, 35, 30)
    BLUSH_C   = (255, 145, 130, 55)

    # ── Hair (behind everything) ─────────────────────────────────────────
    d.ellipse([cx-230, 40, cx+230, 360], fill=HAIR)          # main mass
    d.ellipse([cx-240, 140, cx-95,  680], fill=HAIR)         # left side
    d.ellipse([cx+95,  140, cx+240, 680], fill=HAIR)         # right side
    d.ellipse([cx-55,  38, cx+55, 165],   fill=HAIR_HI)      # part highlight

    # ── Face oval ────────────────────────────────────────────────────────
    d.ellipse([cx-192, 90, cx+192, 590], fill=SKIN)

    # ── Chin jaw shadow ──────────────────────────────────────────────────
    d.ellipse([cx-120, 480, cx+120, 620], fill=SKIN_SH)
    d.ellipse([cx-190, 420, cx+190, 610], fill=SKIN)         # re-draw face over

    # ── Neck ─────────────────────────────────────────────────────────────
    d.rectangle([cx-58, 570, cx+58, 700], fill=SKIN)
    d.rectangle([cx-40, 570, cx+40, 720], fill=SKIN)

    # ── Shoulders / blazer ───────────────────────────────────────────────
    d.polygon([(cx-280, 800), (cx-80, 600), (cx-55, 580),
               (cx+55, 580), (cx+80, 600), (cx+280, 800)],
              fill=BLAZER)
    # Shirt collar V
    d.polygon([(cx-35, 590), (cx, 680), (cx+35, 590),
               (cx+28, 720), (cx, 740), (cx-28, 720)],
              fill=SHIRT)

    # ── Ears ─────────────────────────────────────────────────────────────
    d.ellipse([cx-210, 275, cx-168, 360], fill=SKIN)
    d.ellipse([cx+168, 275, cx+210, 360], fill=SKIN)

    # ── Eyebrows ─────────────────────────────────────────────────────────
    br_off = -int(eyebrow_raise * 14)
    for sign in [-1, 1]:
        ex0 = cx + sign * (50 if sign < 0 else 50)
        bx0 = cx - 168 if sign < 0 else cx + 70
        bx1 = cx - 68  if sign < 0 else cx + 168
        by0 = 243 + br_off
        by1 = 258 + br_off
        d.arc([bx0, by0 - 18, bx1, by1 + 10], 200, 340, fill=BROW_C, width=8)

    # ── Eyes ─────────────────────────────────────────────────────────────
    EYE_RX, EYE_RY = 44, 28
    eye_positions = [(cx - 118, 320), (cx + 118, 320)]

    for ex, ey in eye_positions:
        if blink == 0:
            # Open eye
            d.ellipse([ex - EYE_RX, ey - EYE_RY, ex + EYE_RX, ey + EYE_RY],
                      fill=EYE_WHITE)
            d.ellipse([ex - 22, ey - 22, ex + 22, ey + 22], fill=IRIS_C)
            d.ellipse([ex - 11, ey - 11, ex + 11, ey + 11], fill=PUPIL_C)
            # Catchlight
            d.ellipse([ex - 8, ey - 16, ex - 2, ey - 10],
                      fill=(255, 255, 255, 200))
            # Upper lid line
            d.arc([ex - EYE_RX, ey - EYE_RY, ex + EYE_RX, ey + EYE_RY],
                  200, 340, fill=(35, 22, 10), width=5)
            # Eyelashes
            for a in range(208, 332, 16):
                ar = math.radians(a)
                x1 = ex + EYE_RX * math.cos(ar)
                y1 = ey + EYE_RY * 0.65 * math.sin(ar)
                x2 = x1 + 10 * math.cos(ar)
                y2 = y1 + 10 * 0.7 * math.sin(ar)
                d.line([(x1, y1), (x2, y2)], fill=(20, 14, 8), width=3)

        elif blink == 1:
            # Half-closed
            d.ellipse([ex - EYE_RX, ey - EYE_RY, ex + EYE_RX, ey + EYE_RY],
                      fill=EYE_WHITE)
            d.ellipse([ex - 18, ey - 8, ex + 18, ey + 18], fill=IRIS_C)
            d.ellipse([ex - 9, ey + 2, ex + 9, ey + 16], fill=PUPIL_C)
            # Lid covering upper half
            d.ellipse([ex - EYE_RX - 4, ey - EYE_RY - 4,
                       ex + EYE_RX + 4, ey + 4], fill=SKIN)
            d.arc([ex - EYE_RX, ey - EYE_RY, ex + EYE_RX, ey + EYE_RY],
                  200, 340, fill=(35, 22, 10), width=5)

        else:
            # Fully closed — just a curved line
            d.arc([ex - EYE_RX, ey - 10, ex + EYE_RX, ey + 10],
                  0, 180, fill=(35, 22, 10), width=5)

    # ── Nose ─────────────────────────────────────────────────────────────
    NSH = (200, 160, 125)
    d.line([(cx, 345), (cx - 18, 440)], fill=NSH, width=3)
    d.line([(cx, 345), (cx + 18, 440)], fill=NSH, width=3)
    d.ellipse([cx - 30, 428, cx - 6, 454], fill=NSH)
    d.ellipse([cx + 6,  428, cx + 30, 454], fill=NSH)

    # ── Cheek blush ──────────────────────────────────────────────────────
    blush = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blush)
    bd.ellipse([cx - 178, 380, cx - 82, 450], fill=BLUSH_C)
    bd.ellipse([cx + 82,  380, cx + 178, 450], fill=BLUSH_C)
    img = Image.alpha_composite(img, blush)
    d   = ImageDraw.Draw(img)

    # ── Mouth ─────────────────────────────────────────────────────────────
    mx, my = cx, 520

    if mouth == 0:
        # Closed smile
        d.arc([mx - 62, my - 14, mx + 62, my + 26], 20, 160, fill=LIP_UP, width=7)
        d.arc([mx - 60, my - 6,  mx + 60, my + 32], 20, 160, fill=LIP_LO, width=5)

    elif mouth == 1:
        # Slight open — small gap
        d.ellipse([mx - 54, my - 10, mx + 54, my + 20], fill=MOUTH_IN)
        d.ellipse([mx - 48, my - 2,  mx + 48, my + 14], fill=TEETH_C)
        d.arc([mx - 62, my - 16, mx + 62, my + 14], 10, 170, fill=LIP_UP, width=7)
        d.arc([mx - 60, my + 4,  mx + 60, my + 28], 10, 170, fill=LIP_LO, width=5)

    elif mouth == 2:
        # Medium open — clear teeth
        d.ellipse([mx - 62, my - 20, mx + 62, my + 26], fill=MOUTH_IN)
        d.ellipse([mx - 55, my - 10, mx + 55, my + 20], fill=TEETH_C)
        for tx in [mx - 24, mx, mx + 24]:
            d.line([(tx, my - 10), (tx, my + 18)], fill=(215, 215, 215), width=2)
        d.arc([mx - 66, my - 26, mx + 66, my + 14], 10, 170, fill=LIP_UP, width=8)
        d.arc([mx - 64, my + 8,  mx + 64, my + 32], 10, 170, fill=LIP_LO, width=6)

    else:  # mouth == 3  — wide open
        d.ellipse([mx - 68, my - 30, mx + 68, my + 36], fill=MOUTH_IN)
        d.ellipse([mx - 60, my - 18, mx + 60, my + 26], fill=TEETH_C)
        for tx in [mx - 28, mx, mx + 28]:
            d.line([(tx, my - 18), (tx, my + 22)], fill=(215, 215, 215), width=2)
        d.arc([mx - 72, my - 36, mx + 72, my + 16], 10, 170, fill=LIP_UP, width=9)
        d.arc([mx - 70, my + 10, mx + 70, my + 40], 10, 170, fill=LIP_LO, width=7)

    return img


def build_face_cache(target_size: int = AV_R * 2) -> dict:
    """Pre-render 12 face states: 4 mouth × 3 blink. Returns {(m, b): RGBA Image}."""
    print("  [face] pre-rendering 12 avatar states...")
    cache = {}
    for m in range(4):
        for b in range(3):
            raw = _draw_face_raw(m, b)
            scaled = raw.resize((target_size, target_size), Image.LANCZOS)
            cache[(m, b)] = scaled
    return cache


def make_circle_crop(face_img: Image.Image) -> Image.Image:
    """Crop an RGBA image to a circle with soft edge."""
    s = face_img.size[0]
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out.paste(face_img, mask=mask)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
#  BLINK SCHEDULE
# ═══════════════════════════════════════════════════════════════════════════════

def make_blink_schedule(total_frames: int, fps: int = FPS) -> np.ndarray:
    """
    Returns int array of blink state per frame: 0=open, 1=half, 2=closed.
    Blinks occur every 2.5-5.5 seconds. Each blink: 6 frames (0.25s).
    """
    schedule = np.zeros(total_frames, dtype=np.int8)
    rng = random.Random(42)
    f = 0
    while f < total_frames:
        gap = int(rng.uniform(2.5, 5.5) * fps)
        f += gap
        if f >= total_frames:
            break
        # 6-frame blink: half, closed, closed, half, open, open
        for df, state in enumerate([1, 2, 2, 1, 0, 0]):
            if f + df < total_frames:
                schedule[f + df] = state
        f += 6
    return schedule


# ═══════════════════════════════════════════════════════════════════════════════
#  AMPLITUDE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def load_amplitude(audio_path: Path, total_frames: int) -> np.ndarray:
    if _LIBROSA:
        try:
            y, sr = librosa.load(str(audio_path), sr=None, mono=True)
            hop = max(1, int(sr / FPS))
            rms = librosa.feature.rms(y=y, hop_length=hop)[0]
            rms_n = rms / (rms.max() + 1e-8)
            x_old = np.linspace(0, 1, len(rms_n))
            x_new = np.linspace(0, 1, total_frames)
            return np.interp(x_new, x_old, rms_n).clip(0, 1).astype(np.float32)
        except Exception:
            pass
    t = np.linspace(0, total_frames / FPS, total_frames)
    return (0.5 + 0.4 * np.sin(t * 5.5)).clip(0, 1).astype(np.float32)


def amp_to_mouth(amp: float) -> int:
    if amp < 0.10: return 0
    if amp < 0.28: return 1
    if amp < 0.52: return 2
    return 3


# ═══════════════════════════════════════════════════════════════════════════════
#  WORD TIMESTAMPS (Whisper API — cached to JSON)
# ═══════════════════════════════════════════════════════════════════════════════

def get_word_timestamps(audio_path: Path, text: str, scene_slug: str) -> list[dict]:
    """Returns [{word, start, end}, ...]. Cached to TS_DIR."""
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
        # Evenly space words across duration
        clip = AudioFileClip(str(audio_path))
        dur  = clip.duration
        clip.close()
        ws = text.split()
        dt = dur / max(len(ws), 1)
        words = [{"word": w, "start": i * dt, "end": (i + 1) * dt} for i, w in enumerate(ws)]
        cache_path.write_text(json.dumps(words, indent=2), encoding="utf-8")
        return words


def subtitle_at(t: float, words: list[dict], window: int = 12) -> str:
    """Return the last `window` spoken words up to time t."""
    spoken = [w["word"] for w in words if w["start"] <= t + 0.05]
    if not spoken:
        return ""
    return " ".join(spoken[-window:])


# ═══════════════════════════════════════════════════════════════════════════════
#  WORKFLOW SIDEBAR RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def render_workflow_sidebar(fnt: dict, active_sprints: list[int]) -> np.ndarray:
    """Render a WORKFLOW_W × H sidebar showing sprint progress."""
    img  = Image.new("RGBA", (WORKFLOW_W, H), (8, 14, 48, 255))
    draw = ImageDraw.Draw(img)

    # Header strip
    draw.rectangle([0, 0, WORKFLOW_W, HDR_H], fill=(12, 20, 58))
    draw.line([0, HDR_H, WORKFLOW_W, HDR_H], fill=BLUE, width=2)
    draw.text((16, 22), "SPRINT PROGRESS", font=fnt["wf"], fill=CYAN)

    content_h = H - HDR_H - SBTL_H
    row_h     = content_h // len(SPRINT_LABELS)
    ry = HDR_H

    for num, label, done in SPRINT_LABELS:
        active   = num in active_sprints
        bg_base  = (14, 26, 72) if not done else (10, 36, 22)
        if done:
            bg = (12, 44, 26) if active else (10, 30, 18)
        else:
            bg = (50, 14, 14) if active else (28, 12, 12)
        draw.rectangle([0, ry, WORKFLOW_W, ry + row_h], fill=bg)

        # Accent bar on left edge
        bar_col = GREEN if done else RED
        draw.rectangle([0, ry, 5, ry + row_h], fill=bar_col)

        # Active glow highlight
        if active:
            draw.rectangle([5, ry, WORKFLOW_W, ry + row_h + 1],
                           fill=(*bar_col[:3], 25) if False else
                           (GREEN[0], GREEN[1], GREEN[2], 20) if done else
                           (RED[0], RED[1], RED[2], 20))
            draw.rectangle([5, ry, WORKFLOW_W, ry + 2], fill=bar_col)

        # Sprint number
        draw.text((14, ry + row_h // 2 - 10), f"S{num:02d}", font=fnt["wf"], fill=GRAY)

        # Label
        label_color = (180, 255, 190) if (done and active) else \
                      (140, 200, 150) if done else \
                      (255, 160, 160) if active else \
                      (200, 120, 120) if not done else \
                      (148, 163, 184)
        draw.text((50, ry + row_h // 2 - 10), label, font=fnt["wf"], fill=label_color)

        # Status badge (right side)
        mark = "✓" if done else "✗"
        mark_col = GREEN if done else RED
        if active:
            draw.ellipse([WORKFLOW_W - 32, ry + row_h // 2 - 12,
                         WORKFLOW_W - 8,  ry + row_h // 2 + 12],
                         fill=(*mark_col, 60))
        draw.text((WORKFLOW_W - 28, ry + row_h // 2 - 9), mark,
                  font=fnt["wf"], fill=mark_col)

        # Divider
        draw.line([0, ry + row_h, WORKFLOW_W, ry + row_h], fill=(20, 30, 70), width=1)
        ry += row_h

    # Legend at bottom
    leg_y = H - SBTL_H - 28
    draw.text((12, leg_y), "✓ Complete  ✗ Pending",
              font=fnt["wf"], fill=(80, 100, 130))

    return np.array(img.convert("RGB"))


# ═══════════════════════════════════════════════════════════════════════════════
#  SLIDE BUILDERS — content panel only (CONTENT_W × H)
# ═══════════════════════════════════════════════════════════════════════════════

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
    draw.text((20, 18), "NexGen  ·  Field to Finish  ·  Agentic AI OS", font=fnt["tag"], fill=CYAN)
    total = len(SCENES)
    dot_w, dot_r = 20, 5
    sx = w - total * dot_w - 16
    for i in range(total):
        cx2 = sx + i * dot_w + dot_r
        cy2 = HDR_H // 2
        draw.ellipse([cx2 - dot_r, cy2 - dot_r, cx2 + dot_r, cy2 + dot_r],
                     fill=CYAN if i == scene_num else (40, 55, 90))


def _white_card(img: Image.Image, w: int = CONTENT_W) -> tuple:
    """Draw white rounded card. Returns (img, draw, tx, ty)."""
    pad = 28
    x0, y0 = pad, HDR_H + pad
    x1, y1 = w - pad, H - SBTL_H - pad
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=(255, 255, 255, 245))
    d.rounded_rectangle([x0, y0, x1, y0 + 6], radius=14, fill=(*BLUE, 255))
    return img, d, x0 + 40, y0 + 40


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, line = text.split(), [], []
    for w in words:
        test = " ".join(line + [w])
        if draw.textbbox((0, 0), test, font=font)[2] > max_w and line:
            lines.append(" ".join(line)); line = [w]
        else:
            line.append(w)
    if line: lines.append(" ".join(line))
    return lines


def slide_bullets(scene_num: int, title: str, bullets: list[tuple], fnt: dict,
                  tag: str = "") -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, tag, scene_num)
    img, draw, tx, ty = _white_card(img)
    draw.text((tx, ty), title, font=fnt["h1"], fill=DARK)
    ty += draw.textbbox((0, 0), title, font=fnt["h1"])[3] + 32
    for text, color in bullets:
        draw.ellipse([tx, ty + 9, tx + 13, ty + 22], fill=BLUE)
        for ln in _wrap(draw, text, fnt["body"], CONTENT_W - 100):
            draw.text((tx + 24, ty), ln, font=fnt["body"], fill=color)
            ty += draw.textbbox((0, 0), ln, font=fnt["body"])[3] + 4
        ty += 14
    return np.array(img.convert("RGB"))


def slide_intro(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Introduction", 0)
    img, draw, tx, ty = _white_card(img)

    draw.text((tx, ty), "NexGen Field to Finish", font=fnt["h1"], fill=DARK)
    draw.text((tx, ty + 62), "Automated Quoting System", font=fnt["h2"], fill=BLUE)
    draw.line([tx, ty + 108, CONTENT_W - 56, ty + 108], fill=(219, 234, 254), width=2)

    stats = [("8", "AI Agents"), ("6", "Sprints"), ("141", "Tests Passing")]
    bx = tx; by = ty + 130; bw, bh = 220, 130
    for num, lbl in stats:
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=(239, 246, 255))
        draw.rounded_rectangle([bx, by, bx + bw, by + 6], radius=10, fill=BLUE)
        nb = draw.textbbox((0, 0), num, font=fnt["h1"])
        draw.text((bx + (bw - (nb[2] - nb[0])) // 2, by + 14), num, font=fnt["h1"], fill=BLUE)
        lb = draw.textbbox((0, 0), lbl, font=fnt["small"])
        draw.text((bx + (bw - (lb[2] - lb[0])) // 2, by + 78), lbl, font=fnt["small"], fill=GRAY)
        bx += bw + 24

    tag_str = "Sprint 0-6 Delivery  ·  May 2026  ·  Phase 1 Complete"
    tb = draw.textbbox((0, 0), tag_str, font=fnt["body"])
    draw.text((tx + (CONTENT_W - tx*2 - (tb[2]-tb[0])) // 2, by + bh + 26),
              tag_str, font=fnt["body"], fill=GRAY)
    return np.array(img.convert("RGB"))


def slide_pipeline(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Pipeline", 2)

    pad = 28
    x0, y0 = pad, HDR_H + pad
    x1, y1 = CONTENT_W - pad, H - SBTL_H - pad
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=(15, 23, 42, 250))
    draw.rounded_rectangle([x0, y0, x1, y0 + 50], radius=14, fill=(20, 35, 80, 255))
    draw = ImageDraw.Draw(img)
    draw.text((x0 + 22, y0 + 12), "8-AGENT PIPELINE  —  ALL BUILT & TESTED", font=fnt["h3"], fill=CYAN)

    rows = [
        ("Agent 2", "Monitor",         "S1", GREEN,  "Scans FTF every 60 min"),
        ("Agent 3", "Classifier",      "S2", GREEN,  "14 flag checks in <2s"),
        ("Agent 4", "Human Gate",      "S3", GREEN,  "Teams alert for complex orders"),
        ("Agent 5", "Pricing Engine",  "S2", GREEN,  "Pulls price from FTF API"),
        ("Agent 6", "Writer",          "S4", GREEN,  "Personalized estimate email"),
        ("Agent 7", "Reviewer",        "S5", GREEN,  "4-check accuracy review"),
        ("Agent 8", "Sender",          "S6", GREEN,  "Sends 8 AM–6 PM"),
        ("Agent 9", "Reporter",        "S6", GREEN,  "Daily Teams digest"),
    ]
    rh = (y1 - y0 - 56) // len(rows)
    ry = y0 + 56
    for i, (num, name, sprint, col, desc) in enumerate(rows):
        bg = (18, 30, 68) if i % 2 == 0 else (14, 24, 56)
        draw.rectangle([x0, ry, x1, ry + rh], fill=bg)
        draw.rounded_rectangle([x0 + 8, ry + rh//2 - 12, x0 + 38, ry + rh//2 + 12],
                                radius=5, fill=(18, 48, 26))
        draw.text((x0 + 14, ry + rh // 2 - 9), "✓", font=fnt["tag"], fill=GREEN)
        draw.text((x0 + 48, ry + 8), num, font=fnt["tag"], fill=GRAY)
        draw.text((x0 + 140, ry + 5), name, font=fnt["h3"], fill=WHITE)
        sb = draw.textbbox((0, 0), sprint, font=fnt["small"])
        draw.rounded_rectangle([x0 + 370, ry + 6, x0 + 370 + sb[2] + 18, ry + 6 + sb[3] + 10],
                                radius=4, fill=(20, 40, 100))
        draw.text((x0 + 378, ry + 10), sprint, font=fnt["small"], fill=CYAN)
        draw.text((x0 + 450, ry + 8), desc, font=fnt["body"], fill=(148, 163, 184))
        ry += rh
    return np.array(img.convert("RGB"))


def slide_ftf(fnt: dict, scene_num: int) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Field to Finish Portal", scene_num)

    bx, by = 24, HDR_H + 24
    bw = CONTENT_W - 48
    bh = H - SBTL_H - by - 24

    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=(240, 242, 247))
    draw.rounded_rectangle([bx, by, bx + bw, by + 42], radius=10, fill=WHITE)
    for xi, col in [(bx+10,(239,68,68)),(bx+28,(234,179,8)),(bx+46,(22,163,74))]:
        draw.ellipse([xi, by+12, xi+14, by+26], fill=col)
    draw.text((bx+68, by+12), "stage.fieldtofinish.jobs/orders", font=fnt["small"], fill=GRAY)

    ay = by + 42
    draw.rectangle([bx, ay, bx + bw, ay + 48], fill=(30, 64, 175))
    draw.text((bx+18, ay+10), "Field to Finish", font=fnt["h3"], fill=WHITE)
    draw.text((bx+bw-300, ay+12), "Orders   Clients   Reports", font=fnt["small"], fill=(186,209,255))

    ty = ay + 48 + 14
    draw.rectangle([bx+8, ty, bx+bw-8, ty+38], fill=(239,246,255))
    draw.text((bx+18, ty+8), "Quote-Stage Orders  —  New in last 60 minutes", font=fnt["small"], fill=(30,64,175))

    hdrs = ["Order ID","Service Type","Client","County","Time","Status"]
    cxs  = [bx+12, bx+150, bx+360, bx+600, bx+760, bx+920]
    hy = ty + 48
    draw.rectangle([bx+8, hy, bx+bw-8, hy+34], fill=(219,234,254))
    for h2, c in zip(hdrs, cxs):
        draw.text((c, hy+7), h2, font=fnt["tag"], fill=(30,64,175))

    tbl_rows = [
        ("ORD-2026-1001","Boundary Survey",    "John Martinez",     "Hillsborough","9:14 AM", True),
        ("ORD-2026-1002","ALTA Table A Survey","Coastal Builders LLC","Monroe",     "10:02 AM",False),
        ("ORD-2026-1003","Elevation Cert.",    "Maria Santos",      "Miami-Dade",  "10:47 AM",False),
    ]
    ry = hy + 34
    for i,(oid,svc,cl,co,ts,hi) in enumerate(tbl_rows):
        bg = (220,252,231) if hi else (241,245,255) if i%2==0 else WHITE
        draw.rectangle([bx+8, ry, bx+bw-8, ry+42], fill=bg)
        for v,c in zip([oid,svc,cl,co,ts], cxs):
            draw.text((c, ry+10), v, font=fnt["small"], fill=DARK)
        lbl = "● JOHN'S ORDER" if hi else "● Quote"
        draw.text((cxs[5], ry+10), lbl, font=fnt["small"], fill=GREEN if hi else BLUE)
        ry += 42

    draw.rounded_rectangle([bx+12, ry+16, bx+420, ry+48], radius=5, fill=(220,252,231))
    draw.text((bx+24, ry+24), "Agent 2 Monitor: ACTIVE — scanning every 60 min",
              font=fnt["small"], fill=(22,101,52))
    return np.array(img.convert("RGB"))


def slide_classify(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Classify & Price", 5)
    img, draw, tx, ty = _white_card(img)

    draw.text((tx, ty), "Agent 3 — Classifier  ·  ORD-2026-1001", font=fnt["h2"], fill=DARK)
    ty += 52

    checks = [
        "Standard service type", "Property in Florida", "Not a competitor",
        "Not on NEVER_AUTO_QUOTE list", "Not in VE flood zone", "Not Monroe County",
        "Valid property coordinates", "FEMA data available",
        "No missing county", "Not out-of-state", "No competitor email domain",
        "Not ALWAYS_FLAG type", "Value within range", "Valid address format",
    ]
    col_w = (CONTENT_W - tx * 2 - 10) // 2
    col_y = [ty, ty]
    for i, chk in enumerate(checks):
        col = 0 if i % 2 == 0 else 1
        cx2 = tx if col == 0 else tx + col_w + 12
        cy2 = col_y[col]
        draw.rounded_rectangle([cx2, cy2, cx2 + 22, cy2 + 24], radius=4, fill=(220,252,231))
        draw.text((cx2 + 4, cy2 + 3), "✓", font=fnt["tag"], fill=GREEN)
        draw.text((cx2 + 28, cy2 + 4), chk, font=fnt["small"], fill=DARK)
        col_y[col] += 36

    pr_y = max(col_y) + 16
    draw.rounded_rectangle([tx, pr_y, CONTENT_W - 56, pr_y + 66], radius=8, fill=(239,246,255))
    draw.rectangle([tx, pr_y, tx + 6, pr_y + 66], fill=GREEN)
    draw.text((tx + 18, pr_y + 8), "Agent 5 — Pricing Engine", font=fnt["h3"], fill=DARK)
    draw.text((tx + 18, pr_y + 38),
              "FTF API price:  $350.00   ·   Boundary Survey  ·   Status → PRICED",
              font=fnt["body"], fill=GREEN)
    return np.array(img.convert("RGB"))


def slide_human_gate(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Human Approval Gate", 6)

    cx0 = 24; cy0 = HDR_H + 24
    cw = CONTENT_W - 48

    draw.rounded_rectangle([cx0, cy0, cx0+cw, cy0+520], radius=12, fill=WHITE)
    draw.rounded_rectangle([cx0, cy0, cx0+cw, cy0+52], radius=12, fill=(98,100,167))
    draw.text((cx0+18, cy0+14), "Microsoft Teams  —  FTF Invoicing Channel", font=fnt["h3"], fill=WHITE)

    my = cy0+66
    draw.rounded_rectangle([cx0+16, my, cx0+cw-16, my+440], radius=8, fill=(245,247,250))
    draw.text((cx0+30, my+14), "FTF Agentic AI OS  ·  10:03 AM", font=fnt["small"], fill=GRAY)

    cy2 = my+44
    draw.rounded_rectangle([cx0+30, cy2, cx0+cw-30, cy2+366], radius=6, fill=WHITE)
    draw.rectangle([cx0+30, cy2, cx0+38, cy2+366], fill=AMBER)
    draw.text((cx0+52, cy2+16), "Order Requires Human Review — ORD-2026-1002", font=fnt["h3"], fill=DARK)

    facts = [
        ("Service Type", "ALTA Table A Survey", RED),
        ("Client",       "Coastal Builders LLC", DARK),
        ("County",       "Monroe (Florida Keys)", RED),
        ("Estimate",     "$1,725.00", DARK),
        ("Flag Reason",  "Monroe County — complex pricing", AMBER),
    ]
    fy = cy2 + 60
    for lbl, val, col in facts:
        draw.text((cx0+58, fy), lbl+":", font=fnt["small"], fill=GRAY)
        draw.text((cx0+250, fy), val, font=fnt["body"], fill=col)
        fy += 44

    draw.rounded_rectangle([cx0+58, fy+14, cx0+400, fy+50], radius=5, fill=(220,252,231))
    draw.text((cx0+72, fy+22), "Robert replied:  approve  →  pipeline resumed",
              font=fnt["body"], fill=(22,101,52))
    return np.array(img.convert("RGB"))


def slide_write_send(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Write · Review · Send", 7)
    img, draw, tx, ty = _white_card(img)

    draw.text((tx, ty), "ORD-2026-1001 — John Martinez", font=fnt["h2"], fill=DARK)
    ty += 50

    ew = CONTENT_W - tx * 2 - 8
    draw.rounded_rectangle([tx, ty, tx+ew, ty+200], radius=7, fill=(248,250,255))
    draw.rounded_rectangle([tx, ty, tx+ew, ty+34], radius=7, fill=(219,234,254))
    draw.text((tx+14, ty+8), "From: estimates@nexgen.enterprises    To: john.martinez@email.com",
              font=fnt["small"], fill=(30,64,175))
    for ln, txt in enumerate([
        "Hi John,",
        "Thank you for reaching out to NexGen Surveying.",
        "Service: Boundary Survey  ·  Property: Hillsborough County  ·  Estimate: $350.00",
    ]):
        draw.text((tx+14, ty+42+ln*38), txt, font=fnt["small"], fill=DARK)
    ty += 216

    draw.text((tx, ty+8), "Agent 7 — 4 Accuracy Checks", font=fnt["h3"], fill=DARK)
    ty += 46
    for chk in ["Price match ($350.00 ✓)", "Client name: John Martinez ✓",
                "Address: Hillsborough County ✓", "Change order clause present ✓"]:
        draw.rounded_rectangle([tx, ty, tx+22, ty+22], radius=4, fill=(220,252,231))
        draw.text((tx+4, ty+3), "✓", font=fnt["tag"], fill=GREEN)
        draw.text((tx+28, ty+3), chk, font=fnt["body"], fill=GREEN)
        ty += 36

    ty += 12
    draw.rounded_rectangle([tx, ty, tx+ew, ty+56], radius=7, fill=(239,246,255))
    draw.text((tx+14, ty+8),  "9:14 AM  John's order arrives in Field to Finish",
              font=fnt["small"], fill=GRAY)
    draw.text((tx+14, ty+30), "10:27 AM  Quote sent  →  73 minutes  ·  ZERO manual work",
              font=fnt["small"], fill=BLUE)
    return np.array(img.convert("RGB"))


def slide_db(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Live Database", 5)

    cx0 = 24; cy0 = HDR_H + 24
    cw = CONTENT_W - 48; ch = H - SBTL_H - cy0 - 24
    draw.rounded_rectangle([cx0, cy0, cx0+cw, cy0+ch], radius=10, fill=(15,23,42))
    draw.rounded_rectangle([cx0, cy0, cx0+cw, cy0+50], radius=10, fill=(20,35,80))
    draw.text((cx0+18, cy0+12), "DATABASE  —  processed_orders  (live)", font=fnt["h3"], fill=CYAN)

    cols = ["ORDER ID","CLIENT","SERVICE","AMOUNT","STATUS"]
    cxs  = [cx0+12, cx0+190, cx0+430, cx0+690, cx0+860]
    hy = cy0+56
    draw.rectangle([cx0, hy, cx0+cw, hy+36], fill=(25,45,95))
    for col, c in zip(cols, cxs):
        draw.text((c, hy+8), col, font=fnt["tag"], fill=(148,163,184))

    rows_d = [
        ("ORD-2026-1001","John Martinez",    "Boundary Survey",    "$350.00","PRICED",  CYAN,  "→"),
        ("ORD-2026-1002","Coastal Builders", "ALTA Table A Survey","$1,725","AWAITING", AMBER, "⏳"),
        ("ORD-2026-1003","Maria Santos",     "Elevation Cert.",    "$450.00","SENT",    GREEN, "✓"),
    ]
    ry = hy+36
    for i,(oid,cl,svc,amt,st,sc,ic) in enumerate(rows_d):
        bg = (22,42,94) if i==0 else (18,30,68) if i%2==0 else (14,24,56)
        draw.rectangle([cx0, ry, cx0+cw, ry+56], fill=bg)
        if i==0: draw.rectangle([cx0, ry, cx0+4, ry+56], fill=CYAN)
        for v,c in zip([oid,cl,svc,amt], cxs):
            draw.text((c, ry+16), v, font=fnt["mono"], fill=WHITE)
        draw.text((cxs[4]+2, ry+8), ic, font=fnt["body"], fill=sc)
        draw.text((cxs[4]+28, ry+16), st, font=fnt["mono"], fill=sc)
        ry += 56

    draw.rounded_rectangle([cx0+12, ry+12, cx0+780, ry+42], radius=5, fill=(20,50,90))
    draw.text((cx0+24, ry+18), "← John's order: all 14 classifier checks passed, price $350.00 locked",
              font=fnt["small"], fill=CYAN)
    return np.array(img.convert("RGB"))


def slide_roadmap(fnt: dict) -> np.ndarray:
    img = Image.new("RGB", (CONTENT_W, H))
    draw = ImageDraw.Draw(img)
    _content_bg(draw)
    _content_header(draw, fnt, "Sprint 7-12 Roadmap", 8)

    cx0 = 24; cy0 = HDR_H + 24
    cw = CONTENT_W - 48
    draw.rounded_rectangle([cx0, cy0, cx0+cw, cy0+50], radius=10, fill=(20,35,80))
    draw.text((cx0+18, cy0+12), "WHAT COMES NEXT — AND WHAT EACH SPRINT NEEDS",
              font=fnt["h3"], fill=CYAN)

    roadmap = [
        ("Sprint 7",  "AR Follow-Up",         "READY TO BUILD",  AMBER, "Needs: Jessica's process recording"),
        ("Sprint 8",  "Monthly Statements",   "READY TO BUILD",  AMBER, "Needs: Wyatt + Jessica recording"),
        ("Sprint 9",  "Memory Loop",          "CAN START NOW",   GREEN, "No external dependencies"),
        ("Sprint 10", "Staging Tests",        "MILESTONE",       BLUE,  "Needs: Ryan cost approval + stakeholder demo"),
        ("Sprint 11", "Limited Launch",       "BLOCKED",         GRAY,  "Needs: Sprint 10 + Ryan GO"),
        ("Sprint 12", "Full Production",      "BLOCKED",         GRAY,  "Needs: Sprint 11 + Robert/Mark sign-off"),
    ]
    rh = (H - SBTL_H - cy0 - 60) // len(roadmap)
    ry = cy0 + 56
    for i, (sp, ttl, status, sc, dep) in enumerate(roadmap):
        bg = (18,30,68) if i%2==0 else (14,24,56)
        draw.rectangle([cx0, ry, cx0+cw, ry+rh], fill=bg)
        draw.text((cx0+14, ry+rh//2-10), sp, font=fnt["tag"], fill=GRAY)
        draw.text((cx0+120, ry+rh//2-12), ttl, font=fnt["h3"], fill=WHITE)
        sb = draw.textbbox((0,0), status, font=fnt["small"])
        bw = sb[2]-sb[0]+20
        bx = cx0+620
        draw.rounded_rectangle([bx, ry+rh//2-14, bx+bw, ry+rh//2+14], radius=5,
                                fill=(40,55,90) if sc==GRAY else (sc[0]//5, sc[1]//5, sc[2]//5))
        draw.text((bx+8, ry+rh//2-9), status, font=fnt["small"], fill=sc)
        draw.text((cx0+650+bw, ry+rh//2-9), dep, font=fnt["small"], fill=(148,163,184))
        ry += rh
    return np.array(img.convert("RGB"))


def slide_outro(fnt: dict) -> np.ndarray:
    return slide_bullets(9, "Sprint 0-6: Complete", [
        ("141 automated tests — all passing", GREEN),
        ("8 AI agents — fully built and tested", GREEN),
        ("6 sprints — delivered on schedule", GREEN),
        ("Quoting is automated, 24/7, zero manual effort", DARK),
        ("Next: Sprints 7-12 once dependencies are resolved", GRAY),
    ], fnt, "Summary")


def build_all_slides(fnt: dict) -> dict:
    print("  [slides] rendering content panels...")
    s = {}
    s[0]  = slide_intro(fnt)
    s[1]  = slide_bullets(1, "The Manual Process — Before", [
                ("Check Field to Finish for new orders manually", RED),
                ("Look up price for each service type manually", RED),
                ("Write estimate email from scratch — every order", RED),
                ("50+ orders/week = hours of work every single day", RED),
                ("Now: fully automated, every 60 minutes", GREEN),
            ], fnt, "The Problem")
    s[2]  = slide_pipeline(fnt)
    s[3]  = slide_ftf(fnt, 3)
    s[4]  = slide_bullets(4, "Agent 2 — Monitor", [
                ("Scans Field to Finish every 60 minutes", DARK),
                ("Finds ORD-2026-1001: John Martinez, Boundary Survey", GREEN),
                ("Confirms it has not been processed before", DARK),
                ("Writes to database — Status: PENDING", DARK),
                ("Time from John's submission: under 60 minutes", BLUE),
                ("Your team: zero effort, zero log-ins", GREEN),
            ], fnt, "Sprint 1 — Monitor")
    s[5]  = slide_classify(fnt)
    s[6]  = slide_human_gate(fnt)
    s[7]  = slide_write_send(fnt)
    s[8]  = slide_roadmap(fnt)
    s[9]  = slide_outro(fnt)
    print(f"  {len(s)} slides rendered")
    return s


# ═══════════════════════════════════════════════════════════════════════════════
#  WORKFLOW SIDEBAR CACHE (one per scene)
# ═══════════════════════════════════════════════════════════════════════════════

def build_sidebar_cache(fnt: dict) -> dict:
    print("  [sidebar] pre-rendering workflow panels per scene...")
    cache = {}
    for idx, slug, _ in SCENES:
        actives = SCENE_SPRINTS.get(idx, [])
        cache[idx] = render_workflow_sidebar(fnt, actives)
    return cache


# ═══════════════════════════════════════════════════════════════════════════════
#  WAVEFORM HALO (amplitude-driven, around avatar circle)
# ═══════════════════════════════════════════════════════════════════════════════

_BAR_ANGLES = np.linspace(0, 2 * math.pi, 48, endpoint=False)


def draw_waveform_halo(img: Image.Image, t: float, amp: float, bob_y: int) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    r_in = AV_R + 8
    for i, angle in enumerate(_BAR_ANGLES):
        local = amp * (0.4 + 0.6 * abs(math.sin(t * 7.2 + i * 0.44)))
        local = max(0.05, local)
        r_out = r_in + int(local * 48) + 3
        x1 = AV_CX + r_in  * math.cos(angle)
        y1 = bob_y + r_in  * math.sin(angle)
        x2 = AV_CX + r_out * math.cos(angle)
        y2 = bob_y + r_out * math.sin(angle)
        inten = int(100 + 155 * local)
        alpha = int(50 + 190 * local)
        draw.line([(x1, y1), (x2, y2)],
                  fill=(79, inten, min(255, inten + 60), alpha), width=2)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


# ═══════════════════════════════════════════════════════════════════════════════
#  FRAME RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def build_make_frame(
    content_np: np.ndarray,
    sidebar_np: np.ndarray,
    face_cache: dict,
    amplitude: np.ndarray,
    blink_sched: np.ndarray,
    words: list[dict],
    fnt: dict,
) -> callable:
    """Build a make_frame(t) → np.ndarray[H,W,3] function for one scene."""
    # Pre-compose full background (avatar panel + content + sidebar) as RGBA
    bg = Image.new("RGB", (W, H))
    # Left avatar panel background
    av_draw = ImageDraw.Draw(bg)
    for y in range(H):
        t2 = y / H
        r = int(12 + 8 * t2); g = int(22 + 10 * t2); b = int(65 + 15 * t2)
        av_draw.line([(0, y), (LEFT_W, y)], fill=(r, g, b))
    av_draw.rectangle([LEFT_W, 0, LEFT_W + 2, H], fill=(30, 50, 120))
    # Header strip across full width
    av_draw.rectangle([0, 0, W, HDR_H], fill=(8, 15, 50))
    av_draw.line([0, HDR_H, W, HDR_H], fill=BLUE, width=3)
    av_draw.text((LEFT_W + 20, 18), "NexGen  ·  Field to Finish  ·  Agentic AI OS",
                 font=fnt["tag"], fill=CYAN)
    # Paste content panel
    content_img = Image.fromarray(content_np)
    bg.paste(content_img, (CONTENT_X, 0))
    # Paste sidebar
    sidebar_img = Image.fromarray(sidebar_np)
    bg.paste(sidebar_img, (WORKFLOW_X, 0))
    # Subtitle bar background
    av_draw.rectangle([0, H - SBTL_H, W, H], fill=(6, 12, 40))
    av_draw.line([0, H - SBTL_H, W, H - SBTL_H], fill=(30, 50, 100), width=1)
    # Avatar label
    av_draw.text((AV_CX - 30, H - SBTL_H + 18), "Alex  —  NexGen AI",
                 font=fnt["small"], fill=(148, 163, 184))

    bg_rgba = bg.convert("RGBA")

    # Crop pre-rendered face circles to circles once
    circle_cache = {k: make_circle_crop(v) for k, v in face_cache.items()}

    def make_frame(t: float) -> np.ndarray:
        fi   = min(int(t * FPS), len(amplitude) - 1)
        amp  = float(amplitude[fi])
        bk   = int(blink_sched[fi])
        ms   = amp_to_mouth(amp)
        bob  = AV_CY + int(math.sin(t * 1.7) * 4)

        # Start from pre-composed background
        frame = draw_waveform_halo(bg_rgba.copy(), t, amp, bob)

        # Paste animated face
        face_img = circle_cache[(ms, bk)]
        ax, ay = AV_CX - AV_R, bob - AV_R
        frame.paste(face_img, (ax, ay), face_img)

        # White ring border around avatar
        ri = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        ImageDraw.Draw(ri).ellipse(
            [ax - 4, ay - 4, ax + AV_R * 2 + 4, ay + AV_R * 2 + 4],
            outline=(255, 255, 255, 200), width=3,
        )
        frame = Image.alpha_composite(frame, ri)

        # Speaking pulse dot (below avatar)
        dot_y = bob + AV_R + 20
        di = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        dot_a = int(100 + 155 * amp)
        ImageDraw.Draw(di).ellipse(
            [AV_CX - 7, dot_y - 7, AV_CX + 7, dot_y + 7],
            fill=(22, 163, 74, dot_a),
        )
        frame = Image.alpha_composite(frame, di)

        # Subtitle overlay
        sub = subtitle_at(t, words, window=14)
        if sub:
            frame_rgb = frame.convert("RGB")
            sd = ImageDraw.Draw(frame_rgb)
            sb2 = sd.textbbox((0, 0), sub, font=fnt["sbtl"])
            sw = sb2[2] - sb2[0]
            sx2 = LEFT_W + (CONTENT_W - sw) // 2
            sy2 = H - SBTL_H + (SBTL_H - (sb2[3] - sb2[1])) // 2
            sd.text((sx2, sy2), sub, font=fnt["sbtl"], fill=WHITE)
            return np.array(frame_rgb)

        return np.array(frame.convert("RGB"))

    return make_frame


# ═══════════════════════════════════════════════════════════════════════════════
#  AUDIO
# ═══════════════════════════════════════════════════════════════════════════════

async def _tts(text: str, path: Path) -> float:
    if path.exists():
        c = AudioFileClip(str(path)); d = c.duration; c.close(); return d
    try:
        r = OAI.audio.speech.create(model="tts-1-hd", voice="nova",
                                    input=text, response_format="mp3")
        r.write_to_file(str(path))
    except Exception:
        await edge_tts.Communicate(text, "en-US-JennyNeural").save(str(path))
    c = AudioFileClip(str(path)); d = c.duration; c.close()
    return d


async def generate_all_audio() -> dict:
    print("  [audio] generating TTS narrations...")
    result = {}
    for idx, slug, text in SCENES:
        p = AUDIO_DIR / f"s{idx:02d}_{slug}.mp3"
        print(f"    {idx:02d} {slug:<22}", end="", flush=True)
        t0 = time.time()
        dur = await _tts(text, p)
        result[idx] = (p, dur)
        print(f" {dur:.1f}s  ({time.time()-t0:.1f}s)")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  TRANSCRIPT
# ═══════════════════════════════════════════════════════════════════════════════

def write_transcript(audio_map: dict) -> None:
    labels = {
        0:"Introduction", 1:"The Problem", 2:"Pipeline Overview",
        3:"Meet the Order", 4:"Agent 2 — Monitor", 5:"Classify & Price",
        6:"Human Approval Gate", 7:"Write, Review & Send",
        8:"Sprint 7–12 Roadmap", 9:"Summary",
    }
    lines = ["# FTF Agentic AI — Client Demo v3",
             f"**Date:** {datetime.now().strftime('%Y-%m-%d')}  |  **Voice:** OpenAI TTS nova  |  **Sprint 0–6**",
             "", "---", ""]
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


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def build_video() -> None:
    print("\nNexGen Client Demo v3 — Animated Avatar + Workflow Sidebar")
    print("=" * 58)
    print(f"Output: {DEMO_DIR}")
    print(f"librosa: {'active' if _LIBROSA else 'sine fallback'}")

    # 1. Audio
    print("\n[1/6] Audio")
    audio_map = await generate_all_audio()

    # 2. Word timestamps (Whisper)
    print("\n[2/6] Word timestamps (Whisper)")
    word_map = {}
    for idx, slug, text in SCENES:
        path, dur = audio_map[idx]
        print(f"  {idx:02d} {slug:<22}", end="", flush=True)
        t0 = time.time()
        words = get_word_timestamps(path, text, f"s{idx:02d}_{slug}")
        word_map[idx] = words
        print(f" {len(words)} words ({time.time()-t0:.1f}s)")

    # 3. Animated face cache
    print("\n[3/6] Face")
    fnt        = _fonts()
    face_cache = build_face_cache(AV_R * 2)

    # 4. Slides + sidebar
    print("\n[4/6] Slides + Sidebar")
    slides  = build_all_slides(fnt)
    sidebar = build_sidebar_cache(fnt)

    # 5. Transcript
    print("\n[5/6] Transcript")
    write_transcript(audio_map)

    # 6. Assemble
    print("\n[6/6] Assembling video...")
    clips = []
    for idx, slug, _ in SCENES:
        path, duration = audio_map[idx]
        total_frames   = int((duration + 0.4) * FPS) + 1
        amplitude      = load_amplitude(path, total_frames)
        blink_sched    = make_blink_schedule(total_frames)
        make_frame     = build_make_frame(
            slides[idx], sidebar[idx], face_cache,
            amplitude, blink_sched, word_map[idx], fnt,
        )
        print(f"  scene {idx:02d} {slug:<22} {duration:.1f}s")
        video = VideoClip(make_frame, duration=duration + 0.4)
        audio = AudioFileClip(str(path))
        clips.append(video.with_audio(audio))

    final = concatenate_videoclips(clips, method="compose")
    print(f"\nRendering → {OUTPUT}")
    print(f"Duration:   {final.duration:.0f}s  ({final.duration/60:.1f} min)")
    print("(5-15 minutes at 1920x1080 24fps...)\n")

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
