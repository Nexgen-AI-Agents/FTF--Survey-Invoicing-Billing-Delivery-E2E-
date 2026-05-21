from unittest.mock import patch
from core.state import mark_classified, mark_flagged, mark_priced, mark_sent


@patch("core.state.save_order_state")
def test_mark_classified(mock_save):
    mark_classified("ORD-001", "Boundary Survey", "cli@test.com")
    mock_save.assert_called_once()
    kwargs = mock_save.call_args
    assert kwargs[0][0] == "ORD-001"
    assert kwargs[1]["status"] == "classified"
    assert kwargs[1]["service_type"] == "Boundary Survey"


@patch("core.state.save_order_state")
def test_mark_flagged(mock_save):
    mark_flagged("ORD-002", "ALTA Survey — always flag")
    mock_save.assert_called_once()
    kwargs = mock_save.call_args
    assert kwargs[1]["status"] == "flagged"
    assert "ALTA" in kwargs[1]["flag_reason"]


@patch("core.state.save_order_state")
def test_mark_priced(mock_save):
    mark_priced("ORD-003", 575.0, is_flood_zone=True)
    mock_save.assert_called_once()
    kwargs = mock_save.call_args
    assert kwargs[1]["status"] == "priced"
    assert kwargs[1]["estimate_amount"] == 575.0
    assert kwargs[1]["is_flood_zone"] is True


@patch("core.state.save_order_state")
def test_mark_sent(mock_save):
    mark_sent("ORD-004")
    mock_save.assert_called_once()
    kwargs = mock_save.call_args
    assert kwargs[1]["status"] == "sent"
    assert "sent_at" in kwargs[1]
