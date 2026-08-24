"""teams_learning.py — learn from the team's Teams-chat answers (self-learning loop).

The report asks numbered questions in the chat. The team replies (usually tagging the
agent) with answers like "Question1: ... Answer: ...". This module closes the loop:

  1. record_open_questions()  — remember WHAT we asked, with stable ids (Q1, Q2 ...)
  2. ingest_replies()         — read new chat messages, match each answer to the question
                                it refers to, and LEARN from it
  3. Learning is written to learned_rules.json['user_guidance'] — the SAME store the
     Approvals-sheet "Learning provided by user" column feeds, which A3 already injects
     into its pricing prompt as [OPERATOR GUIDANCE]. Nothing is hardcoded: the model
     reasons with the operator's own words, and every record keeps its provenance.
  4. When an answer is unclear or risky, we do NOT guess — we queue a CLARIFICATION that
     quotes the exact question plus the answer it refers to, so the next report can ask
     precisely "about Q1, you said X — I need Y".

Safety: read-only w.r.t. Teams and the Excel sheet. It never executes an operational
action (never excludes orders, never changes prices by itself) — it only records guidance
for the model to reason with, and questions for humans to confirm. Never raises.
"""
import json
import os
import re
from datetime import datetime, timezone

from config.models import HUMAN_GATE_MODEL
from config.settings import TEAMS_LEARNING_ENABLED
from core.claude_client import call as llm_call
from core.logger import get_logger
from core.teams_reader import fetch_messages, resolve_chat_id

log = get_logger("teams_learning")

_RULES_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "learned_rules.json")
)

_MAX_OPEN_QUESTIONS = 12      # questions stay answerable for a few report cycles
_MAX_MSGS           = 25      # newest messages scanned per run
_MAX_PROCESSED_IDS  = 500     # ring buffer for idempotency
_MAX_CLARIFY_PER_Q  = 2       # hard cap: one question, at most two follow-ups, ever


def _load() -> dict:
    try:
        with open(_RULES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> bool:
    """Atomic write — a crash must never corrupt the learning memory."""
    try:
        tmp = _RULES_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _RULES_FILE)
        return True
    except Exception as exc:
        log.warning("teams_learning: could not save memory: %s", exc)
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_TAGS = re.compile(r"<[^>]+>")


def _topic_key(text: str) -> str:
    """Stable identity for a question, ignoring HTML and the counts/ids inside it.

    "Set a price for <b>104</b> order(s)? e.g. #100028" and the same question next cycle
    with 93 orders are the SAME question — matching on raw text would keep re-asking it
    forever and would never mark it answered."""
    t = _TAGS.sub("", text or "").lower()
    t = re.sub(r"[#$]?\d[\d,.]*", "", t)      # drop counts, order numbers, amounts
    t = re.sub(r"[^a-z ]+", " ", t)
    return " ".join(t.split())


def record_open_questions(questions: list, label: str = "") -> list:
    """Remember the questions this report asks so replies can be matched to them.

    Returns [{qid, text}] in order, so the report can render "Question 1: ...".
    Re-asking the same text reuses its qid (the team may answer a day later)."""
    fallback = [{"qid": "Q%d" % (i + 1), "text": q} for i, q in enumerate(questions)]
    data = _load()
    if not data:
        return fallback
    open_qs = data.setdefault("open_questions", [])
    by_key = {q.get("key"): q for q in open_qs if isinstance(q, dict) and q.get("key")}
    seq = int(data.get("question_seq") or 0)
    out = []
    for i, text in enumerate(questions):
        key = _topic_key(text)
        existing = by_key.get(key)
        if existing:
            existing["asked_at"] = _now()
            existing["ask_count"] = int(existing.get("ask_count") or 1) + 1
            existing["text"] = _TAGS.sub("", text)      # refresh display text (counts move)
            out.append({"qid": existing.get("qid"), "text": text})
            continue
        seq += 1
        rec = {"qid": "Q%d" % seq, "text": _TAGS.sub("", text), "key": key,
               "asked_at": _now(), "label": label,
               "ask_count": 1, "answered": False, "num": i + 1}
        open_qs.append(rec)
        out.append({"qid": rec["qid"], "text": text})
    data["question_seq"] = seq
    unanswered = [q for q in open_qs if not q.get("answered")][-_MAX_OPEN_QUESTIONS:]
    answered   = [q for q in open_qs if q.get("answered")][-_MAX_OPEN_QUESTIONS:]
    data["open_questions"] = unanswered + answered
    _save(data)
    return out or fallback


