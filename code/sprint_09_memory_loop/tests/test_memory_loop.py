"""
Sprint 9 — Memory Loop unit tests

All DB and filesystem interactions are mocked.
Tests verify:
  1. memory_manager writes a daily log file
  2. memory_manager groups decisions by agent correctly
  3. memory_manager counts error decisions correctly
  4. memory_manager handles empty DB gracefully
  5. dream_processor writes / appends reflection.md
  6. dream_processor flags agents exceeding error threshold
  7. dream_processor handles zero rows without crashing
  8. orchestrator logs loop_start and loop_complete decisions
  9. save_loop_state is called with 'running' then 'completed'
"""

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "shared"))

# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_row(agent: str, decision: str, order_id: str = "ORD-001",
              created_at=None) -> dict:
    if created_at is None:
        created_at = datetime(2026, 5, 26, 10, 0, 0, tzinfo=timezone.utc)
    return {
        "agent_name": agent,
        "decision": decision,
        "order_id": order_id,
        "reason": f"{agent} did {decision}",
        "input_summary": None,
        "output_summary": None,
        "model_used": None,
        "created_at": created_at,
    }


SAMPLE_ROWS = [
    _make_row("agent_02_monitor",    "new_order_found"),
    _make_row("agent_03_classifier", "classified"),
    _make_row("agent_03_classifier", "error"),
    _make_row("agent_05_pricing",    "priced"),
    _make_row("agent_06_writer",     "written"),
    _make_row("agent_07_reviewer",   "approved"),
    _make_row("agent_08_sender",     "sent"),
]


# ── memory_manager tests ──────────────────────────────────────────────────────

class TestMemoryManager:

    @patch("memory.memory_manager.log_decision")
    @patch("memory.memory_manager.get_decisions_for_date", return_value=SAMPLE_ROWS)
    def test_writes_daily_log_file(self, mock_db, mock_log, tmp_path):
        """Memory manager must write a dated markdown file."""
        import memory.memory_manager as mm
        mm.MEMORY_DIR = tmp_path / "memory"

        result = mm.run(date(2026, 5, 26))

        assert result.exists(), "Daily log file was not created"
        assert "2026-05-26" in result.name

    @patch("memory.memory_manager.log_decision")
    @patch("memory.memory_manager.get_decisions_for_date", return_value=SAMPLE_ROWS)
    def test_groups_by_agent(self, mock_db, mock_log, tmp_path):
        """Log must contain a section for each agent in the decision rows."""
        import memory.memory_manager as mm
        mm.MEMORY_DIR = tmp_path / "memory"

        path = mm.run(date(2026, 5, 26))
        content = path.read_text(encoding="utf-8")

        assert "agent_02_monitor" in content
        assert "agent_03_classifier" in content
        assert "agent_08_sender" in content

    @patch("memory.memory_manager.log_decision")
    @patch("memory.memory_manager.get_decisions_for_date", return_value=SAMPLE_ROWS)
    def test_counts_errors_correctly(self, mock_db, mock_log, tmp_path):
        """Error count for agent_03 must show 1 (one 'error' decision)."""
        import memory.memory_manager as mm
        mm.MEMORY_DIR = tmp_path / "memory"

        path = mm.run(date(2026, 5, 26))
        content = path.read_text(encoding="utf-8")

        # agent_03 has 2 total, 1 error → 50%
        assert "50%" in content

    @patch("memory.memory_manager.log_decision")
    @patch("memory.memory_manager.get_decisions_for_date", return_value=[])
    def test_empty_db_no_crash(self, mock_db, mock_log, tmp_path):
        """Empty decision log must produce a valid (empty) markdown file."""
        import memory.memory_manager as mm
        mm.MEMORY_DIR = tmp_path / "memory"

        path = mm.run(date(2026, 5, 26))

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Total decisions logged:** 0" in content

    @patch("memory.memory_manager.log_decision")
    @patch("memory.memory_manager.get_decisions_for_date", return_value=SAMPLE_ROWS)
    def test_also_writes_latest_md(self, mock_db, mock_log, tmp_path):
        """latest.md must be updated alongside the dated file."""
        import memory.memory_manager as mm
        mm.MEMORY_DIR = tmp_path / "memory"

        mm.run(date(2026, 5, 26))

        assert (tmp_path / "memory" / "latest.md").exists()


# ── dream_processor tests ─────────────────────────────────────────────────────

HIGH_ERROR_ROWS = [
    _make_row("agent_06_writer", "written"),
    _make_row("agent_06_writer", "error"),
    _make_row("agent_06_writer", "error"),   # 2/3 = 67% — above threshold
    _make_row("agent_08_sender", "sent"),
]


