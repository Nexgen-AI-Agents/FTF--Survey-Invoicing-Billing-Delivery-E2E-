import pytest
import anthropic
from unittest.mock import patch, MagicMock
from core.claude_client import call
from core.exceptions import LLMUnavailableError
from config.models import CLAUDE_HAIKU


def _mock_message(text="OK"):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


@patch("core.claude_client._get_client")
def test_call_returns_text_on_success(mock_get_client):
    client = MagicMock()
    client.messages.create.return_value = _mock_message("OK")
    mock_get_client.return_value = client

    result = call(CLAUDE_HAIKU, "system prompt", "user message", max_tokens=10)
    assert result == "OK"


@patch("core.claude_client._get_client")
def test_call_retries_on_rate_limit_then_succeeds(mock_get_client):
    client = MagicMock()
    client.messages.create.side_effect = [
        anthropic.RateLimitError("rate limit", response=MagicMock(), body={}),
        _mock_message("OK"),
    ]
    mock_get_client.return_value = client

    with patch("core.claude_client.time.sleep"):
        result = call(CLAUDE_HAIKU, "sys", "usr", max_tokens=10)
    assert result == "OK"
    assert client.messages.create.call_count == 2


@patch("core.claude_client._get_client")
def test_call_raises_llm_unavailable_after_max_retries(mock_get_client):
    client = MagicMock()
    client.messages.create.side_effect = anthropic.RateLimitError(
        "rate limit", response=MagicMock(), body={}
    )
    mock_get_client.return_value = client

    with patch("core.claude_client.time.sleep"):
        with pytest.raises(LLMUnavailableError):
            call(CLAUDE_HAIKU, "sys", "usr", max_tokens=10)

    assert client.messages.create.call_count == 3  # _MAX_RETRIES
