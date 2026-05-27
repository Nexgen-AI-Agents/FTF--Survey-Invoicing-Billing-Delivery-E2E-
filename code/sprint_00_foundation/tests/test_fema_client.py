import pytest
import httpx
from unittest.mock import patch, MagicMock
from core.fema_client import check_flood_zone
from core.exceptions import FEMAUnavailableError


def _mock_fema_response(features):
    r = MagicMock(spec=httpx.Response)
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = {"features": features}
    return r


@patch("core.fema_client.httpx.get")
def test_returns_zone_code_when_feature_found(mock_get):
    mock_get.return_value = _mock_fema_response(
        [{"attributes": {"FLD_ZONE": "AE", "ZONE_SUBTY": None}}]
    )
    zone = check_flood_zone(26.7998, -80.0642)
    assert zone == "AE"


@patch("core.fema_client.httpx.get")
def test_returns_x_when_no_features(mock_get):
    mock_get.return_value = _mock_fema_response([])
    zone = check_flood_zone(26.7998, -80.0642)
    assert zone == "X"


@patch("core.fema_client.httpx.get")
def test_raises_on_timeout(mock_get):
    mock_get.side_effect = httpx.TimeoutException("timed out")
    with pytest.raises(FEMAUnavailableError, match="all 3 strategies failed"):
        check_flood_zone(26.7998, -80.0642)


@patch("core.fema_client.httpx.get")
def test_raises_on_generic_error(mock_get):
    mock_get.side_effect = Exception("network error")
    with pytest.raises(FEMAUnavailableError):
        check_flood_zone(26.7998, -80.0642)
