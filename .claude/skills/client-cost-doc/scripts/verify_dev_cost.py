#!/usr/bin/env python3
"""DEVELOPMENT (build) cost of one project, measured from its Claude Code transcripts.

Sums each assistant message's usage from ~/.claude/projects/<slug>/*.jsonl and prices it at list
rates. CRITICAL: dedupes by API message id - Claude Code re-logs resumed/compacted sessions, so a
raw sum double-counts ~5x. Scope is STRICTLY this project's folder(s); other projects share the
same Claude Code keys and must not be attributed here.

Edit the CONFIG block, then run:  python verify_dev_cost.py
"""
import os, json, glob, re
from collections import defaultdict

# ============================ CONFIG (edit per project) ============================
# REPO_PATHS: one or more absolute repo paths whose transcripts count as THIS project.
# The Claude Code folder slug = every non-alphanumeric char replaced by '-'.
REPO_PATHS = [r"C:\path\to\my project"]
PROJECTS_ROOT = os.path.expanduser(r"~/.claude/projects")
# ===================================================================================

RATE = {"opus": (5.0, 25.0, 0.50, 6.25, 10.0), "sonnet": (3.0, 15.0, 0.30, 3.75, 6.0),
        "haiku": (1.0, 5.0, 0.10, 1.25, 2.0)}
def fam(m):
    m = (m or "").lower()
    return "opus" if "opus" in m else "sonnet" if "sonnet" in m else "haiku" if "haiku" in m else "opus"
def slug(p): return re.sub(r"[^A-Za-z0-9]", "-", p)

def usage_of(u):
    cw = u.get("cache_creation_input_tokens", 0) or 0
    cc = u.get("cache_creation")
    if not cw and isinstance(cc, dict):
        cw = (cc.get("ephemeral_5m_input_tokens", 0) or 0) + (cc.get("ephemeral_1h_input_tokens", 0) or 0)
    return (int(u.get("input_tokens", 0) or 0), int(u.get("output_tokens", 0) or 0),
            int(u.get("cache_read_input_tokens", 0) or 0), int(cw))

def cost_of(model, t):
    ui, out, cr, cw = t; r = RATE[fam(model)]
    return ui/1e6*r[0] + out/1e6*r[1] + cr/1e6*r[2] + cw/1e6*r[3]

def scan(folder):
    by_model = defaultdict(lambda: [0, 0, 0, 0]); turns = 0; days = set(); seen = set()
    for fp in glob.glob(os.path.join(folder, "*.jsonl")):
        with open(fp, encoding="utf-8") as fh:
            for line in fh:
                if '"usage"' not in line: continue
                try: o = json.loads(line)
                except Exception: continue
                msg = o.get("message") if isinstance(o.get("message"), dict) else None
                if not msg or msg.get("role") != "assistant": continue
                u = msg.get("usage")
                if not isinstance(u, dict): continue
                mid = msg.get("id") or o.get("requestId") or o.get("uuid")   # dedupe key
                if mid is not None:
                    if mid in seen: continue
                    seen.add(mid)
                t = usage_of(u)
                if sum(t) == 0: continue
                m = by_model[msg.get("model", "unknown")]
                for i in range(4): m[i] += t[i]
                turns += 1
                ts = o.get("timestamp", "")
                if ts: days.add(ts[:10])
    return by_model, turns, days

grand_c = grand_t = 0
for rp in REPO_PATHS:
    folder = os.path.join(PROJECTS_ROOT, slug(rp))
    by_model, turns, days = scan(folder)
    print(f"=== {rp}")
    if not os.path.isdir(folder):
        print(f"   (no transcripts at {folder})"); continue
    fc = ft = 0
    for model, t in sorted(by_model.items()):
        c = cost_of(model, t); tok = sum(t); fc += c; ft += tok
        print(f"   {model:18} {tok:>14,} tok  ${c:,.2f}")
    dr = (min(days) + ".." + max(days)) if days else "n/a"
    print(f"   turns {turns:,} | {dr} | TOTAL {ft:,} tok  ${fc:,.2f}")
    grand_c += fc; grand_t += ft
print(f"\n=== DEVELOPMENT TOTAL (deduped): {grand_t:,} tokens  ${grand_c:,.2f} ===")
print("   (value at list rates; +/-~10%. Validate token count with validate_dev.py.)")
