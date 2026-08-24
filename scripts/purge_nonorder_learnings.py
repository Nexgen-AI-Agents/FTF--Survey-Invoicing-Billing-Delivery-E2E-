"""purge_nonorder_learnings.py — the agent's memory is about ORDERS, nothing else.

The Teams learning loop was paraphrasing conversation back as durable rules. By 2026-08-24 the
teams_chat half of data/learned_rules.json['user_guidance'] held notes like:

    "When Prateek says to close the sheet, stop reading and writing to the master sheet and
     pause updates until he says it is okay to resume."
    "When a quote-sending delay is reported, immediately compile and post the exact list of
     order numbers that have approved prices but no quote sent, so Prateek can investigate."
    "Orders 1000288760 through 1000288764 had approved prices with quotes not sent; keep them
     tracked as pending quote-send..."

None of that is knowledge about an order. Two of the three are actively harmful: A3 injects
user_guidance into its pricing prompt as [OPERATOR GUIDANCE], so a "pause / stop writing" note
sits in the context that decides what a client is charged, and a transient "these five are
unsent" note is simply false an hour later.

This drops the non-order notes from BOTH stores:
  • user_guidance   — the channel A3 and the daily report read
  • teams_learnings — fed back to the interpreter as "already_learned", so junk left here keeps
                      reinforcing itself

Kept, untouched: every non-teams_chat entry (the per-order overrides synced from the sheet),
and any teams_chat note that IS about orders/pricing (e.g. the #1000288500 cutoff rule).
Nothing else in the file is read or written — rules, order_overrides, observations, processed
ids and open_questions are preserved byte-for-byte.

Safety: backs the file up first, writes atomically, never touches the Excel sheet or any order.
--dry-run prints the classification and writes nothing.

Usage:
    python scripts/purge_nonorder_learnings.py --dry-run
    python scripts/purge_nonorder_learnings.py
"""
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "data", "learned_rules.json")
BACKUPS = os.path.join(ROOT, "backups", "learning")

# Kept deliberately identical in spirit to teams_learning._SELF_OP: an instruction about the
# agent's own operation must never live in memory. Operational control is cron + config.
_SELF_OP = re.compile(
    # Object must be one of the agent's own actions, close to the verb — see teams_learning.
    r"\b(pause|unpause|resume|stop|halt|suspend|disable|re-?enable|restart|reboot|re-?deploy)\b"
    r"[^.]{0,25}?\b(post|posting|writ|read|sync|updates?|the sheet|the workbook|the spreadsheet|"
    r"the file|the agent|the bot|the pipeline)"
    r"|\b(close|lock|unlock|open)\b[^.]{0,30}?\b(sheet|workbook|spreadsheet|file)\b"
    r"|\bstay paused\b|\buntil .{0,30}\bsays? (it is okay|GO)\b",
    re.I,
)

# Time-bound state. True when written, false an hour later — never durable knowledge.
_TRANSIENT = re.compile(
    r"\bnot (yet )?sent\b|\bstill (not|un)sent\b|\bquotes? (are )?unsent\b|\bwith quotes not sent\b"
    r"|\bpending quote-send\b|\bsitting unsent\b|\bsit unsent\b|\bkeep them tracked\b"
    r"|\bis stuck at\b|\bfalls behind\b|\bvalidation is confirmed complete\b"
    r"|\bhas not been (sent|processed|picked)\b",
    re.I,
)

# How the agent should talk / who it should answer / what it should escalate. Chat etiquette and
# monitoring behaviour, not order knowledge — and it has no business in a pricing prompt.
_META = re.compile(
    r"\b(do not|don'?t|you may) reply\b|\brespond only to\b|\bpost the exact list\b"
    r"|\bflag it to\b|\breport back\b|\btreat it as an? .{0,25}failure\b"
    r"|\brather than (marking|treating)\b|\bkeep responses focused\b",
    re.I,
)

_REASONS = (("self-operation instruction", _SELF_OP),
            ("transient status, not durable", _TRANSIENT),
            ("agent behaviour / chat etiquette", _META))


def classify(text: str):
    """Return the reason this note must go, or None to keep it."""
    for reason, rx in _REASONS:
        if rx.search(str(text or "")):
            return reason
    return None


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in argv
    with open(RULES, encoding="utf-8") as f:
        data = json.load(f)

    guidance = [g for g in (data.get("user_guidance") or []) if isinstance(g, dict)]
    learnings = [x for x in (data.get("teams_learnings") or []) if isinstance(x, dict)]

    keep_g, drop_g = [], []
    for g in guidance:
        # Only ever judge chat-derived notes. Sheet-derived per-order overrides are the
        # operators' own data and are never touched.
        if g.get("source") != "teams_chat":
            keep_g.append(g)
            continue
        why = classify(g.get("note"))
        (drop_g if why else keep_g).append(g)
        if why:
            g["_why"] = why

    keep_l, drop_l = [], []
    for x in learnings:
        why = classify(x.get("learning"))
        (drop_l if why else keep_l).append(x)
        if why:
            x["_why"] = why

    print("user_guidance   : %d total, %d from teams_chat" %
          (len(guidance), sum(1 for g in guidance if g.get("source") == "teams_chat")))
    print("  dropping %d:" % len(drop_g))
    for g in drop_g:
        print("    - [%s] %s" % (g.pop("_why"), str(g.get("note"))[:110].replace("\n", " ")))
    print("  keeping %d teams_chat note(s):" %
          sum(1 for g in keep_g if g.get("source") == "teams_chat"))
    for g in keep_g:
        if g.get("source") == "teams_chat":
            print("    + %s" % str(g.get("note"))[:110].replace("\n", " "))
    print("\nteams_learnings : %d total, dropping %d" % (len(learnings), len(drop_l)))
    for x in drop_l:
        print("    - [%s] %s" % (x.pop("_why"), str(x.get("learning"))[:100].replace("\n", " ")))

    if not drop_g and not drop_l:
        print("\nnothing to purge")
        return 0
    if dry:
        print("\nDRY RUN — nothing written")
        return 0

    os.makedirs(BACKUPS, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(BACKUPS, "learned_rules.%s.json" % stamp)
    shutil.copy2(RULES, bak)

    data["user_guidance"] = keep_g
    data["teams_learnings"] = keep_l
    tmp = RULES + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, RULES)
    print("\nbackup : %s" % bak)
    print("written: %s (user_guidance %d -> %d, teams_learnings %d -> %d)"
          % (RULES, len(guidance), len(keep_g), len(learnings), len(keep_l)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
