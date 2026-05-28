"""
agent_01_orchestrator.py — Estimate Generation Loop Orchestrator

Runs the full estimate pipeline once per invocation (GitHub Actions calls this
every 60 minutes via estimate_generation.yml).

Pipeline sequence:
    Agent 12 — Email Monitor  (check info@ for customer quote approvals; quote→pending)
    Agent 2  — Monitor        (detect new FTF orders)
    Agent 3  — Classifier     (14 flag checks)
    Agent 4  — Human Gate     (route flagged orders)
    Agent 5  — Pricing        (county-based + commercial pricing)
    Agent 6  — Writer         (generate estimate email)
    Agent 7  — Reviewer       (4-check validation)
    Agent 8  — Sender         (send via FTF Books, 8 AM–6 PM ET only)
    Agent 9  — Reporter       (daily Teams digest — runs once at end)

AR Loop (Agents 10–14) and Statement Loop (Agents 15–17) are stubbed here;
they have their own GitHub Actions workflows and will be wired in Sprint 7/8.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from core.db import log_decision, save_loop_state
from core.exceptions import AgentError
from core.logger import get_logger

AGENT_NAME = "agent_01_orchestrator"
LOOP_NAME = "estimate_generation"
log = get_logger(AGENT_NAME)

# ── Pipeline agent placeholders (lazy-loaded; mocks replace these in tests) ──
_email_monitor = None
_monitor       = None
_classifier    = None
_pricing       = None
_human_gate    = None
_writer        = None
_reviewer      = None
_sender        = None
_reporter      = None


def _init_agents() -> None:
    """Load pipeline agents on first real run. Skipped when mocks are already in place."""
    global _email_monitor, _monitor, _classifier, _pricing, _human_gate
    global _writer, _reviewer, _sender, _reporter
    if _monitor is not None:
        return  # already loaded or mocked by tests

    _here = os.path.dirname(__file__)
    _code = os.path.join(_here, "..", "..")  # → code/

    sys.path.insert(0, os.path.join(_code, "sprint_01_monitor",            "agents"))
    sys.path.insert(0, os.path.join(_code, "sprint_02_classifier_pricing", "agents"))
    sys.path.insert(0, os.path.join(_code, "sprint_03_human_gate",         "agents"))
    sys.path.insert(0, os.path.join(_code, "sprint_04_writer",             "agents"))
    sys.path.insert(0, os.path.join(_code, "sprint_05_reviewer",           "agents"))
    sys.path.insert(0, os.path.join(_code, "sprint_05_email_monitor",      "agents"))
    sys.path.insert(0, os.path.join(_code, "sprint_06_sender_reporter",    "agents"))

    import agent_02_monitor          as m2;  _monitor       = m2   # noqa: E702
    import agent_03_classifier       as m3;  _classifier    = m3   # noqa: E702
    import agent_05_pricing_engine   as m5;  _pricing       = m5   # noqa: E702
    import agent_04_human_gate       as m4;  _human_gate    = m4   # noqa: E702
    import agent_06_writer           as m6;  _writer        = m6   # noqa: E702
    import agent_07_reviewer         as m7;  _reviewer      = m7   # noqa: E702
    import agent_08_sender           as m8;  _sender        = m8   # noqa: E702
    import agent_09_reporter         as m9;  _reporter      = m9   # noqa: E702
    import agent_12_email_monitor    as m12; _email_monitor = m12  # noqa: E702


# ── Step runners ─────────────────────────────────────────────────────────────

def _run_step(label: str, fn) -> bool:
    """Run one pipeline step. Returns True on success, False on skip (no work), raises on error."""
    try:
        result = fn()
        log.info("step=%s result=%s", label, result)
        return result is not None
    except AgentError as exc:
        log.error("step=%s AgentError: %s", label, exc)
        raise
    except Exception as exc:
        log.error("step=%s unexpected error: %s", label, exc)
        raise AgentError(f"{label} failed: {exc}") from exc


def run_estimate_loop() -> dict:
    """
    Execute one full cycle of the estimate generation pipeline.

    Processes one order per stage per call — the GitHub Actions cron runs this
    every 60 minutes so the pipeline advances across cycles.

    Returns a summary dict with counts of actions taken.
    """
    _init_agents()
    started_at = datetime.now(timezone.utc)
    summary = {
        "loop": LOOP_NAME,
        "started_at": started_at.isoformat(),
        "email_monitor": 0,
        "monitor": 0,
        "classified": 0,
        "priced": 0,
        "flagged": 0,
        "written": 0,
        "reviewed": 0,
        "sent": 0,
        "errors": 0,
    }

    save_loop_state(LOOP_NAME, "running", last_run_at=started_at)
    log_decision(AGENT_NAME, "loop_start",
                 reason=f"estimate loop started at {started_at.isoformat()}")

    steps = [
        ("email_monitor", _email_monitor.run),   # Gap 4: check info@ for customer quote approvals
        ("monitor",       _monitor.run),
        ("classifier",    _classifier.run),
        ("pricing",       _pricing.run),
        ("human_gate",    _human_gate.run),
        ("writer",        _writer.run),
        ("reviewer",      _reviewer.run),
        ("sender",        _sender.run),
    ]

    for label, fn in steps:
        try:
            did_work = _run_step(label, fn)
            if did_work:
                summary[label.split("_")[0]] = summary.get(label.split("_")[0], 0) + 1
        except AgentError as exc:
            summary["errors"] += 1
            log.error("pipeline step %s failed: %s — continuing to next step", label, exc)
            # Non-fatal: log and continue so other orders aren't blocked

    # Daily reporter — send Teams digest once per loop cycle
    try:
        _run_step("reporter", _reporter.run)
    except AgentError as exc:
        log.warning("reporter failed (non-critical): %s", exc)

    finished_at = datetime.now(timezone.utc)
    duration_s = (finished_at - started_at).total_seconds()

    save_loop_state(
        LOOP_NAME,
        "completed",
        last_run_at=started_at,
        error_count=summary["errors"],
    )
    log_decision(
        AGENT_NAME, "loop_complete",
        reason=f"cycle done in {duration_s:.1f}s errors={summary['errors']}",
        output_summary=str(summary),
    )
    log.info("estimate loop complete duration=%.1fs summary=%s", duration_s, summary)
    return summary


def run() -> dict:
    """Entry point called by GitHub Actions and tests."""
    return run_estimate_loop()


if __name__ == "__main__":
    result = run()
    print(result)
