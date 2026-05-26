"""
openai_client.py — OpenAI integration for FTF Agentic AI OS

Three capabilities:
  1. TTS (tts-1-hd, voice=nova)  — high-quality narration for demos + future client comms
  2. Chat completion (gpt-4o-mini) — fallback when Claude API is unavailable
  3. Embeddings (text-embedding-3-small) — semantic memory search in Sprint 9 loop

Why OpenAI alongside Claude?
  - TTS: OpenAI tts-1-hd produces noticeably cleaner audio than edge-tts (Microsoft)
  - Fallback: resilience — if Anthropic API has an outage, gpt-4o-mini takes over
  - Embeddings: text-embedding-3-small is the cheapest high-quality embedding in the
    market ($0.02/1M tokens). Sprint 9 memory loop indexes past orders semantically.
"""

import asyncio
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI, OpenAI

from config import settings

# ── sync client (for blocking calls) ─────────────────────────────────────────
def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI_API_KEY not set in .env")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _async_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI_API_KEY not set in .env")
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. TTS — Text-to-Speech
# ═══════════════════════════════════════════════════════════════════════════════

def tts_to_file(
    text: str,
    output_path: str | Path,
    voice: str | None = None,
    model: str | None = None,
) -> Path:
    """
    Convert text to MP3 using OpenAI tts-1-hd.
    Blocking. Returns the output path.

    Voice options: alloy | echo | fable | onyx | nova | shimmer
    Default voice 'nova' — warm, professional female.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    response = _client().audio.speech.create(
        model=model or settings.OPENAI_TTS_MODEL,
        voice=voice or settings.OPENAI_TTS_VOICE,
        input=text,
        response_format="mp3",
    )
    response.write_to_file(str(out))
    return out


async def atts_to_file(
    text: str,
    output_path: str | Path,
    voice: str | None = None,
    model: str | None = None,
) -> Path:
    """Async version of tts_to_file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    async with _async_client() as ac:
        response = await ac.audio.speech.create(
            model=model or settings.OPENAI_TTS_MODEL,
            voice=voice or settings.OPENAI_TTS_VOICE,
            input=text,
            response_format="mp3",
        )
        response.write_to_file(str(out))
    return out


# ═══════════════════════════════════════════════════════════════════════════════
#  2. Chat Completion — Fallback when Claude is unavailable
# ═══════════════════════════════════════════════════════════════════════════════

def complete(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Synchronous chat completion via gpt-4o-mini.
    Used as fallback in Agent 6 (Writer) when Claude API is unavailable.
    """
    response = _client().chat.completions.create(
        model=model or settings.OPENAI_CHAT_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""


async def acomplete(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Async version of complete()."""
    async with _async_client() as ac:
        response = await ac.chat.completions.create(
            model=model or settings.OPENAI_CHAT_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
    return response.choices[0].message.content or ""


# ═══════════════════════════════════════════════════════════════════════════════
#  3. Embeddings — Sprint 9 memory loop semantic search
# ═══════════════════════════════════════════════════════════════════════════════

def embed(text: str, model: str | None = None) -> list[float]:
    """
    Return embedding vector for text using text-embedding-3-small.
    Used in Sprint 9 to build a semantic index of past orders so the
    Orchestrator can ask "have we seen an order like this before?" cheaply.
    """
    response = _client().embeddings.create(
        input=text,
        model=model or settings.OPENAI_EMBED_MODEL,
    )
    return response.data[0].embedding


def embed_batch(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Batch embed multiple strings in a single API call (more efficient)."""
    response = _client().embeddings.create(
        input=texts,
        model=model or settings.OPENAI_EMBED_MODEL,
    )
    return [item.embedding for item in response.data]
