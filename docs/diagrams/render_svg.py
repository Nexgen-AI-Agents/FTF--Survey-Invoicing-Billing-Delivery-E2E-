"""
render_svg.py — Lightweight Excalidraw JSON → SVG renderer (no CDN/network deps).
Handles: rectangle, ellipse, line (filled polygon), arrow, text.
Usage: python render_svg.py <input.excalidraw> <output.svg>
"""
import json, sys
from pathlib import Path
from html import escape

PADDING = 60

def compute_bounds(elements):
    xs, ys = [], []
    for el in elements:
        x, y, w, h = el.get("x", 0), el.get("y", 0), el.get("width", 0), el.get("height", 0)
        xs += [x, x + w]
        ys += [y, y + h]
        for pt in el.get("points", []):
            xs.append(x + pt[0]); ys.append(y + pt[1])
    return min(xs), min(ys), max(xs), max(ys)

def arrow_marker(color):
    cid = color.replace("#", "")
    return (
        f'<marker id="arr_{cid}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
        f'<polygon points="0 0, 8 3, 0 6" fill="{color}"/>'
        f'</marker>'
    )

def render_rect(el, ox, oy):
    x = el["x"] - ox; y = el["y"] - oy
    w, h = el["width"], el["height"]
    fill = el.get("backgroundColor", "none")
    fill = "none" if fill in ("transparent", "", None) else fill
    stroke = el.get("strokeColor", "#000")
    sw = el.get("strokeWidth", 1)
    rx = "8" if el.get("roundness") else "0"
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}" ry="{rx}"/>'

def render_ellipse(el, ox, oy):
    cx = el["x"] - ox + el["width"] / 2
    cy = el["y"] - oy + el["height"] / 2
    rx, ry = el["width"] / 2, el["height"] / 2
    fill = el.get("backgroundColor", "none")
    fill = "none" if fill in ("transparent", "", None) else fill
    stroke = el.get("strokeColor", "#000")
    sw = el.get("strokeWidth", 1)
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def render_line(el, ox, oy):
    pts = el.get("points", [])
    bx, by = el["x"] - ox, el["y"] - oy
    abs_pts = [(bx + p[0], by + p[1]) for p in pts]
    pts_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in abs_pts)
    fill = el.get("backgroundColor", "none")
    fill = "none" if fill in ("transparent", "", None) else fill
    stroke = el.get("strokeColor", "#000")
    sw = el.get("strokeWidth", 1)
    is_closed = len(pts) > 2 and (pts[0][0] == pts[-1][0] and pts[0][1] == pts[-1][1])
    if is_closed:
        return f'<polygon points="{pts_str}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    return f'<polyline points="{pts_str}" fill="none" stroke="{stroke}" stroke-width="{sw}"/>'

def render_arrow(el, ox, oy, arrow_colors):
    pts = el.get("points", [])
    bx, by = el["x"] - ox, el["y"] - oy
    abs_pts = [(bx + p[0], by + p[1]) for p in pts]
    pts_str = " ".join(f"{px:.1f},{py:.1f}" for px, py in abs_pts)
    stroke = el.get("strokeColor", "#000")
    sw = el.get("strokeWidth", 2)
    arrow_colors.add(stroke)
    cid = stroke.replace("#", "")
    end = el.get("endArrowhead")
    marker = f' marker-end="url(#arr_{cid})"' if end else ""
    return f'<polyline points="{pts_str}" fill="none" stroke="{stroke}" stroke-width="{sw}"{marker}/>'

def render_text(el, ox, oy):
    x = el["x"] - ox; y = el["y"] - oy
    w = el.get("width", 200); h = el.get("height", 20)
    fs = el.get("fontSize", 16)
    ta = el.get("textAlign", "left")
    color = el.get("strokeColor", "#000")
    raw = el.get("text", "")
    lines = raw.split("\n")
    lh = fs * 1.35

    if ta == "center":
        anchor, tx = "middle", x + w / 2
    elif ta == "right":
        anchor, tx = "end", x + w
    else:
        anchor, tx = "start", x

    parts = []
    # Clip text to its bounding box
    clip_id = f"clip_{abs(hash(raw) % 999999)}"
    # Use dominant-baseline to align top of first line with y
    for i, line in enumerate(lines):
        ty = y + fs + i * lh
        parts.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" '
            f'fill="{color}" font-size="{fs}" font-family="monospace" '
            f'text-anchor="{anchor}">{escape(line)}</text>'
        )
    return "\n".join(parts)

def excalidraw_to_svg(inpath, outpath):
    data = json.loads(Path(inpath).read_text(encoding="utf-8"))
    elements = [e for e in data["elements"] if not e.get("isDeleted")]

    min_x, min_y, max_x, max_y = compute_bounds(elements)
    ox = min_x - PADDING
    oy = min_y - PADDING
    W = int(max_x - min_x + PADDING * 2)
    H = int(max_y - min_y + PADDING * 2)

    arrow_colors = set()
    body_parts = []

    for el in elements:
        t = el.get("type")
        if t == "rectangle":
            body_parts.append(render_rect(el, ox, oy))
        elif t == "ellipse":
            body_parts.append(render_ellipse(el, ox, oy))
        elif t == "line":
            body_parts.append(render_line(el, ox, oy))
        elif t == "arrow":
            body_parts.append(render_arrow(el, ox, oy, arrow_colors))
        elif t == "text":
            body_parts.append(render_text(el, ox, oy))

    defs = "<defs>" + "".join(arrow_marker(c) for c in arrow_colors) + "</defs>"

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'style="background:#ffffff; font-family:monospace;">\n'
        f'{defs}\n'
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>\n'
        + "\n".join(body_parts)
        + "\n</svg>"
    )

    Path(outpath).write_text(svg, encoding="utf-8")
    print(f"SVG written: {outpath}  ({W}x{H}px)")

if __name__ == "__main__":
    excalidraw_to_svg(sys.argv[1], sys.argv[2])
