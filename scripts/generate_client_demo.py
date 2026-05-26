"""
generate_client_demo.py — Synthesia-style client demo video

HD 1920x1080 video with:
  - Real human AI avatar (DALL-E 3 professional headshot)
  - Animated speaking rings + natural bob motion
  - FTF Field to Finish portal mockup
  - Live database visualization
  - OpenAI TTS nova voice narration
  - 9 scenes, ~3 minutes, non-technical client language

Output: docs/demo_client_v1.mp4

Usage:
    set PYTHONUTF8=1
    python scripts/generate_client_demo.py
"""

import asyncio
import io
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests as req
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent / "code" / "shared"))
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import edge_tts
from moviepy import AudioFileClip, VideoClip, concatenate_videoclips

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

OAI = OpenAI(api_key=os.getenv("OpenAI_API_KEY"))

W, H  = 1920, 1080
FPS   = 24

ASSETS = Path("docs") / "demo_assets"
AUDIO  = ASSETS / "client_audio"
OUTPUT = Path("docs") / "demo_client_v1.mp4"
AVATAR_PATH = ASSETS / "avatar.png"

ASSETS.mkdir(parents=True, exist_ok=True)
AUDIO.mkdir(parents=True, exist_ok=True)

# ── layout constants ─────────────────────────────────────────────────────────
HDR_H   = 72      # header bar height
FTR_H   = 58      # footer height
LEFT_W  = 540     # avatar panel width
GAP     = 0       # gap between panels
RGT_X   = LEFT_W + GAP
RGT_W   = W - RGT_X
AV_CX   = LEFT_W  // 2        # avatar centre x
AV_CY   = HDR_H + (H - HDR_H - FTR_H) // 2   # avatar centre y  (≈ 569)
AV_R    = 195     # avatar circle radius

# ── colours ───────────────────────────────────────────────────────────────────
NAVY    = (10,  20,  60)
NAVY2   = (16,  32,  80)
BLUE    = (37,  99, 235)
CYAN    = (79, 195, 247)
WHITE   = (255, 255, 255)
OFF_W   = (248, 249, 252)
DARK    = (15,  23,  42)
GRAY    = (100, 116, 139)
GREEN   = (22, 163,  74)
YELLOW  = (202, 138,   4)
RED     = (220,  38,  38)
RING    = (99,  179, 255)

# ── fonts ─────────────────────────────────────────────────────────────────────
_FD = Path("C:/Windows/Fonts")

def _f(name: str, size: int) -> ImageFont.FreeTypeFont:
    for p in [_FD / name, _FD / name.lower()]:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)

def _fonts():
    return {
        "h1":    _f("calibrib.ttf", 54),
        "h2":    _f("calibrib.ttf", 38),
        "h3":    _f("calibrib.ttf", 28),
        "body":  _f("calibri.ttf",  26),
        "small": _f("calibri.ttf",  20),
        "tag":   _f("calibrib.ttf", 17),
        "mono":  _f("consola.ttf",  20),
    }

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — AVATAR (DALL-E 3)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_avatar() -> Image.Image:
    if AVATAR_PATH.exists():
        print("  [avatar] using cached avatar.png")
        return Image.open(AVATAR_PATH).convert("RGBA")

    prompt = (
        "Professional corporate headshot of a friendly female business consultant "
        "in her early 30s, dark navy blazer, white shirt, clean light-grey background, "
        "warm confident smile, photorealistic portrait photography"
    )

    # Try OpenAI image models in order of availability
    for model in ["gpt-image-1", "dall-e-3", "dall-e-2"]:
        try:
            print(f"  [avatar] trying {model}...")
            kwargs = dict(prompt=prompt, n=1)
            if model == "gpt-image-1":
                kwargs["size"] = "1024x1024"
            else:
                kwargs.update(size="1024x1024", quality="standard")
            resp = OAI.images.generate(model=model, **kwargs)
            url = resp.data[0].url
            img_bytes = req.get(url, timeout=30).content
            img = Image.open(io.BytesIO(img_bytes)).convert("RGBA").resize((512, 512), Image.LANCZOS)
            img.save(AVATAR_PATH)
            print(f"  [avatar] generated with {model} → {AVATAR_PATH}")
            return img
        except Exception as e:
            print(f"  [avatar] {model} failed: {e}")

    # Fallback — free professional portrait (randomuser.me)
    print("  [avatar] using free portrait fallback (randomuser.me)...")
    try:
        img_bytes = req.get("https://randomuser.me/api/portraits/women/44.jpg", timeout=15).content
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA").resize((512, 512), Image.LANCZOS)
        img.save(AVATAR_PATH)
        print(f"  [avatar] portrait saved → {AVATAR_PATH}")
        return img
    except Exception as e:
        print(f"  [avatar] portrait download failed: {e}")

    # Last resort — draw a professional silhouette avatar with Pillow
    print("  [avatar] drawing fallback silhouette avatar...")
    return _draw_fallback_avatar()


