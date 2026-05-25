import pytest
from unittest.mock import patch, MagicMock

from agents.agent_04_human_gate import (
    notify_human,
    check_approval,
    run,
    AGENT_NAME,
    STATUS_AWAITING,
    STATUS_APPROVED,
    STATUS_REJECTED,
)
from core.exceptions import AgentError


# ── shared fixtures ───────────────────────────────────────────────────────────

_FLAGGED_ROW = {
    "order_id": "ORD-001",
    "status": "flagged",
    "service_type": "Boundary Survey",
    "property_county": "Broward",
    "property_state": "FL",
    "flag_reason": "competitor company name match: Apex Surveying",
    "estimate_amount": 350.0,
    "flagged_at": "2026-05-25T10:00:00+00:00",
}

_TEAMS_URL = "https://outlook.office.com/webhook/test"


def _patch_notify(db_row=None, teams_status=200, webhook_url=_TEAMS_URL):
    """Context manager stack: mocks all external calls for notify_human."""
    import contextlib
    row = db_row or _FLAGGED_ROW.copy()
    mock_response = MagicMock()
    mock_response.status_code = teams_status
    mock_response.raise_for_status = (
        MagicMock() if teams_status < 400
        else MagicMock(side_effect=Exception(f"HTTP {teams_status}"))
    )

    return contextlib.ExitStack()  # caller builds patches directly


# ── UT-03-01  Teams webhook POST is called ────────────────────────────────────

def test_notify_posts_to_teams_webhook():
    with patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", _TEAMS_URL), \
         patch("agents.agent_04_human_gate.get_order_by_id", return_value=_FLAGGED_ROW), \
         patch("agents.agent_04_human_gate.httpx.post") as mock_post, \
         patch("agents.agent_04_human_gate.save_order_state"), \
         patch("agents.agent_04_human_gate.log_decision"):
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
        result = notify_human("ORD-001")

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[0][0] == _TEAMS_URL  # first positional arg = URL
    assert result["notified"] is True
    assert result["order_id"] == "ORD-001"


# ── UT-03-02  DB status set to awaiting_approval after notify ────────────────

def test_notify_saves_awaiting_approval_status():
    with patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", _TEAMS_URL), \
         patch("agents.agent_04_human_gate.get_order_by_id", return_value=_FLAGGED_ROW), \
         patch("agents.agent_04_human_gate.httpx.post",
               return_value=MagicMock(status_code=200, raise_for_status=MagicMock())), \
         patch("agents.agent_04_human_gate.save_order_state") as mock_save, \
         patch("agents.agent_04_human_gate.log_decision"):
        notify_human("ORD-001")

    mock_save.assert_called_once()
    args, kwargs = mock_save.call_args
    assert args[0] == "ORD-001"
    assert kwargs["status"] == STATUS_AWAITING


# ── UT-03-03  log_decision called once with correct agent name ────────────────

def test_notify_logs_decision():
    with patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", _TEAMS_URL), \
         patch("agents.agent_04_human_gate.get_order_by_id", return_value=_FLAGGED_ROW), \
         patch("agents.agent_04_human_gate.httpx.post",
               return_value=MagicMock(status_code=200, raise_for_status=MagicMock())), \
         patch("agents.agent_04_human_gate.save_order_state"), \
         patch("agents.agent_04_human_gate.log_decision") as mock_log:
        notify_human("ORD-001")

    mock_log.assert_called_once()
    assert mock_log.call_args[1]["agent_name"] == AGENT_NAME
    assert mock_log.call_args[1]["decision"] == "notified"


# ── UT-03-04  check_approval returns DB status (stub poller) ─────────────────

def test_check_approval_returns_awaiting_when_no_change():
    row = {**_FLAGGED_ROW, "status": STATUS_AWAITING}
    with patch("agents.agent_04_human_gate.get_order_by_id", return_value=row):
        status = check_approval("ORD-001")
    assert status == STATUS_AWAITING


