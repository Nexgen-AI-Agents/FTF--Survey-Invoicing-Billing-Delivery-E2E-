import os
import time
from typing import Optional

import anthropic

from core.exceptions import LLMUnavailableError
from core.logger import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 5.0

_client: Optional[anthropic.Anthropic] = None
_OPENAI_FALLBACK_MODEL = "gpt-4o"


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _openai_call(system: str, user: str, max_tokens: int) -> str:
    """Fallback to OpenAI gpt-4o when Anthropic is unavailable."""
    import openai as _openai
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMUnavailableError("OpenAI fallback unavailable — OPENAI_API_KEY not set")
    oc = _openai.OpenAI(api_key=api_key)
    resp = oc.chat.completions.create(
        model=_OPENAI_FALLBACK_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def _openai_call_with_image(system: str, user_text: str, image_b64: str,
                             media_type: str, max_tokens: int) -> str:
    """Fallback to OpenAI gpt-4o vision when Anthropic is unavailable."""
    import openai as _openai
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMUnavailableError("OpenAI fallback unavailable — OPENAI_API_KEY not set")
    oc = _openai.OpenAI(api_key=api_key)
    resp = oc.chat.completions.create(
        model=_OPENAI_FALLBACK_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                    {"type": "text", "text": user_text},
                ],
            },
        ],
    )
    return resp.choices[0].message.content or ""


def call_with_image(
    model: str,
    system: str,
    user_text: str,
    image_b64: str,
    media_type: str = "image/png",
    max_tokens: int = 1024,
) -> str:
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
            if not message.content:
                raise LLMUnavailableError("Claude returned empty content block")
            return message.content[0].text

        except anthropic.RateLimitError as exc:
            logger.warning("Claude rate limit hit (attempt %d/%d)", attempt, _MAX_RETRIES)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY * attempt)

        except anthropic.APIConnectionError as exc:
            cause = exc.__cause__ or exc
            logger.warning("Claude connection error (attempt %d/%d): %s | cause: %r",
                           attempt, _MAX_RETRIES, exc, cause)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY * attempt)

        except anthropic.APIStatusError as exc:
            logger.error("Claude API error %s (attempt %d/%d)", exc.status_code, attempt, _MAX_RETRIES)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY)

    logger.warning("Claude exhausted — falling back to OpenAI %s", _OPENAI_FALLBACK_MODEL)
    try:
        return _openai_call_with_image(system, user_text, image_b64, media_type, max_tokens)
    except Exception as exc:
        raise LLMUnavailableError(
            f"Both Claude and OpenAI unavailable: claude={last_exc!r} openai={exc!r}"
        ) from exc


def call(model: str, system: str, user: str, max_tokens: int = 1024,
         cache_system: bool = True) -> str:
    client = _get_client()
    last_exc: Optional[Exception] = None

    if cache_system:
        system_param = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
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
            if not message.content:
                raise LLMUnavailableError("Claude returned empty content block")
            return message.content[0].text

        except anthropic.RateLimitError as exc:
            logger.warning("Claude rate limit hit (attempt %d/%d)", attempt, _MAX_RETRIES)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY * attempt)

        except anthropic.APIConnectionError as exc:
            cause = exc.__cause__ or exc
            logger.warning("Claude connection error (attempt %d/%d): %s | cause: %r",
                           attempt, _MAX_RETRIES, exc, cause)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY * attempt)

        except anthropic.APIStatusError as exc:
            logger.error("Claude API error %s (attempt %d/%d)", exc.status_code, attempt, _MAX_RETRIES)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY)

    logger.warning("Claude exhausted — falling back to OpenAI %s", _OPENAI_FALLBACK_MODEL)
    try:
        return _openai_call(system, user, max_tokens)
    except Exception as exc:
        raise LLMUnavailableError(
            f"Both Claude and OpenAI unavailable: claude={last_exc!r} openai={exc!r}"
        ) from exc
