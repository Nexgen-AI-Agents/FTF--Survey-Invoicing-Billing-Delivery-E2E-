#!/usr/bin/env python3
"""PRODUCTION (runtime) Anthropic cost for one project, scoped to its OWN API key(s).

Method (authoritative): Admin Usage API filtered by api_key_id -> price tokens at official rates.
The Cost API can't filter by key (only workspace/description), so we isolate by key and then
VALIDATE by reproducing the Cost-API workspace total to the cent. Reads the admin key from .env;
never prints it.

GOTCHAS baked in:
- Cost API `amount` is in CENTS (divide by 100).
- usage `cache_creation` is NESTED (ephemeral_5m/1h_input_tokens); the flat field is 0.

Edit the CONFIG block, then run:  python fetch_production_cost.py
"""
import os, json, urllib.request, urllib.parse, urllib.error
from collections import defaultdict

# ============================ CONFIG (edit per project) ============================
KEY_NAMES   = ["MyApp", "MyApp_Dev"]   # exact production key name(s) for THIS project
ENV_PATH    = ".env"                    # file holding the admin key
ADMIN_VAR   = "Anthropic_Admin_Key"     # env var name of the sk-ant-admin... key
START       = "2026-06-01T00:00:00Z"    # window start (day-aligned UTC)
END         = "2026-07-01T00:00:00Z"    # window end
# Official list rates USD/1M: (uncached_in, output, cache_read, cache_write_5m, cache_write_1h)
RATE = {"opus": (5.0, 25.0, 0.50, 6.25, 10.0), "sonnet": (3.0, 15.0, 0.30, 3.75, 6.0),
        "haiku": (1.0, 5.0, 0.10, 1.25, 2.0)}
# ===================================================================================

def env(name, path=ENV_PATH):
    for ln in open(path, encoding="utf-8"):
        if ln.strip().startswith(name):
            return ln.split("=", 1)[1].strip()
KEY = env(ADMIN_VAR)
assert KEY and KEY.startswith("sk-ant-admin"), "admin key not found in .env"
BASE = "https://api.anthropic.com/v1/organizations"
HDR = {"x-api-key": KEY, "anthropic-version": "2023-06-01"}

def fam(m):
    m = (m or "").lower()
    return "opus" if "opus" in m else "sonnet" if "sonnet" in m else "haiku" if "haiku" in m else "opus"

def toks(res):
    cc = res.get("cache_creation") or {}
    return (int(res.get("uncached_input_tokens", 0) or 0), int(res.get("output_tokens", 0) or 0),
            int(res.get("cache_read_input_tokens", 0) or 0),
            int(cc.get("ephemeral_5m_input_tokens", 0) or 0), int(cc.get("ephemeral_1h_input_tokens", 0) or 0))

def cost_of(model, t):
    ui, out, cr, w5, w1 = t; r = RATE[fam(model)]
    return ui/1e6*r[0] + out/1e6*r[1] + cr/1e6*r[2] + w5/1e6*r[3] + w1/1e6*r[4]

def get_all(path, params):
    items, page = [], None
    while True:
        q = list(params) + [("limit", 31)]
        if page: q.append(("page", page))
        url = f"{BASE}/{path}?" + urllib.parse.urlencode(q, doseq=True)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=120) as r:
                body = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} on {path}:", e.read().decode()[:400]); raise
        items.extend(body.get("data", []))
        if body.get("has_more") and body.get("next_page"): page = body["next_page"]
        else: return items

# resolve key names -> ids (+ their workspace, for validation)
keys = {k["id"]: k for k in get_all("api_keys", [])}
ids = {kid: k.get("name") for kid, k in keys.items() if k.get("name") in KEY_NAMES}
assert ids, f"no keys matched {KEY_NAMES}; available: {sorted(set(k.get('name') for k in keys.values()))[:30]}"
wss = set(keys[k].get("workspace_id") for k in ids)

# pull usage scoped to those keys
params = [("starting_at", START), ("ending_at", END), ("bucket_width", "1d"),
          ("group_by[]", "model"), ("group_by[]", "api_key_id")]
for kid in ids: params.append(("api_key_ids[]", kid))
agg = defaultdict(lambda: [0, 0, 0, 0, 0])
for b in get_all("usage_report/messages", params):
    for res in b.get("results", []):
        kid = res.get("api_key_id")
        if kid not in ids: continue
        cur = agg[(kid, res.get("model"))]; agg[(kid, res.get("model"))] = [a+c for a, c in zip(cur, toks(res))]

print("=== PRODUCTION usage by key/model ===")
g_cost = g_tok = 0
for (kid, model), t in sorted(agg.items(), key=lambda x: ids[x[0][0]]):
    c = cost_of(model, t); tok = sum(t); g_cost += c; g_tok += tok
    print(f"  {ids[kid]:14} {model:18} {tok:>14,} tok  ${c:,.2f}")
print(f"  TOTAL: {g_tok:,} tokens  ${g_cost:,.2f}")

# validate pricing: reproduce the Cost-API workspace total (in CENTS) for each workspace
print("\n=== validation (priced full workspace vs authoritative Cost API) ===")
for ws in wss:
    if not ws: continue
    wp = [("starting_at", START), ("ending_at", END), ("bucket_width", "1d"),
          ("group_by[]", "model"), ("workspace_ids[]", ws)]
    priced = sum(cost_of(res.get("model"), toks(res)) for b in get_all("usage_report/messages", wp)
                 for res in b.get("results", []))
    cr = [("starting_at", START), ("ending_at", END), ("group_by[]", "workspace_id")]
    cents = sum(float(res.get("amount", 0) or 0) for b in get_all("cost_report", cr)
                for res in b.get("results", []) if res.get("workspace_id") == ws)
    auth = cents / 100.0   # Cost API amount is in CENTS
    ratio = priced / auth if auth else 0
    print(f"  ws {ws}: priced ${priced:,.2f} vs authoritative ${auth:,.2f}  ratio {ratio:.4f} (~1.0 = pricing correct)")
