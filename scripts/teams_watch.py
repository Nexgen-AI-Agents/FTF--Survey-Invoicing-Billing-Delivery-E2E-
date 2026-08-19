"""teams_watch.py — check the Teams chat every 30 min and act on the team's input.

Between the twice-daily reports the team may answer a question or drop an instruction.
This watcher closes that gap: it reads new chat messages, learns from them, and replies
in the chat — but ONLY when there is something to say.

What it does when it finds input:
  • learns it (saved to learned_rules.json['user_guidance'], which A3 reads as
    [OPERATOR GUIDANCE] when pricing — nothing hardcoded); and
  • posts a SHORT acknowledgement naming what it learned, plus any clarification it
    needs, quoting the exact question + answer it refers to.

What it never does: post when there is nothing new (no chat spam), touch the Approvals
sheet, email a client, or act on an ambiguous instruction by itself.

Usage:
    python scripts/teams_watch.py              # ingest + reply if there is input
    python scripts/teams_watch.py --dry-run    # show what it WOULD post; posts nothing
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_11_invoice_pipeline"))

from core.logger import get_logger  # noqa: E402

log = get_logger("teams_watch")


def _esc(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


_QUOTES = "\"'" + chr(0x201C) + chr(0x201D)     # straight + curly quotes
_ELLIPSIS = chr(0x2026)


def _clean(s: str, limit: int = 150) -> str:
    """Tidy a snippet: strip wrapping quotes/ellipses so it never renders as ''text''."""
    t = str(s or "").strip().strip(_QUOTES).strip()
    while t.startswith("..."):
        t = t[3:].strip()
    t = t.strip(_QUOTES).strip()
    return _esc(t[:limit] + (_ELLIPSIS if len(t) > limit else ""))


def build_reply(learned: list, clarifs: list) -> str:
    """Short, skimmable chat reply: a table of what I learned + a table of what I must confirm."""
    from daily_report import _table          # one table style across all chat messages

    parts = ["<p>&#129302; <b>AI Invoicing Agent</b> &mdash; <i>thanks, I read your message.</i></p>"]

    if learned:
        rows = [[_esc(x.get("qid") or "&mdash;"),
                 _clean(x.get("answer"), 90),
                 "<b>%s</b>" % _clean(x.get("learning"), 150)] for x in learned]
        parts.append("<p>&#127891; <b>What I learned</b> <i>(saved to memory)</i></p>")
        parts.append(_table(["Q", "You said", "So I will now"], rows))

    if clarifs:
        rows = [[_esc(c.get("qid") or "&mdash;"),
                 _clean(c.get("question"), 80),
                 _clean(c.get("answer"), 80),
                 "<b>%s</b>" % _clean(c.get("clarification"), 220)] for c in clarifs]
        parts.append("<p>&nbsp;</p><p>&#129300; <b>Before I act, please confirm</b><br>"
                     "<i>I will not skip or change any billing until you reply.</i></p>")
        parts.append(_table(["Q", "I asked", "You said", "&#128072; I need to know"], rows))
        parts.append("<p><i>Reply with the question number (e.g. &ldquo;Q1: ...&rdquo;) "
                     "and I will save it.</i></p>")
    return "".join(parts)


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in argv

    from agents.teams_learning import (
        ingest_replies, recent_learnings, take_pending_clarifications,
    )

    res = ingest_replies()
    if not res.get("enabled"):
        log.info("teams_watch: learning loop disabled/idle — nothing to do")
        print("IDLE: learning loop not enabled (TEAMS_CHAT_ID unset?)")
        return 0

    n_learn, n_clar = res.get("learned", 0), res.get("clarifications", 0)
    log.info("teams_watch: read=%s learned=%s clarifications=%s",
             res.get("read", 0), n_learn, n_clar)

    learned = recent_learnings(limit=n_learn) if n_learn else []
    # Consuming here is correct: these clarifications are being ASKED right now in chat.
    # Includes any still-unasked clarification from an earlier tick, so a question the agent
    # needs answered reaches the team within ~30 min instead of waiting for the next report.
    clarifs = take_pending_clarifications(limit=3, mark_asked=not dry)

    if not learned and not clarifs:
        print(f"NO_NEW_INPUT (read={res.get('read', 0)}) — nothing posted")
        return 0

    html = build_reply(learned, clarifs)

    if dry:
        print(html)
        return 0

    from daily_report import post
    code = post(html)
    print(f"POSTED status={code} learned={n_learn} clarifications={len(clarifs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
