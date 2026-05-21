import pytest
from unittest.mock import MagicMock, patch, call
from core.db import get_pending_order, save_order_state, log_decision, get_unprocessed_reminder, order_exists
from core.exceptions import AgentError


@pytest.fixture
def mock_cursor():
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.rowcount = 1
    return cur


@patch("core.db._get_cursor")
def test_get_pending_order_returns_none_when_empty(mock_ctx, mock_cursor):
    mock_ctx.return_value.__enter__ = lambda s: mock_cursor
    mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = None
    result = get_pending_order()
    assert result is None


@patch("core.db._get_cursor")
def test_get_pending_order_returns_dict(mock_ctx, mock_cursor):
    mock_ctx.return_value.__enter__ = lambda s: mock_cursor
    mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = {"order_id": "ORD-001", "status": "pending"}
    result = get_pending_order()
    assert result == {"order_id": "ORD-001", "status": "pending"}


@patch("core.db._get_cursor")
def test_save_order_state_raises_on_invalid_column(mock_ctx, mock_cursor):
    mock_ctx.return_value.__enter__ = lambda s: mock_cursor
    mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
    with pytest.raises(AgentError, match="unknown columns"):
        save_order_state("ORD-001", nonexistent_field="value")


@patch("core.db._get_cursor")
def test_save_order_state_upserts_on_no_row(mock_ctx, mock_cursor):
    mock_ctx.return_value.__enter__ = lambda s: mock_cursor
    mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
    mock_cursor.rowcount = 0  # triggers INSERT path
    save_order_state("ORD-001", status="classified")
    assert mock_cursor.execute.call_count == 2  # UPDATE then INSERT


@patch("core.db._get_cursor")
def test_order_exists_returns_true_when_found(mock_ctx, mock_cursor):
    mock_ctx.return_value.__enter__ = lambda s: mock_cursor
    mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = {"1": 1}
    result = order_exists("ORD-001")
    assert result is True


@patch("core.db._get_cursor")
def test_order_exists_returns_false_when_not_found(mock_ctx, mock_cursor):
    mock_ctx.return_value.__enter__ = lambda s: mock_cursor
    mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = None
    result = order_exists("ORD-999")
    assert result is False


@patch("core.db._get_cursor")
def test_log_decision_inserts_row(mock_ctx, mock_cursor):
    mock_ctx.return_value.__enter__ = lambda s: mock_cursor
    mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
    log_decision("agent_03_classifier", "classified", order_id="ORD-001", reason="Boundary Survey")
    mock_cursor.execute.assert_called_once()
    sql = mock_cursor.execute.call_args[0][0]
    assert "INSERT INTO agent_decision_log" in sql
