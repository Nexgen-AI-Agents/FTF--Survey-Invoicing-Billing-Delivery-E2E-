#!/usr/bin/env python3
"""VALIDATE the transcript-based dev measurement against Anthropic's Admin API ground truth.

Sums deduped tokens across ALL local Claude Code projects (window-filtered) and compares to the
Admin Usage API total for the Claude Code keys. If they reconcile (~within 10-15%; residual gap =
same-day reporting lag), the transcript+dedupe method is sound and the per-project subset is
trustworthy. Reads the admin key from .env; never prints it.

Edit the CONFIG block, then run:  python validate_dev.py
"""
import os, json, glob, urllib.request, urllib.parse
from collections import defaultdict

# ============================ CONFIG (edit per project) ============================
ENV_PATH      = ".env"
ADMIN_VAR     = "Anthropic_Admin_Key"
CC_WORKSPACE  = ""                 # the "Claude Code" workspace id (wrkspc_...); find via api_keys
CC_KEY_MATCH  = "claude_code_key"  # substring identifying the Claude Code (dev) key names
START         = "2026-06-01"       # window (YYYY-MM-DD); local transcripts filtered to this
END           = "2026-06-30"
PROJECTS_ROOT = os.path.expanduser(r"~/.claude/projects")
# ===================================================================================

def env(name, path=ENV_PATH):
    for ln in open(path, encoding="utf-8"):
        if ln.strip().startswith(name):
            return ln.split("=", 1)[1].strip()
KEY = env(ADMIN_VAR)
BASE = "https://api.anthropic.com/v1/organizations"
HDR = {"x-api-key": KEY, "anthropic-version": "2023-06-01"}

def get_all(path, params):
    items, page = [], None
    while True:
        q = list(params) + [("limit", 31)]
        if page: q.append(("page", page))
        url = f"{BASE}/{path}?" + urllib.parse.urlencode(q, doseq=True)
        with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=120) as r:
            body = json.loads(r.read().decode())
        items.extend(body.get("data", []))
        if body.get("has_more") and body.get("next_page"): page = body["next_page"]
        else: return items

# 1) Admin API token total for the Claude Code dev keys
names = {k["id"]: (k.get("name") or "") for k in get_all("api_keys", [])}
params = [("starting_at", START + "T00:00:00Z"), ("ending_at", END + "T23:59:59Z"),
          ("bucket_width", "1d"), ("group_by[]", "api_key_id")]
if CC_WORKSPACE: params.append(("workspace_ids[]", CC_WORKSPACE))
admin = 0
for b in get_all("usage_report/messages", params):
    for res in b.get("results", []):
        if CC_KEY_MATCH not in names.get(res.get("api_key_id"), ""): continue
        cc = res.get("cache_creation") or {}
        admin += (int(res.get("uncached_input_tokens", 0) or 0) + int(res.get("output_tokens", 0) or 0)
                  + int(res.get("cache_read_input_tokens", 0) or 0)
                  + int(cc.get("ephemeral_5m_input_tokens", 0) or 0) + int(cc.get("ephemeral_1h_input_tokens", 0) or 0))

# 2) local transcripts: deduped token total (window-filtered) across ALL projects
seen = set(); local = 0; per_folder = defaultdict(int)
for folder in glob.glob(os.path.join(PROJECTS_ROOT, "*")):
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
                ts = (o.get("timestamp") or "")[:10]
                if not (ts and START <= ts <= END): continue
                mid = msg.get("id")
                if mid:
                    if mid in seen: continue
                    seen.add(mid)
                cc = u.get("cache_creation") or {}
                cw = u.get("cache_creation_input_tokens", 0) or 0
                if not cw and isinstance(cc, dict):
                    cw = (cc.get("ephemeral_5m_input_tokens", 0) or 0) + (cc.get("ephemeral_1h_input_tokens", 0) or 0)
                tok = (int(u.get("input_tokens", 0) or 0) + int(u.get("output_tokens", 0) or 0)
                       + int(u.get("cache_read_input_tokens", 0) or 0) + int(cw))
                local += tok; per_folder[os.path.basename(folder)] += tok

print(f"Admin API (dev keys, {START}..{END}):  {admin:,} tokens")
print(f"Local transcripts (deduped, window):  {local:,} tokens")
print(f"ratio local/admin = {local/admin:.3f}  (~1.0-1.15 validates; >1 excess = same-day reporting lag)\n")
print("Top local projects (window, deduped):")
for fol, tok in sorted(per_folder.items(), key=lambda x: -x[1])[:10]:
    print(f"  {tok:>14,}  {fol[-50:]}")