def _draw_fallback_avatar() -> Image.Image:
    """Draw a professional silhouette avatar when all other options fail."""
    size = 512
    img = Image.new("RGBA", (size, size), (30, 80, 160, 255))
    draw = ImageDraw.Draw(img)
    # gradient background
    for y in range(size):
        t = y / size
        r = int(20 + 40 * t); g = int(50 + 60 * t); b = int(140 + 40 * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    # head
    draw.ellipse([160, 80, 352, 272], fill=(255, 220, 185, 255))
    # hair
    draw.ellipse([155, 65, 357, 200], fill=(80, 50, 30, 255))
    draw.rectangle([155, 130, 357, 190], fill=(80, 50, 30, 255))
    # body / blazer
    draw.polygon([(100, 512), (180, 290), (256, 310), (332, 290), (412, 512)],
                 fill=(30, 50, 120, 255))
    # shirt
    draw.polygon([(200, 290), (256, 310), (312, 290), (300, 512), (212, 512)],
                 fill=(240, 245, 255, 255))
    # face features
    draw.ellipse([206, 155, 222, 171], fill=(60, 40, 20, 255))
    draw.ellipse([290, 155, 306, 171], fill=(60, 40, 20, 255))
    draw.arc([214, 195, 298, 230], 10, 170, fill=(180, 100, 90, 255), width=3)
    img.save(AVATAR_PATH)
    return img


def make_avatar_circle(avatar_img: Image.Image, r: int = AV_R) -> Image.Image:
    """Crop avatar into a circle of diameter 2r with soft edge."""
    size = r * 2
    src = avatar_img.resize((size, size), Image.LANCZOS).convert("RGBA")

    # circular mask
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1))

    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(src, mask=mask)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — AUDIO (OpenAI TTS)
# ═══════════════════════════════════════════════════════════════════════════════

