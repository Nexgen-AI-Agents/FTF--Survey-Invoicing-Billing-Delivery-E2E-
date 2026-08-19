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
    "\"answer\":\"a short faithful quote or paraphrase of what they said\","
    "\"learning\":\"a durable instruction, in THEIR terms, that should guide future pricing or "
    "handling, written so a future run can apply it; empty if there is nothing to learn\","
    "\"scope\":\"pricing|queue|process|other\","
    "\"confidence\":\"HIGH|MEDIUM|LOW\","
    "\"needs_clarification\":true or false,"
    "\"clarification\":\"if unclear, or if acting on it could wrongly skip or mis-bill work, the "
    "ONE precise question you must ask before acting; else empty\"}]}\n\n"
    "Rules: never invent numbers or order ids. If an instruction would make you SKIP, EXCLUDE, "
    "REJECT or STOP billing anything, set needs_clarification true and ask for the exact scope "
    "(which orders, which date range, which status) — skipping real work loses money, so a human "
    "must confirm it. Ignore your own posted reports and pure chit-chat: return no item for them."
)


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
    payload = json.dumps({
        "questions_i_asked": [{"qid": q.get("qid"), "text": q.get("text")} for q in open_qs],
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

    for it in items:
        if not isinstance(it, dict):
            continue
        qid      = (it.get("qid") or "").strip()
        question = (it.get("question") or (q_by_id.get(qid) or {}).get("text") or "").strip()
        answer   = (it.get("answer") or "").strip()
        learning = (it.get("learning") or "").strip()
        if learning:
            # The estimator's existing channel: A3 injects user_guidance as [OPERATOR GUIDANCE].
            note = learning + " (from the team in Teams chat"
            note += (", re: " + question[:90] + ")") if question else ")"
            guidance.append({
                "order_id": "", "client": "", "service": "",
                "note": note, "source": "teams_chat", "observed_at": _now(),
            })
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
            clarifs.append({
                "qid": qid, "question": question, "answer": answer,
                "clarification": it["clarification"].strip(),
                "from": who, "at": _now(), "asked": False,
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