_INTERPRET_SYSTEM = (
    "You are the AI Invoicing Agent for a Florida land-surveying company, and you are NEW to "
    "this job: you must learn from what the team tells you, and you must never guess when money "
    "is involved. You are given (a) the numbered questions you asked in the Teams chat and "
    "(b) new chat messages from the team. Work out which question each message answers.\n\n"
    "Return ONLY valid JSON of this shape:\n"
    "{\"items\":[{\"qid\":\"Q1, or empty if it answers no known question\","
    "\"question\":\"the question text you matched, or empty\","
    "\"answer\":\"a short faithful paraphrase of what they said, MAX 20 words, no quote marks\","
    "\"learning\":\"a durable instruction, in THEIR terms, that should guide future pricing or "
    "handling, written so a future run can apply it; empty if there is nothing to learn\","
    "\"scope\":\"pricing|queue|process|other\","
    "\"confidence\":\"HIGH|MEDIUM|LOW\","
    "\"needs_clarification\":true or false,"
    "\"clarification\":\"if unclear, or if acting on it could wrongly skip or mis-bill work, the "
    "ONE precise question you must ask before acting; else empty\"}]}\n\n"
    "Rules: never invent numbers or order ids.\n"
    "ASK ONCE, THEN COMMIT. You are also given everything you have ALREADY learned and every "
    "clarification you have ALREADY asked. Check both before setting needs_clarification. If the "
    "point is already covered there, or the new answer states a concrete rule you can act on (a "
    "specific order number, date, range or status), set needs_clarification FALSE and simply "
    "record the learning. Re-asking something the team already answered wastes their time and "
    "destroys their trust in you — treat that as a WORSE failure than acting on a slightly "
    "imperfect rule.\n"
    "Set needs_clarification true ONLY when an instruction would SKIP, EXCLUDE, REJECT or STOP "
    "billing AND the concrete scope is genuinely missing from BOTH the answer and what you "
    "already know. Then ask one specific question naming the single missing fact.\n"
    "If they are simply restating or confirming what you already learned, return the item with "
    "needs_clarification false and an empty learning — you already have it.\n\n"
    "WHAT YOU ARE ALLOWED TO LEARN. Your memory is ONLY about orders and their billing. A "
    "learning must be a durable fact or rule about: a price, rate or discount; a client's "
    "negotiated pricing; a service type, tier or line item; how to classify or handle a "
    "particular order, client or property; or which orders are in or out of scope for billing.\n"
    "NEVER learn (return the item with an EMPTY learning) when the message is:\n"
    "  - a report that something is late, stuck, broken, slow or not sent — that is a bug "
    "report for a human, not a rule for you;\n"
    "  - a request for a list, a status, a count or an update, or a question about what you "
    "are doing;\n"
    "  - transient state (\"these five orders are waiting\") — it will be false in an hour;\n"
    "  - about YOUR OWN operation: pausing, stopping, resuming, restarting, deploying, or "
    "opening/closing/locking the sheet or any file. You take NO operational commands from "
    "chat, and you must never record one;\n"
    "  - addressed to another person, or thanks / greetings / chit-chat / your own reports.\n"
    "Do not paraphrase a message back as a rule just because it was said to you. If in doubt, "
    "learn NOTHING: a wrong rule in your memory changes how real money is billed."
)

# Deterministic backstop to the prompt rule above: an instruction about the agent's OWN
# operation must never enter memory, however the model phrases it. On 2026-08-24 "Prateek asks
# that the sheet be closed" was learned as "stop reading and writing to the master sheet and
# pause updates until he says it is okay to resume" — a note A3 would then read as operator
# guidance while pricing. Operational control lives in cron/config, never in chat.
_SELF_OP = re.compile(
    # The object must be one of the agent's OWN actions and must sit close to the verb. A wider
    # window over looser words ("run", "report") misfires on real order rules — it flagged
    # "...should be rejected/skipped ... so they stop appearing as flagged in future runs",
    # which is exactly the kind of billing rule this loop exists to keep.
    r"\b(pause|unpause|resume|stop|halt|suspend|disable|re-?enable|restart|reboot|re-?deploy)\b"
    r"[^.]{0,25}?\b(post|posting|writ|read|sync|updates?|the sheet|the workbook|the spreadsheet|"
    r"the file|the agent|the bot|the pipeline)"
    r"|\b(close|lock|unlock|open)\b[^.]{0,30}?\b(sheet|workbook|spreadsheet|file)\b"
    r"|\bstay paused\b|\buntil .{0,30}\bsays? (it is okay|GO)\b",
    re.I,
)