SCENES = [
    (0, "intro",
     "Hi, I'm Alex from NexGen. In the next 3 minutes, I'll show you "
     "exactly how your new automated estimating system works — "
     "from a client submitting a survey request, all the way to them "
     "receiving their quote, with zero manual work from your team."),

    (1, "problem",
     "Before this system, your team had to manually check Field to Finish "
     "for new orders, calculate the price, write the email, and send it. "
     "With hundreds of orders coming in, that process took hours every day — "
     "and things could still fall through the cracks."),

    (2, "solution",
     "Now your system has 8 AI agents that run automatically every 60 minutes. "
     "They detect new orders, check them against your pricing, write "
     "personalized estimate emails, review them for accuracy, and send "
     "them to the client — all without your team lifting a finger."),

    (3, "ftf_portal",
     "Here's your Field to Finish portal. The moment a new Quote-stage order "
     "appears — like John Smith's Boundary Survey request — the AI detects "
     "it within the hour. No one has to log in and check manually. "
     "The system is always watching."),

    (4, "classify_price",
     "The system instantly checks: Is this a standard service? Is it in Florida? "
     "Any red flags? For John's Boundary Survey in Broward County — "
     "everything looks clean. The price — $350 — is pulled directly "
     "from your Field to Finish pricing system. No manual lookup needed."),

    (5, "db_live",
     "This is your database, updating in real time. "
     "Watch each order move through the pipeline automatically — "
     "from new, to priced, to sent. "
     "Three estimates went out today with zero manual effort. "
     "One order is waiting for Robert's approval — the AI flagged it "
     "because it's a complex survey type."),

    (6, "human_gate",
     "For high-value or complex orders — like an ALTA survey in the Florida Keys — "
     "the AI never sends automatically. It flags the order and sends "
     "Robert a notification in Microsoft Teams with all the details. "
     "Robert reviews it, types 'approve,' and the AI handles everything else. "
     "Nothing sensitive goes out without a human sign-off."),

    (7, "email_sent",
     "For standard orders, the AI writes a personalized estimate email for each client. "
     "It includes the service name, property address, total price, "
     "and the change order clause — automatically. "
     "It even checks its own work before sending. "
     "If it finds an error, it corrects it and checks again. "
     "Estimates go out between 8 AM and 6 PM, with a natural delay."),

    (8, "outro",
     "Every evening, your team receives a digest in Microsoft Teams: "
     "how many quotes were sent today, what's waiting for review, "
     "and the full pipeline status. No manual reporting. "
     "Your system is built, tested — 186 automated checks, zero failures. "
     "Thank you for watching."),
]


async def _tts(text: str, path: Path) -> float:
    if path.exists():
        clip = AudioFileClip(str(path))
        dur = clip.duration
        clip.close()
        return dur
    communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
    await communicate.save(str(path))
    # upgrade to OpenAI TTS for better quality
    try:
        resp = OAI.audio.speech.create(model="tts-1-hd", voice="nova", input=text, response_format="mp3")
        resp.write_to_file(str(path))
    except Exception:
        pass  # keep edge-tts fallback
    clip = AudioFileClip(str(path))
    dur = clip.duration
    clip.close()
    return dur


async def generate_all_audio() -> dict[int, tuple[Path, float]]:
    print("  [audio] generating TTS narrations...")
    result = {}
    for idx, slug, text in SCENES:
        p = AUDIO / f"c{idx:02d}_{slug}.mp3"
        print(f"    scene {idx:02d} {slug:<20}", end="", flush=True)
        dur = await _tts(text, p)
        result[idx] = (p, dur)
        print(f" {dur:.1f}s")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — SLIDE BACKGROUNDS (static Pillow renders)
# ═══════════════════════════════════════════════════════════════════════════════

