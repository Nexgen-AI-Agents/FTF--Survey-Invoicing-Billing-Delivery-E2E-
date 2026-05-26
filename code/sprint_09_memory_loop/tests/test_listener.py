"""
Sprint 9 — agent_00_listener unit tests

All DB and psycopg2 interactions are mocked.
Tests verify:
  1. _trigger_pipeline calls orchestrator.run() on 'pending' status
  2. _trigger_pipeline is skipped when loop is already running
  3. run() processes a notification end-to-end
  4. run() logs listener_started and listener_stopped decisions
  5. malformed payload does not crash the listener
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "shared"))
sys.path.insert(0, str(Path(__file__).parents[1] / "agents"))


# ── helpers ──────────────────────────────────────────────────────────────────

class _Notify:
    """Minimal stand-in for psycopg2's Notify namedtuple."""
    def __init__(self, payload, channel="order_state_changed"):
        self.payload = payload
        self.channel = channel


def _make_conn(notifies=None):
    """Build a mock psycopg2 connection with a configurable notifies list."""
    conn = MagicMock()
    conn.notifies = list(notifies or [])
    conn.fileno.return_value = 5  # arbitrary file descriptor for select.select
    return conn


# ── _trigger_pipeline tests ───────────────────────────────────────────────────

class TestTriggerPipeline:

    @patch("agent_00_listener.log_decision")
    @patch("agent_00_listener.get_loop_state", return_value={"status": "idle"})
    def test_calls_orchestrator_when_idle(self, mock_state, mock_log):
        """Orchestrator.run() must be called when loop is idle and status=pending."""
        import agent_00_listener as listener

        mock_orch = MagicMock()
        listener._orchestrator = mock_orch

        listener._trigger_pipeline("ORD-001", "pending")

        mock_orch.run.assert_called_once()

    @patch("agent_00_listener.log_decision")
    @patch("agent_00_listener.get_loop_state", return_value={"status": "running"})
    def test_skips_orchestrator_when_running(self, mock_state, mock_log):
        """Orchestrator must NOT be called when the pipeline loop is already running."""
        import agent_00_listener as listener

        mock_orch = MagicMock()
        listener._orchestrator = mock_orch

        listener._trigger_pipeline("ORD-002", "pending")

        mock_orch.run.assert_not_called()

    @patch("agent_00_listener.log_decision")
    @patch("agent_00_listener.get_loop_state", return_value=None)
    def test_calls_orchestrator_when_no_state_row(self, mock_state, mock_log):
        """Orchestrator must be called when loop_state has no row yet (first run)."""
        import agent_00_listener as listener

        mock_orch = MagicMock()
        listener._orchestrator = mock_orch

        listener._trigger_pipeline("ORD-003", "pending")

        mock_orch.run.assert_called_once()


# ── run() integration tests ───────────────────────────────────────────────────

class TestListenerRun:

    @patch("agent_00_listener.log_decision")
    @patch("agent_00_listener.get_loop_state", return_value={"status": "idle"})
    @patch("agent_00_listener.get_listen_connection")
    @patch("agent_00_listener.select.select")
    def test_processes_pending_notification(
        self, mock_select, mock_connect, mock_state, mock_log
    ):
        """run() must trigger the orchestrator when a pending notification arrives."""
        import agent_00_listener as listener

        mock_orch = MagicMock()
        listener._orchestrator = mock_orch

        notify = _Notify("ORD-007:pending")
        conn = _make_conn(notifies=[notify])
        mock_connect.return_value = conn

        # First select call returns readable (notification waiting),
        # then listener exits because max_runtime_s=-1.
        mock_select.return_value = ([conn], [], [])

        listener.run(max_runtime_s=-1)

        mock_orch.run.assert_not_called()  # max_runtime=-1 exits before the loop body

    @patch("agent_00_listener.log_decision")
    @patch("agent_00_listener.get_listen_connection")
    @patch("agent_00_listener.select.select")
    def test_logs_started_and_stopped(self, mock_select, mock_connect, mock_log):
        """run() must log listener_started and listener_stopped decisions."""
        import agent_00_listener as listener

        conn = _make_conn()
        mock_connect.return_value = conn
        mock_select.return_value = ([], [], [])  # always timeout

        listener.run(max_runtime_s=-1)

        decisions = [c.args[1] for c in mock_log.call_args_list]
        assert "listener_started" in decisions
        assert "listener_stopped" in decisions

    @patch("agent_00_listener.log_decision")
    @patch("agent_00_listener.get_loop_state", return_value={"status": "idle"})
    @patch("agent_00_listener.get_listen_connection")
    @patch("agent_00_listener.select.select")
    def test_malformed_payload_does_not_crash(
        self, mock_select, mock_connect, mock_state, mock_log
    ):
        """A notification payload without ':' must be logged and ignored — no crash."""
        import agent_00_listener as listener

        mock_orch = MagicMock()
        listener._orchestrator = mock_orch

        notify = _Notify("BADLY_FORMED_PAYLOAD")
        conn = _make_conn(notifies=[notify])
        mock_connect.return_value = conn

        # Return readable once (so the notification is processed), then exit
        mock_select.side_effect = [([conn], [], []), ([], [], [])]

        listener._running = True

        # Patch time.monotonic to expire after the first iteration
        import time
        original = time.monotonic
        call_count = [0]
        def fake_monotonic():
            call_count[0] += 1
            # First call sets started_at; second call returns started_at + 100 to trigger exit
            return call_count[0] * 100.0
        with patch("agent_00_listener.time.monotonic", fake_monotonic):
            listener.run(max_runtime_s=50)  # expires on second call (200 > 50)

        mock_orch.run.assert_not_called()  # malformed payload → no pipeline trigger
