"""
agent_01_orchestrator.py — The Brain of the FTF Agentic AI OS

HIERARCHY ROLE:
    Reports to    : Real Prateek (human) via GitHub Actions / Claude Code
    Manages       : All pipeline agents (2–18)
    Guided by     : TEAM/orchestrator/orchestrator_brain.md
    Routes work   : See TEAM/orchestrator/routing_guide.md
    Never skips   : Failure → Teams alert → log → escalate

MODE 1 — Pipeline Runner (AUTO, GitHub Actions 24/7):
    Agent 12 — Email Monitor  (check info@ for customer quote approvals; quote→pending)
    Agent 2  — Monitor        (detect new FTF orders in Quote status)
    Agent 3  — Classifier     (9 flag triggers: competitor, ALTA, Monroe, VE zone, etc.)
    Agent 4  — Human Gate     (route flagged → Teams; APPROVE/REJECT/DEFER commands)
    Agent 5  — Pricing        (county production avg + B2B multiplier + complexity if enabled)
    Agent 6  — Writer         (estimate email — FL PSM persona + change order clause)
    Agent 7  — Reviewer       (self-correction up to 3 loops)
    Agent 8  — Sender         (send via FTF Books, 8 AM–6 PM ET only, 6–13 min delay)
    Agent 9  — Reporter       (daily Teams digest at end of cycle)

MODE 2 — Runtime Brain (routes non-pipeline work to the right agent/team):
    See TEAM/orchestrator/routing_guide.md for dispatch logic.

AR Loop   : Agents 10–11 (ar_followup.yml — separate workflow)
Statements: Agents 15–17 (monthly_statements.yml — separate workflow)
Memory    : Agent 13 Pricing Trainer + Memory Manager + Dream Processor (nightly)
Analysis  : Agent 18 Business Analyst (on-demand)
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


def _alert_on_anomaly(summary: dict) -> None:
    """Post a Teams alert if the pipeline cycle shows concerning patterns.

    Hierarchy rule: Orchestrator never silently fails. Any anomaly that the
    human team should know about gets surfaced immediately.
    """
    from core.teams_graph_client import send_channel_message
    try:
        if summary["errors"] >= 3:
            send_channel_message(
                f"<h3>&#9888; Orchestrator — {summary['errors']} errors in estimate loop cycle</h3>"
                f"<p>Multiple pipeline steps failed this cycle. Check logs.</p>",
                subject="Orchestrator: multiple errors"
            )
    except Exception:
        pass  # notification failure must not crash the loop itself


def run_estimate_loop() -> dict:
    """Execute one full cycle of the estimate generation pipeline.

    Hierarchy: Orchestrator (Agent 1) manages pipeline agents 2–9 and 12.
    Each step is a delegation to a specialist agent. Failures are logged,
    counted, and surfaced — never silently dropped.

    GitHub Actions runs this every 60 minutes via estimate_generation.yml.
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

    # Escalation check — runs every cycle; escalates orders stuck >24h in awaiting_approval
    try:
        _run_step("escalation_check", _human_gate.run_escalation_check)
    except AgentError as exc:
        summary["errors"] += 1
        log.warning("escalation_check failed (non-critical): %s", exc)

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
    _alert_on_anomaly(summary)
    return summary


def run() -> dict:
    """Entry point called by GitHub Actions and tests.

    Hierarchy: this is the Orchestrator's main activation point.
    GitHub Actions (estimate_generation.yml) calls this every 60 min.
    Real Prateek can also trigger via workflow_dispatch for manual runs.
    """
    return run_estimate_loop()


if __name__ == "__main__":
    result = run()
    print(result)