def _gradient_bg(draw: ImageDraw.ImageDraw) -> None:
    """Fill canvas with deep navy gradient."""
    for y in range(H):
        t = y / H
        r = int(NAVY[0] + (NAVY2[0] - NAVY[0]) * t)
        g = int(NAVY[1] + (NAVY2[1] - NAVY[1]) * t)
        b = int(NAVY[2] + (NAVY2[2] - NAVY[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def _header(draw: ImageDraw.ImageDraw, fnt: dict, title: str) -> None:
    draw.rectangle([0, 0, W, HDR_H], fill=(8, 15, 50))
    draw.line([0, HDR_H, W, HDR_H], fill=(37, 99, 235), width=3)
    draw.text((28, 16), "NexGen  Field to Finish  Agentic AI", font=fnt["tag"], fill=CYAN)
    # right-align title
    bb = draw.textbbox((0, 0), title, font=fnt["tag"])
    tw = bb[2] - bb[0]
    draw.text((W - tw - 28, 16), title, font=fnt["tag"], fill=(148, 163, 184))


def _footer(draw: ImageDraw.ImageDraw, fnt: dict, scene_num: int) -> None:
    y0 = H - FTR_H
    draw.rectangle([0, y0, W, H], fill=(8, 15, 50))
    draw.line([0, y0, W, y0], fill=(30, 50, 100), width=1)
    draw.text((28, y0 + 16), "Alex  —  NexGen AI Lead", font=fnt["small"], fill=(148, 163, 184))
    # progress dots
    total = len(SCENES)
    dot_w, dot_r = 18, 5
    start_x = W - (total * dot_w) - 28
    for i in range(total):
        cx = start_x + i * dot_w + dot_r
        cy = y0 + FTR_H // 2
        color = CYAN if i == scene_num else (40, 55, 90)
        draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=color)


def _avatar_bg(draw: ImageDraw.ImageDraw) -> None:
    """Left panel background + separator."""
    draw.rectangle([0, HDR_H, LEFT_W, H - FTR_H], fill=(12, 22, 65))
    draw.rectangle([LEFT_W, HDR_H, LEFT_W + 2, H - FTR_H], fill=(30, 50, 120))


def _right_card(img: Image.Image, fnt: dict) -> tuple[Image.Image, ImageDraw.ImageDraw, int, int]:
    """Draw white content card on right panel. Returns (img, draw, x0, y0)."""
    pad = 32
    x0, y0 = RGT_X + pad, HDR_H + pad
    x1, y1 = W - pad, H - FTR_H - pad
    r = 16
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(255, 255, 255, 245))
    draw.rounded_rectangle([x0, y0, x1, y0 + 6], radius=r, fill=(*BLUE, 255))
    return img, draw, x0 + 48, y0 + 48


# ─── Scene slide builders ─────────────────────────────────────────────────────

def _slide_bullets(scene_num: int, title: str, bullets: list[tuple[str, tuple]],
                   fnt: dict, header_tag: str = "") -> np.ndarray:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_bg(draw)
    _header(draw, fnt, header_tag or f"Scene {scene_num + 1} of {len(SCENES)}")
    _footer(draw, fnt, scene_num)

    img, draw, tx, ty = _right_card(img, fnt)
    draw.text((tx, ty), title, font=fnt["h1"], fill=DARK)
    bb = draw.textbbox((tx, ty), title, font=fnt["h1"])
    ty += (bb[3] - bb[1]) + 36

    for text, color in bullets:
        # bullet dot
        draw.ellipse([tx, ty + 10, tx + 14, ty + 24], fill=BLUE)
        bb = draw.textbbox((0, 0), text, font=fnt["body"])
        th = bb[3] - bb[1]
        # word-wrap
        words = text.split()
        line, lines = [], []
        for w in words:
            test = " ".join(line + [w])
            bb2 = draw.textbbox((0, 0), test, font=fnt["body"])
            if bb2[2] - bb2[0] > RGT_W - 130 and line:
                lines.append(" ".join(line)); line = [w]
            else:
                line.append(w)
        if line: lines.append(" ".join(line))
        first = True
        for ln in lines:
            draw.text((tx + 28, ty), ln, font=fnt["body"], fill=color)
            bb3 = draw.textbbox((tx + 28, ty), ln, font=fnt["body"])
            ty += (bb3[3] - bb3[1]) + (6 if not first else 4)
            first = False
        ty += 16
    return np.array(img.convert("RGB"))


def _slide_ftf_portal(fnt: dict, scene_num: int) -> np.ndarray:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_bg(draw)
    _header(draw, fnt, "Field to Finish Portal")
    _footer(draw, fnt, scene_num)

    # browser chrome
    bx, by = RGT_X + 32, HDR_H + 32
    bw, bh = W - bx - 32, H - FTR_H - by - 32
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=(240, 242, 247))
    # url bar
    draw.rounded_rectangle([bx, by, bx + bw, by + 44], radius=10, fill=(255, 255, 255))
    draw.text((bx + 18, by + 10), "  stage.fieldtofinish.jobs/orders                                 ", font=fnt["small"], fill=(60, 70, 90))
    # browser dots
    for xi, col in [(bx + 12, (239,68,68)), (bx + 32, (234,179,8)), (bx + 52, (22,163,74))]:
        draw.ellipse([xi, by + 14, xi + 14, by + 28], fill=col)

    # FTF app header
    app_y = by + 44
    draw.rectangle([bx, app_y, bx + bw, app_y + 52], fill=(30, 64, 175))
    draw.text((bx + 20, app_y + 12), "Field to Finish", font=fnt["h3"], fill=WHITE)
    draw.text((bx + bw - 320, app_y + 14), "Orders   Clients   Reports   Settings", font=fnt["small"], fill=(186, 209, 255))

    # table
    tbl_y = app_y + 52 + 16
    draw.rectangle([bx + 8, tbl_y, bx + bw - 8, tbl_y + 40], fill=(239, 246, 255))
    draw.text((bx + 24, tbl_y + 8), "Quote-Stage Orders  —  3 new in last 60 min", font=fnt["small"], fill=(30, 64, 175))

    headers = ["Order ID", "Service Type", "Client Name", "County", "Submitted", "Status"]
    col_xs  = [bx + 16, bx + 130, bx + 370, bx + 650, bx + 830, bx + 1040]
    hdr_y   = tbl_y + 50
    draw.rectangle([bx + 8, hdr_y, bx + bw - 8, hdr_y + 36], fill=(219, 234, 254))
    for hdr, cx in zip(headers, col_xs):
        draw.text((cx, hdr_y + 8), hdr, font=fnt["tag"], fill=(30, 64, 175))

    rows = [
        ("ORD-2026-1001", "Boundary Survey",     "John Smith",        "Broward", "09:14 AM", "Quote", False),
        ("ORD-2026-1002", "ALTA Table A Survey", "Coastal Builders",   "Monroe",  "10:02 AM", "Quote", False),
        ("ORD-2026-1003", "Elevation Certificate","Maria Santos",       "Miami-D", "10:47 AM", "Quote", True),
    ]
    row_y = hdr_y + 36
    for i, (oid, svc, client, county, ts, status, new) in enumerate(rows):
        bg = (241, 245, 255) if i % 2 == 0 else WHITE
        if new: bg = (220, 252, 231)
        draw.rectangle([bx + 8, row_y, bx + bw - 8, row_y + 42], fill=bg)
        vals = [oid, svc, client, county, ts]
        for val, cx in zip(vals, col_xs):
            draw.text((cx, row_y + 10), val, font=fnt["small"], fill=DARK)
        dot_c = (37, 99, 235) if not new else (22, 163, 74)
        draw.ellipse([col_xs[5] - 10, row_y + 16, col_xs[5] + 6, row_y + 32], fill=dot_c)
        label = "● Quote  ← NEW" if new else "● Quote"
        draw.text((col_xs[5] + 10, row_y + 10), label, font=fnt["small"], fill=dot_c)
        row_y += 42

    # AI monitor badge
    badge_y = row_y + 20
    draw.rounded_rectangle([bx + 16, badge_y, bx + 420, badge_y + 36], radius=6, fill=(220, 252, 231))
    draw.text((bx + 32, badge_y + 7), "AI Monitor: scanning every 60 min  ●  ACTIVE", font=fnt["small"], fill=(22, 101, 52))

    return np.array(img.convert("RGB"))


