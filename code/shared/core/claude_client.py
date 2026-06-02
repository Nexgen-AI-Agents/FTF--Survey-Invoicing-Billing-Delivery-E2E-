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


def call_with_image(
    model: str,
    system: str,
    user_text: str,
    image_b64: str,
    media_type: str = "image/png",
    max_tokens: int = 1024,
) -> str:
    """Send a text + base64 image to Claude. Returns response text.

    For property aerial analysis and any other vision tasks.
    """
    client = _get_client()
    last_exc: Optional[Exception] = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": user_text},
                        ],
                    }
                ],
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


def call(model: str, system: str, user: str, max_tokens: int = 1024,
         cache_system: bool = True) -> str:
    """Send a prompt to Claude and return the response text.

    cache_system=True (default): marks the system prompt for prompt caching
    (I-019). System prompts are static per agent run — caching saves cost at
    scale (7,000+ Quote orders). Cache TTL is 5 minutes; re-use within that
    window is free. Set False only for one-off dynamic system prompts.

    Retries up to _MAX_RETRIES times on rate limit or transient API errors.
    Raises LLMUnavailableError after all retries are exhausted.
    """
    client = _get_client()
    last_exc: Optional[Exception] = None

    # Build system param — list format required for cache_control
    if cache_system:
        system_param = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    else:
        system_param = system

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_param,
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
