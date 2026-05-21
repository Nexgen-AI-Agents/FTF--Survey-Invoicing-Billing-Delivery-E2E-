import time
from typing import Optional

import anthropic

from core.exceptions import LLMUnavailableError
from core.logger import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 5.0  # seconds; multiplied by attempt number on rate limit

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment
    return _client


def call(model: str, system: str, user: str, max_tokens: int = 1024) -> str:
    """
    Send a prompt to Claude and return the response text.
    Retries up to _MAX_RETRIES times on rate limit or transient API errors.
    Raises LLMUnavailableError after all retries are exhausted.
    """
    client = _get_client()
    last_exc: Optional[Exception] = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return message.content[0].text

        except anthropic.RateLimitError as exc:
            logger.warning("Claude rate limit hit (attempt %d/%d)", attempt, _MAX_RETRIES)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY * attempt)

        except anthropic.APIStatusError as exc:
            logger.error("Claude API error %s (attempt %d/%d)", exc.status_code, attempt, _MAX_RETRIES)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY)

    raise LLMUnavailableError(
        f"Claude unavailable after {_MAX_RETRIES} attempts"
    ) from last_exc