def _slide_db(fnt: dict, scene_num: int, highlight_row: int = -1) -> np.ndarray:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_bg(draw)
    _header(draw, fnt, "Database: processed_orders")
    _footer(draw, fnt, scene_num)

    cx0, cy0 = RGT_X + 40, HDR_H + 40
    cw, ch = W - cx0 - 40, H - FTR_H - cy0 - 40

    # card
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=12, fill=(15, 23, 42))
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 50], radius=12, fill=(20, 35, 80))
    draw.text((cx0 + 24, cy0 + 12), "DATABASE  —  processed_orders  (live)", font=fnt["h3"], fill=CYAN)

    # column headers
    cols  = ["ORDER ID", "SERVICE TYPE", "CLIENT", "AMOUNT", "STATUS"]
    col_x = [cx0 + 20, cx0 + 200, cx0 + 520, cx0 + 820, cx0 + 1010]
    hdr_y = cy0 + 60
    draw.rectangle([cx0, hdr_y, cx0 + cw, hdr_y + 38], fill=(25, 45, 95))
    for col, cx in zip(cols, col_x):
        draw.text((cx, hdr_y + 8), col, font=fnt["tag"], fill=(148, 163, 184))

    db_rows = [
        ("ORD-2026-1001", "Boundary Survey",      "John Smith",         "$350.00",   "SENT",             GREEN,  "✓"),
        ("ORD-2026-1002", "ALTA Table A Survey",   "Coastal Builders",   "$1,725.00", "AWAITING APPROVAL",YELLOW, "⏳"),
        ("ORD-2026-1003", "Elevation Certificate", "Maria Santos",       "$450.00",   "SENT",             GREEN,  "✓"),
        ("ORD-2026-1004", "Boundary Survey",       "Robert Thompson",    "$350.00",   "PENDING",          (79,195,247), "→"),
    ]
    row_y = hdr_y + 38
    for i, (oid, svc, client, amt, status, sc, icon) in enumerate(db_rows):
        bg = (18, 30, 68) if i % 2 == 0 else (14, 24, 56)
        if i == highlight_row: bg = (22, 50, 30)
        draw.rectangle([cx0, row_y, cx0 + cw, row_y + 52], fill=bg)
        vals = [oid, svc, client, amt]
        for val, cx in zip(vals, col_x):
            draw.text((cx, row_y + 14), val, font=fnt["mono"], fill=WHITE)
        draw.text((col_x[4], row_y + 8), icon, font=fnt["body"], fill=sc)
        draw.text((col_x[4] + 30, row_y + 14), status, font=fnt["mono"], fill=sc)
        row_y += 52

    # summary row
    draw.rectangle([cx0, row_y, cx0 + cw, row_y + 44], fill=(18, 30, 68))
    draw.text((cx0 + 24, row_y + 10),
              "4 orders in pipeline  ·  3 estimates sent today  ·  1 awaiting approval  ·  0 failures",
              font=fnt["small"], fill=(100, 130, 180))

    return np.array(img.convert("RGB"))