class TestDreamProcessor:

    @patch("memory.dream_processor.log_decision")
    @patch("memory.dream_processor.get_decisions_since", return_value=SAMPLE_ROWS)
    def test_writes_reflection_file(self, mock_db, mock_log, tmp_path):
        """Dream processor must write reflection.md."""
        import memory.dream_processor as dp
        dp.REFLECTION_PATH = tmp_path / "reflection.md"

        result = dp.run()

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "System Reflection Log" in content

    @patch("memory.dream_processor.log_decision")
    @patch("memory.dream_processor.get_decisions_since", return_value=HIGH_ERROR_ROWS)
    def test_flags_high_error_rate_agent(self, mock_db, mock_log, tmp_path):
        """Agents with >10% error rate must appear in the flagged list."""
        import memory.dream_processor as dp
        dp.REFLECTION_PATH = tmp_path / "reflection.md"

        dp.run()
        content = (tmp_path / "reflection.md").read_text(encoding="utf-8")

        assert "agent_06_writer" in content
        assert "NEEDS ATTENTION" in content

    @patch("memory.dream_processor.log_decision")
    @patch("memory.dream_processor.get_decisions_since", return_value=[])
    def test_zero_rows_no_crash(self, mock_db, mock_log, tmp_path):
        """Dream processor must not crash when no decisions exist."""
        import memory.dream_processor as dp
        dp.REFLECTION_PATH = tmp_path / "reflection.md"

        path = dp.run()
        assert path.exists()

    @patch("memory.dream_processor.log_decision")
    @patch("memory.dream_processor.get_decisions_since", return_value=SAMPLE_ROWS)
    def test_appends_on_second_run(self, mock_db, mock_log, tmp_path):
        """Second run must append a new entry, not overwrite the file."""
        import memory.dream_processor as dp
        dp.REFLECTION_PATH = tmp_path / "reflection.md"

        dp.run()
        first_size = (tmp_path / "reflection.md").stat().st_size

        dp.run()
        second_size = (tmp_path / "reflection.md").stat().st_size

        assert second_size > first_size, "Second run did not append to reflection.md"


# ── orchestrator tests ────────────────────────────────────────────────────────

class TestOrchestrator:

    @patch("agent_01_orchestrator._reporter")
    @patch("agent_01_orchestrator._sender")
    @patch("agent_01_orchestrator._reviewer")
    @patch("agent_01_orchestrator._writer")
    @patch("agent_01_orchestrator._human_gate")
    @patch("agent_01_orchestrator._pricing")
    @patch("agent_01_orchestrator._classifier")
    @patch("agent_01_orchestrator._monitor")
    @patch("agent_01_orchestrator.save_loop_state")
    @patch("agent_01_orchestrator.log_decision")
    def test_logs_loop_start_and_complete(
        self, mock_log, mock_save,
        mock_monitor, mock_classifier, mock_pricing,
        mock_human_gate, mock_writer, mock_reviewer,
        mock_sender, mock_reporter,
    ):
        """Orchestrator must log loop_start and loop_complete decisions."""
        for m in [mock_monitor, mock_classifier, mock_pricing,
                  mock_human_gate, mock_writer, mock_reviewer,
                  mock_sender, mock_reporter]:
            m.run.return_value = None

        import agent_01_orchestrator as orch
        orch.run()

        decisions = [c.args[1] for c in mock_log.call_args_list]
        assert "loop_start" in decisions
        assert "loop_complete" in decisions

    @patch("agent_01_orchestrator._reporter")
    @patch("agent_01_orchestrator._sender")
    @patch("agent_01_orchestrator._reviewer")
    @patch("agent_01_orchestrator._writer")
    @patch("agent_01_orchestrator._human_gate")
    @patch("agent_01_orchestrator._pricing")
    @patch("agent_01_orchestrator._classifier")
    @patch("agent_01_orchestrator._monitor")
    @patch("agent_01_orchestrator.save_loop_state")
    @patch("agent_01_orchestrator.log_decision")
    def test_save_loop_state_running_then_completed(
        self, mock_log, mock_save,
        mock_monitor, mock_classifier, mock_pricing,
        mock_human_gate, mock_writer, mock_reviewer,
        mock_sender, mock_reporter,
    ):
        """save_loop_state must be called with 'running' first, then 'completed'."""
        for m in [mock_monitor, mock_classifier, mock_pricing,
                  mock_human_gate, mock_writer, mock_reviewer,
                  mock_sender, mock_reporter]:
            m.run.return_value = None

        import agent_01_orchestrator as orch
        orch.run()

        states = [c.args[1] for c in mock_save.call_args_list]
        assert states[0] == "running"
        assert states[-1] == "completed"