# Time-bound state: true when written, false an hour later. "Orders 1000288760 through
# 1000288764 had approved prices with quotes not sent; keep them tracked as pending quote-send"
# was learned as scope=queue on 2026-08-24, so the scope gate below would have let it into the
# pricing prompt. Durable memory is for rules, not for today's backlog.
_TRANSIENT = re.compile(
    r"\bnot (yet )?sent\b|\bstill (not|un)sent\b|\bquotes? (are )?unsent\b|\bwith quotes not sent\b"
    r"|\bpending quote-send\b|\bsit(ting)? unsent\b|\bkeep them tracked\b|\bis stuck at\b"
    r"|\bfalls behind\b|\bhas not been (sent|processed|picked)\b"
    r"|\bvalidation is confirmed complete\b",
    re.I,
)

# Only these scopes are injected into A3's pricing prompt as [OPERATOR GUIDANCE]. Anything
# else is still remembered (teams_learnings, for the audit trail and the chat reply) but is
# kept out of the prompt that decides what a client is charged.
_PRICING_SCOPES = ("pricing", "queue")


def ingest_replies() -> dict:
    """Read new chat replies, learn from them, and queue clarifications.

    Returns {"read": n, "learned": n, "clarifications": n, "items": [...], "enabled": bool}.
    Never raises."""
    result = {"read": 0, "learned": 0, "clarifications": 0, "items": [], "enabled": False}
    if not TEAMS_LEARNING_ENABLED:
        return result
    if not resolve_chat_id():
        log.info("teams_learning: no chat id resolved — learning loop idle (set TEAMS_CHAT_ID)")
        return result
    result["enabled"] = True

    data = _load()
    if not data:
        return result
    processed = set(data.get("processed_message_ids") or [])

    msgs = fetch_messages(limit=_MAX_MSGS)
    fresh = [m for m in msgs
             if m.get("id") and m["id"] not in processed and not m.get("is_bot") and m.get("text")]
    result["read"] = len(fresh)
    if not fresh:
        return result

    open_qs = [q for q in (data.get("open_questions") or []) if isinstance(q, dict)]
    prior_learnings = [x for x in (data.get("teams_learnings") or []) if isinstance(x, dict)]
    prior_clarifs   = [c for c in (data.get("pending_clarifications") or []) if isinstance(c, dict)]
    # Without this context the model has amnesia every cycle and re-derives the same doubt,
    # which is exactly how the team got asked the same thing five times on 2026-08-19.
    payload = json.dumps({
        "questions_i_asked": [{"qid": q.get("qid"), "text": q.get("text")} for q in open_qs],
        "already_learned": [{"qid": x.get("qid"), "learning": x.get("learning")}
                            for x in prior_learnings[-25:]],
        "already_asked_clarifications": [c.get("clarification") for c in prior_clarifs[-15:]],
        "new_messages": [{"from": m["from"], "at": m["created"], "text": m["text"][:1500]}
                         for m in reversed(fresh)],   # oldest first for readability
    }, indent=2, default=str)

    try:
        raw = llm_call(model=HUMAN_GATE_MODEL, system=_INTERPRET_SYSTEM, user=payload,
                       max_tokens=4000, thinking=True, effort="high").strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        items = (json.loads(raw) or {}).get("items") or []
    except Exception as exc:
        log.warning("teams_learning: interpretation failed (%s) — messages left unprocessed", exc)
        return result          # leave ids unprocessed so we retry next cycle

    guidance  = data.setdefault("user_guidance", [])
    learnings = data.setdefault("teams_learnings", [])
    clarifs   = data.setdefault("pending_clarifications", [])
    q_by_id   = {q.get("qid"): q for q in open_qs}
    q_by_key  = {(q.get("key") or _topic_key(q.get("text", ""))): q for q in open_qs}
    who       = ", ".join(sorted({m["from"] for m in fresh}))

    # Deterministic anti-nag guards. The prompt asks the model to stop re-asking; these make
    # sure it CANNOT, however it words the question. Both are cheap and both are needed:
    # the topic key catches a re-worded duplicate, the per-question cap catches the drift
    # ("what is the cutoff?" -> "confirm the cutoff?" -> "confirm permanently?") that got the
    # team asked the same thing five times in three hours on 2026-08-19.
    seen_learn = {_topic_key(x.get("learning", "")) for x in learnings if isinstance(x, dict)}
    asked_keys = {_topic_key(c.get("clarification", "")) for c in clarifs if isinstance(c, dict)}
    clar_count = {}
    for c in clarifs:
        if isinstance(c, dict):
            k = (c.get("qid") or "").strip() or "_none"
            clar_count[k] = clar_count.get(k, 0) + 1

    for it in items:
        if not isinstance(it, dict):
            continue
        qid      = (it.get("qid") or "").strip()
        question = (it.get("question") or (q_by_id.get(qid) or {}).get("text") or "").strip()
        answer   = (it.get("answer") or "").strip()
        learning = (it.get("learning") or "").strip()
        if learning and _SELF_OP.search(learning):
            log.warning("teams_learning: REFUSING to learn a self-operation instruction from "
                        "chat: %s", learning[:110])
            learning = ""
        if learning and _TRANSIENT.search(learning):
            log.warning("teams_learning: REFUSING to learn transient status as a durable rule: "
                        "%s", learning[:110])
            learning = ""
        if learning and _topic_key(learning) in seen_learn:
            log.info("teams_learning: already know this, not re-learning: %s", learning[:70])
            learning = ""            # a restatement, not new knowledge
        if learning:
            seen_learn.add(_topic_key(learning))
            scope = (it.get("scope") or "other").strip().lower()
            # The estimator's existing channel: A3 injects user_guidance as [OPERATOR GUIDANCE].
            # Gate it on scope so only pricing/queue rules can influence what a client is
            # charged; process/other notes are remembered but stay out of the pricing prompt.
            if scope in _PRICING_SCOPES:
                note = learning + " (from the team in Teams chat"
                note += (", re: " + question[:90] + ")") if question else ")"
                guidance.append({
                    "order_id": "", "client": "", "service": "",
                    "note": note, "source": "teams_chat", "observed_at": _now(),
                })
            else:
                log.info("teams_learning: scope=%s — remembering but NOT injecting into pricing: "
                         "%s", scope, learning[:90])
            learnings.append({
                "qid": qid, "question": question, "answer": answer, "learning": learning,
                "scope": it.get("scope") or "other",
                "confidence": it.get("confidence") or "MEDIUM",
                "from": who, "at": _now(),
            })
            result["learned"] += 1
            # Mark the question answered so we stop re-asking it. Match on qid first, then
            # on topic key (the model may echo the question text rather than the id).
            target = q_by_id.get(qid) or q_by_key.get(_topic_key(question))
            if target:
                target["answered"] = True
                target["answered_at"] = _now()
        if it.get("needs_clarification") and (it.get("clarification") or "").strip():
            text = it["clarification"].strip()
            bucket = qid or "_none"
            if _topic_key(text) in asked_keys:
                log.info("teams_learning: skipping already-asked clarification: %s", text[:70])
            elif clar_count.get(bucket, 0) >= _MAX_CLARIFY_PER_Q:
                log.warning("teams_learning: clarification cap hit for %s — acting on what the "
                            "team already said instead of asking again: %s", bucket, text[:70])
            else:
                asked_keys.add(_topic_key(text))
                clar_count[bucket] = clar_count.get(bucket, 0) + 1
                clarifs.append({
                    "qid": qid, "question": question, "answer": answer,
                    "clarification": text, "from": who, "at": _now(), "asked": False,
                })
                result["clarifications"] += 1
        result["items"].append(it)

    processed.update(m["id"] for m in fresh)
    data["processed_message_ids"]  = list(processed)[-_MAX_PROCESSED_IDS:]
    data["user_guidance"]          = guidance[-400:]
    data["teams_learnings"]        = learnings[-200:]
    data["pending_clarifications"] = clarifs[-40:]
    _save(data)
    log.info("teams_learning: read=%d learned=%d clarifications=%d",
             result["read"], result["learned"], result["clarifications"])
    return result


def is_answered(question_text: str) -> bool:
    """True if the team already answered this exact question — so we stop re-asking it.

    Once answered, any remaining ambiguity is carried by a pending clarification instead;
    repeating the original question would just nag the team with something they replied to."""
    key = _topic_key(question_text)
    for q in (_load().get("open_questions") or []):
        if isinstance(q, dict) and (q.get("key") or _topic_key(q.get("text", ""))) == key:
            return bool(q.get("answered"))
    return False


def recent_learnings(limit: int = 4) -> list:
    """Newest learnings absorbed from the chat (for the report)."""
    return [x for x in (_load().get("teams_learnings") or []) if isinstance(x, dict)][-limit:]


def take_pending_clarifications(limit: int = 3, mark_asked: bool = True) -> list:
    """Clarifications to ask in this report. Marks them asked so we don't nag every cycle."""
    data = _load()
    if not data:
        return []
    pend = [c for c in (data.get("pending_clarifications") or []) if isinstance(c, dict)]
    todo = [c for c in pend if not c.get("asked")][:limit]
    if todo and mark_asked:
        for c in todo:
            c["asked"] = True
            c["asked_at"] = _now()
        data["pending_clarifications"] = pend
        _save(data)
    return todo