def _slide_teams_report(fnt: dict, scene_num: int) -> np.ndarray:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw)
    _avatar_bg(draw)
    _header(draw, fnt, "Daily Teams Digest")
    _footer(draw, fnt, scene_num)

    cx0, cy0 = RGT_X + 40, HDR_H + 40
    cw = W - cx0 - 40

    # Teams card
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 560], radius=14, fill=WHITE)
    # purple Teams header strip
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 54], radius=14, fill=(98, 100, 167))
    draw.text((cx0 + 20, cy0 + 14), "Microsoft Teams  —  FTF Invoicing Channel", font=fnt["h3"], fill=WHITE)

    # message bubble
    msg_y = cy0 + 70
    draw.rounded_rectangle([cx0 + 20, msg_y, cx0 + cw - 20, msg_y + 450], radius=10, fill=(245, 247, 250))
    draw.text((cx0 + 36, msg_y + 16), "FTF Agentic AI OS  ·  Today 6:00 PM", font=fnt["small"], fill=GRAY)

    card_y = msg_y + 48
    draw.rounded_rectangle([cx0 + 36, card_y, cx0 + cw - 36, card_y + 360], radius=8, fill=WHITE)
    draw.rectangle([cx0 + 36, card_y, cx0 + 44, card_y + 360], fill=(98, 100, 167))
    draw.text((cx0 + 60, card_y + 16), "Daily Pipeline Summary — May 26, 2026", font=fnt["h3"], fill=DARK)

    facts = [
        ("Estimates Sent Today",     "8",  GREEN),
        ("Flagged (Needs Review)",   "2",  YELLOW),
        ("Awaiting Approval",        "1",  YELLOW),
        ("Ready to Send",            "3",  BLUE),
        ("Active Pipeline Total",    "14", DARK),
    ]
    fy = card_y + 60
    for label, val, color in facts:
        draw.text((cx0 + 70, fy), label + ":", font=fnt["body"], fill=GRAY)
        draw.text((cx0 + 430, fy), val, font=fnt["h2"], fill=color)
        fy += 52

    return np.array(img.convert("RGB"))


