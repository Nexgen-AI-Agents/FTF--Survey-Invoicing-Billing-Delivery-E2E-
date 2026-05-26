"""
agent_00_listener.py — Real-Time Order Change Listener

Listens on the PostgreSQL 'order_state_changed' channel.  A DB trigger fires
pg_notify whenever processed_orders is INSERTed or its status changes.

When a 'pending' order notification arrives, the full estimate pipeline
(agents 2–9) is triggered immediately — eliminating the 60-minute GitHub
Actions polling lag between each pipeline step.

Deployment:
  python code/sprint_09_memory_loop/agents/agent_00_listener.py

Or via .github/workflows/order_listener.yml (auto-restarts every ~6 hours).

Design:
  - Uses psycopg2 synchronous LISTEN + select.select (works on Windows and Linux)
  - Guards against concurrent pipeline runs via loop_state table
  - Exits cleanly on SIGTERM / SIGINT or after MAX_RUNTIME_S
"""

import os
import select
import signal
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from core.db import get_listen_connection, get_loop_state, log_decision
from core.logger import get_logger

AGENT_NAME  = "agent_00_listener"
CHANNEL     = "order_state_changed"
POLL_TIMEOUT_S = 5        # select.select timeout between heartbeat logs
MAX_RUNTIME_S  = 21_000   # 5h50m — safely under GitHub Actions 6h limit

log = get_logger(AGENT_NAME)

# Module-level placeholder — replaced by _load_orchestrator() on first use;
# mocks replace it in tests before run() is called.
_orchestrator = None

_running = True


def _handle_signal(signum, frame):
    global _running
    log.info("shutdown signal received signum=%s", signum)
    _running = False


def _load_orchestrator():
    """Lazy-load the orchestrator once; skip if already loaded or mocked."""
    global _orchestrator
    if _orchestrator is not None:
        return
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    import agent_01_orchestrator
    _orchestrator = agent_01_orchestrator


def _trigger_pipeline(order_id: str, status: str) -> None:
    """Trigger the estimate pipeline if not already running."""
    state = get_loop_state("estimate_generation")
    if state and state.get("status") == "running":
        log.info(
            "pipeline already running — order=%s will be picked up in current cycle",
            order_id,
        )
        return

    log.info("triggering pipeline order=%s status=%s", order_id, status)
    log_decision(
        AGENT_NAME, "pipeline_triggered",
        order_id=order_id,
        reason=f"NOTIFY received on channel={CHANNEL} status={status}",
    )

    _load_orchestrator()
    _orchestrator.run()


def run(max_runtime_s: int = MAX_RUNTIME_S) -> None:
    """
    Main listener loop.

    Opens a LISTEN connection, waits for notifications, and triggers the
    pipeline on each 'pending' status event.  Exits after max_runtime_s
    seconds or on SIGTERM/SIGINT.
    """
    global _running
    _running = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    started_at = time.monotonic()
    conn = get_listen_connection(CHANNEL)
    log_decision(AGENT_NAME, "listener_started",
                 reason=f"channel={CHANNEL} max_runtime={max_runtime_s}s")
    log.info("listener started channel=%s", CHANNEL)

    try:
        while _running:
            elapsed = time.monotonic() - started_at
            if elapsed >= max_runtime_s:
                log.info("max runtime reached elapsed=%.0fs — exiting", elapsed)
                break

            # Block for up to POLL_TIMEOUT_S waiting for DB activity
            readable, _, _ = select.select([conn], [], [], POLL_TIMEOUT_S)
            if not readable:
                continue  # heartbeat timeout — no notifications, loop back

            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                payload = notify.payload
                log.info("notify channel=%s payload=%s", notify.channel, payload)
                try:
                    order_id, status = payload.split(":", 1)
                    if status == "pending":
                        _trigger_pipeline(order_id, status)
                    else:
                        log.debug(
                            "notify status=%s — orchestrator handles mid-pipeline "
                            "steps; no immediate action needed", status
                        )
                except ValueError:
                    log.error("malformed notify payload=%r — expected 'order_id:status'",
                              payload)
                except Exception as exc:
                    log.error("error handling notify payload=%r: %s", payload, exc)

    finally:
        elapsed = time.monotonic() - started_at
        log_decision(AGENT_NAME, "listener_stopped",
                     reason=f"runtime={elapsed:.0f}s")
        conn.close()
        log.info("listener stopped runtime=%.0fs", elapsed)


if __name__ == "__main__":
    run()
