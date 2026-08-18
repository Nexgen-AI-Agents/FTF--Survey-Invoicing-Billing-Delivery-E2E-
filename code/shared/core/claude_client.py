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
        # FTF Invoicing Agent uses its OWN dedicated Anthropic key.
        # Falls back to the generic ANTHROPIC_API_KEY if the dedicated one is unset,
        # and to library default (env) if neither — so a missing var never hard-fails
        # here; a bad/absent key surfaces on the API call and triggers the OpenAI fallback.
        api_key = (
            os.getenv("FTF_INVOICING_AGENT_ANTHROPIC_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )
        _client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    return _client


def _openai_call(system: str, user: str, max_tokens: int) -> str:
    """Fallback to OpenAI gpt-4o when Anthropic is unavailable (with its own retry)."""
    import openai as _openai
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMUnavailableError("OpenAI fallback unavailable — OPENAI_API_KEY not set")
    oc = _openai.OpenAI(api_key=api_key)
    last_exc: Optional[Exception] = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = oc.chat.completions.create(
                model=_OPENAI_FALLBACK_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            last_exc = exc
            logger.warning("OpenAI fallback error (attempt %d/%d): %r", attempt, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BASE_DELAY * attempt)
    raise LLMUnavailableError(f"OpenAI fallback exhausted: {last_exc!r}")


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

        except Exception as exc:
            # ANY other Claude failure (auth error, bad request, decode error, etc.) —
            # do not let it escape uncaught; route straight to the OpenAI fallback so the
            # agent never hard-fails on an unexpected Claude error class.
            logger.error("Claude unexpected error (attempt %d/%d): %r", attempt, _MAX_RETRIES, exc)
            last_exc = exc
            break

    logger.warning("Claude exhausted — falling back to OpenAI %s", _OPENAI_FALLBACK_MODEL)
    try:
        return _openai_call_with_image(system, user_text, image_b64, media_type, max_tokens)
    except Exception as exc:
        raise LLMUnavailableError(
            f"Both Claude and OpenAI unavailable: claude={last_exc!r} openai={exc!r}"
        ) from exc


def _extract_text(message) -> str:
    """Join all text blocks, skipping thinking/other blocks.

    With extended thinking on, message.content[0] can be a thinking block (which has no
    .text) — so never index [0]; collect the text blocks explicitly. For a normal
    response this returns exactly what content[0].text used to."""
    return "".join(
        b.text for b in message.content if getattr(b, "type", None) == "text"
    )


def call(model: str, system: str, user: str, max_tokens: int = 1024,
         cache_system: bool = True, thinking: bool = False,
         effort: Optional[str] = None) -> str:
    """Call Claude and return the text answer.

    thinking=True enables extended (adaptive) thinking on Opus 4.x — the model reasons
    before answering. Off by default so existing callers are unchanged. When thinking is
    on, max_tokens is floored so the visible answer isn't starved by the reasoning budget.
    NOTE: budget_tokens is NOT used — it is rejected (400) on Opus 4.8/4.7."""
    client = _get_client()
    last_exc: Optional[Exception] = None

    if cache_system:
        system_param = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    else:
        system_param = system

    # Models that think by default (Opus 5 / Fable / Mythos / Sonnet 5) run adaptive thinking
    # even when `thinking` is omitted — so floor max_tokens for them too, or a small budget
    # would be spent on reasoning and starve the visible answer.
    _think_by_default = model.startswith(("claude-opus-5", "claude-fable", "claude-mythos",
                                          "claude-sonnet-5"))
    thinking_active = thinking or _think_by_default

    create_kwargs = dict(
        model=model,
        max_tokens=max(max_tokens, 4096) if thinking_active else max_tokens,
        system=system_param,
        messages=[{"role": "user", "content": user}],
    )
    if thinking:
        create_kwargs["thinking"] = {"type": "adaptive"}
        create_kwargs["output_config"] = {"effort": effort or "high"}

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            message = client.messages.create(**create_kwargs)
            if not message.content:
                raise LLMUnavailableError("Claude returned empty content block")
            text = _extract_text(message)
            if not text:
                raise LLMUnavailableError("Claude returned no text block")
            return text

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

        except Exception as exc:
            # ANY other Claude failure (auth error, bad request, decode error, etc.) —
            # do not let it escape uncaught; route straight to the OpenAI fallback so the
            # agent never hard-fails on an unexpected Claude error class.
            logger.error("Claude unexpected error (attempt %d/%d): %r", attempt, _MAX_RETRIES, exc)
            last_exc = exc
            break

    logger.warning("Claude exhausted — falling back to OpenAI %s", _OPENAI_FALLBACK_MODEL)
    try:
        return _openai_call(system, user, max_tokens)
    except Exception as exc:
        raise LLMUnavailableError(
            f"Both Claude and OpenAI unavailable: claude={last_exc!r} openai={exc!r}"
        ) from exc