def _slide_human_gate(fnt: dict, scene_num: int) -> np.ndarray:
    bullets = [
        ("Robert receives a Teams notification with full order details", DARK),
        ("He reviews the property on GIS and in Field to Finish", DARK),
        ("He types 'approve' — the AI handles everything else", (22, 101, 52)),
        ("Full audit trail: every decision is logged automatically", GRAY),
        ("Nothing risky goes out without a human sign-off", (153, 27, 27)),
    ]
    return _slide_bullets(scene_num, "Complex Orders: Robert Stays in Control", bullets, fnt, "Human Approval Gate")


def build_all_slides(fnt: dict) -> dict[int, np.ndarray]:
    print("  [slides] rendering scene backgrounds...")
    slides = {}
    slides[0] = _slide_bullets(0, "Your New Automated Estimating System", [
        ("Detects new survey orders the moment they arrive in Field to Finish", DARK),
        ("Prices them automatically using your existing pricing data", DARK),
        ("Writes a personalized estimate email using Claude AI", DARK),
        ("Sends it between 8 AM–6 PM with a natural human-like delay", DARK),
        ("Every 60 minutes, around the clock — zero manual effort", (22, 101, 52)),
    ], fnt, "Intro")

    slides[1] = _slide_bullets(1, "Before: Manual Process, Hours of Work", [
        ("Log into Field to Finish to check for new orders", (153, 27, 27)),
        ("Manually look up the price for each service type", (153, 27, 27)),
        ("Write the estimate email from scratch — every time", (153, 27, 27)),
        ("Review and send — hoping nothing was missed", (153, 27, 27)),
        ("Now: the AI does all of this automatically", (22, 101, 52)),
    ], fnt, "The Challenge")

    slides[2] = _slide_bullets(2, "8 AI Agents, Running Every 60 Minutes", [
        ("Agent 2  —  Scans Field to Finish for new orders", DARK),
        ("Agent 3  —  Classifies service type, checks 9 risk triggers", DARK),
        ("Agent 4  —  Routes complex orders to Robert for approval", DARK),
        ("Agent 5  —  Pulls price from your FTF pricing system", DARK),
        ("Agents 6+7  —  Writes and self-reviews the estimate email", DARK),
        ("Agent 8  —  Sends estimate in business hours with natural delay", DARK),
    ], fnt, "The Solution")

    slides[3] = _slide_ftf_portal(fnt, 3)
    slides[4] = _slide_bullets(4, "Instant Classification and Pricing", [
        ("Service: Boundary Survey  →  standard, no flags", (22, 101, 52)),
        ("Location: Florida, Broward County  →  in-state, no restrictions", (22, 101, 52)),
        ("Flood zone: X  →  no elevation certificate required", (22, 101, 52)),
        ("Price: $350.00  →  pulled directly from FTF pricing API", (22, 101, 52)),
        ("Decision: auto-quote approved  ·  zero human involvement", BLUE),
    ], fnt, "Classification & Pricing")

    slides[5] = _slide_db(fnt, 5, highlight_row=2)
    slides[6] = _slide_human_gate(fnt, 6)
    slides[7] = _slide_bullets(7, "Personalized Email — Written and Reviewed by AI", [
        ("Claude AI writes a warm, personalized email for each client", DARK),
        ("Includes: service name, property address, price, change order clause", DARK),
        ("Reviewer Agent runs 4 accuracy checks before sending", DARK),
        ("If it finds an error, it corrects and re-checks automatically", (202, 138, 4)),
        ("Sends between 8 AM–6 PM with a 6–13 minute natural delay", DARK),
    ], fnt, "Estimate Email")

    slides[8] = _slide_teams_report(fnt, 8)
    return slides


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — FRAME RENDERING (avatar animation + slide composite)
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_speaking_rings(img: Image.Image, t: float, bob_y: int) -> Image.Image:
    """Overlay animated speaking rings onto RGBA image."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for i, (r_add, a_scale) in enumerate([(0, 0.75), (28, 0.45), (56, 0.22)]):
        phase = t * 5.5 + i * 1.1
        r = int(AV_R + 24 + r_add + np.sin(phase) * 9)
        a = int((np.sin(phase) * 0.25 + 0.75) * a_scale * 255)
        draw.ellipse(
            [AV_CX - r, bob_y - r, AV_CX + r, bob_y + r],
            outline=(*RING, a), width=4 - i
        )
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def build_make_frame(slide_np: np.ndarray, av_circle: Image.Image) -> callable:
    """Returns a make_frame(t) function for this scene."""
    slide_rgba = Image.fromarray(slide_np).convert("RGBA")

    def make_frame(t: float) -> np.ndarray:
        bob = AV_CY + int(np.sin(t * 1.7) * 4)
        frame = _draw_speaking_rings(slide_rgba.copy(), t, bob)
        # paste avatar circle (with alpha)
        ax = AV_CX - AV_R
        ay = bob - AV_R
        frame.paste(av_circle, (ax, ay), av_circle)
        # white ring border around avatar
        ring_img = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        ring_draw = ImageDraw.Draw(ring_img)
        ring_draw.ellipse([ax - 4, ay - 4, ax + AV_R * 2 + 4, ay + AV_R * 2 + 4],
                          outline=(255, 255, 255, 220), width=4)
        frame = Image.alpha_composite(frame, ring_img)
        return np.array(frame.convert("RGB"))

    return make_frame


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — ASSEMBLE VIDEO
# ═══════════════════════════════════════════════════════════════════════════════

async def build_video():
    print("\nNexGen Client Demo Video Generator")
    print("=" * 50)

    # 1. Avatar
    print("\n[1/4] Avatar")
    avatar_raw = fetch_avatar()
    av_circle  = make_avatar_circle(avatar_raw)

    # 2. Audio
    print("\n[2/4] Audio (OpenAI TTS)")
    audio_map = await generate_all_audio()

    # 3. Slides
    print("\n[3/4] Slides")
    fnt    = _fonts()
    slides = build_all_slides(fnt)
    print(f"  {len(slides)} slides rendered")

    # 4. Assemble
    print("\n[4/4] Assembling video...")
    clips = []
    for idx, slug, _ in SCENES:
        audio_path, duration = audio_map[idx]
        slide_np = slides[idx]
        make_frame = build_make_frame(slide_np, av_circle)

        print(f"  scene {idx:02d} {slug:<22} {duration:.1f}s")
        video = VideoClip(make_frame, duration=duration + 0.4)
        audio = AudioFileClip(str(audio_path))
        video = video.with_audio(audio)
        clips.append(video)

    final = concatenate_videoclips(clips, method="compose")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nRendering → {OUTPUT}")
    print(f"Duration:   {final.duration:.0f}s  ({final.duration/60:.1f} min)")
    print("(this takes 5-10 minutes at 1920x1080 24fps...)\n")

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
    print(f"Total: {total_dur:.0f} seconds  ({total_dur/60:.1f} min)")


if __name__ == "__main__":
    asyncio.run(build_video())