def test_check_approval_returns_approved_when_set():
    row = {**_FLAGGED_ROW, "status": STATUS_APPROVED}
    with patch("agents.agent_04_human_gate.get_order_by_id", return_value=row):
        status = check_approval("ORD-001")
    assert status == STATUS_APPROVED


def test_check_approval_raises_if_order_not_found():
    with patch("agents.agent_04_human_gate.get_order_by_id", return_value=None):
        with pytest.raises(AgentError):
            check_approval("ORD-999")


# ── UT-03-05  Teams webhook missing → AgentError ─────────────────────────────

def test_no_webhook_url_raises_agent_error():
    with patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", None):
        with pytest.raises(AgentError, match="TEAMS_WEBHOOK_URL"):
            notify_human("ORD-001")


def test_empty_webhook_url_raises_agent_error():
    with patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", ""):
        with pytest.raises(AgentError, match="TEAMS_WEBHOOK_URL"):
            notify_human("ORD-001")


# ── UT-03-06  Teams HTTP failure raises AgentError ───────────────────────────

def test_teams_http_error_raises_agent_error():
    import httpx as _httpx
    with patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", _TEAMS_URL), \
         patch("agents.agent_04_human_gate.get_order_by_id", return_value=_FLAGGED_ROW), \
         patch("agents.agent_04_human_gate.httpx.post",
               side_effect=_httpx.HTTPStatusError(
                   "403", request=MagicMock(), response=MagicMock(status_code=403)
               )), \
         patch("agents.agent_04_human_gate.save_order_state"), \
         patch("agents.agent_04_human_gate.log_decision"):
        with pytest.raises(AgentError):
            notify_human("ORD-001")


def test_teams_network_error_raises_agent_error():
    import httpx as _httpx
    with patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", _TEAMS_URL), \
         patch("agents.agent_04_human_gate.get_order_by_id", return_value=_FLAGGED_ROW), \
         patch("agents.agent_04_human_gate.httpx.post",
               side_effect=_httpx.ConnectError("timeout")), \
         patch("agents.agent_04_human_gate.save_order_state"), \
         patch("agents.agent_04_human_gate.log_decision"):
        with pytest.raises(AgentError):
            notify_human("ORD-001")


# ── UT-03-07  run() picks first flagged order ─────────────────────────────────

def test_run_picks_first_flagged_order():
    with patch("agents.agent_04_human_gate.get_flagged_order",
               return_value=_FLAGGED_ROW) as mock_get, \
         patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", _TEAMS_URL), \
         patch("agents.agent_04_human_gate.get_order_by_id", return_value=_FLAGGED_ROW), \
         patch("agents.agent_04_human_gate.httpx.post",
               return_value=MagicMock(status_code=200, raise_for_status=MagicMock())), \
         patch("agents.agent_04_human_gate.save_order_state"), \
         patch("agents.agent_04_human_gate.log_decision"):
        result = run()

    mock_get.assert_called_once()
    assert result["order_id"] == "ORD-001"


def test_run_returns_none_when_no_flagged_orders():
    with patch("agents.agent_04_human_gate.get_flagged_order", return_value=None):
        result = run()
    assert result is None


# ── UT-03-08  Teams payload contains all required fields ─────────────────────

def test_teams_payload_contains_order_id():
    with patch("agents.agent_04_human_gate.TEAMS_WEBHOOK_URL", _TEAMS_URL), \
         patch("agents.agent_04_human_gate.get_order_by_id", return_value=_FLAGGED_ROW), \
         patch("agents.agent_04_human_gate.httpx.post") as mock_post, \
         patch("agents.agent_04_human_gate.save_order_state"), \
         patch("agents.agent_04_human_gate.log_decision"):
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
        notify_human("ORD-001")

    posted_json = mock_post.call_args[1]["json"]
    # The MessageCard facts must include the order_id
    facts = posted_json["sections"][0]["facts"]
    fact_values = {f["name"]: f["value"] for f in facts}
    assert fact_values["Order ID"] == "ORD-001"
    assert fact_values["Flag Reason"] == _FLAGGED_ROW["flag_reason"]
