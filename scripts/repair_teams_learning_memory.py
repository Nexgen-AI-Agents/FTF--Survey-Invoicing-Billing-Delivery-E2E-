"""repair_teams_learning_memory.py — clean up the guidance my own re-asking bug polluted.

On 2026-08-19 the Teams learning loop asked the team the same question five times in three
hours (root cause: the interpreter prompt forced a clarification on every exclusion-style
answer, and it was never shown what it had already learned or asked). Each round wrote a
fresh 'learning', so data/learned_rules.json ended up with 13 near-duplicate teams_chat
guidance notes that CONTRADICT each other, e.g.:

    "Do not price or bill any order with an order number below #1000288500"
    "Leave flagged orders below #1000288500 untouched - no rejection, no status change"

A3 injects every one of these into its pricing prompt as [OPERATOR GUIDANCE]. Contradictory
guidance about not billing is the dangerous kind: it could talk the model into zeroing a
price on an order a human actually wants billed. So this collapses the whole cluster into
ONE conservative note that matches what the team actually confirmed and what the code now
does (hide from the report; never auto-reject; still billable on human approval).

Also drops one misread: the agent learned "when Prateek says he is modifying the agent,
pause posting" from a message Prateek addressed to Sumit, not to it.

Safety: backs the file up first, writes atomically, changes NOTHING else in the file (rules,
order_overrides, observations, processed ids, open_questions all preserved untouched), and
never touches the Excel sheet or any order. --dry-run shows the diff and writes nothing.

Usage:
    python scripts/repair_teams_learning_memory.py --dry-run
    python scripts/repair_teams_learning_memory.py
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

CUTOFF = "1000288500"

# The single note that replaces the contradictory cluster. Deliberately conservative: it
# constrains what the agent SAYS, not whether work can be billed.
CANONICAL = (
    "Orders with an order number below #%s are historical / test-phase backlog. "
    "Do not surface them in the daily report and do not ask the team about them. "
    "Do NOT reject them, change their status, or treat them as non-billable: if a human "
    "approves one, price and bill it normally. Only orders #%s and above are fresh work "
    "worth asking about. (Confirmed by the team in the Teams chat, 2026-08-19.)"
) % (CUTOFF, CUTOFF)

# A note is part of the cluster if it is about the cutoff, or is the misread pause instruction.
_PAUSE = re.compile(r"pause posting|modifying the agent", re.I)


def _is_cluster(note: str) -> bool:
    n = str(note or "")
    return CUTOFF in n or "1000288000" in n or bool(_PAUSE.search(n)) \
        or "older historical order" in n.lower() or "legacy flagged" in n.lower() \
        or "master sheet is a mixed dataset" in n.lower()


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in argv
    with open(RULES, encoding="utf-8") as f:
        data = json.load(f)

    guidance = [g for g in (data.get("user_guidance") or []) if isinstance(g, dict)]
    chat = [g for g in guidance if g.get("source") == "teams_chat"]
    doomed = [g for g in chat if _is_cluster(g.get("note"))]
    keep = [g for g in guidance if g not in doomed]

    print("user_guidance total     : %d" % len(guidance))
    print("  from teams_chat       : %d" % len(chat))
    print("  duplicates to collapse: %d" % len(doomed))
    for g in doomed:
        print("      - %s" % (str(g.get("note"))[:96]))
    if not doomed:
        print("nothing to repair")
        return 0

    keep.append({
        "order_id": "", "client": "", "service": "",
        "note": CANONICAL, "source": "teams_chat",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    })
    print("\nreplaced by ONE note:\n  %s" % CANONICAL)

    # every clarification in the file was already asked; keep them as the audit trail but
    # make sure none can fire again at the team.
    clarifs = [c for c in (data.get("pending_clarifications") or []) if isinstance(c, dict)]
    unasked = [c for c in clarifs if not c.get("asked")]
    for c in unasked:
        c["asked"] = True
        c["asked_at"] = datetime.now(timezone.utc).isoformat()
        c["note"] = "auto-closed by repair: superseded by the canonical guidance"
    print("\npending_clarifications  : %d (closed %d that could still have fired)"
          % (len(clarifs), len(unasked)))

    if dry:
        print("\nDRY RUN — nothing written")
        return 0

    os.makedirs(BACKUPS, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(BACKUPS, "learned_rules.%s.json" % stamp)
    shutil.copy2(RULES, bak)

    data["user_guidance"] = keep
    data["pending_clarifications"] = clarifs
    tmp = RULES + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, RULES)
    print("\nbackup : %s" % bak)
    print("written: %s (user_guidance now %d)" % (RULES, len(keep)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
