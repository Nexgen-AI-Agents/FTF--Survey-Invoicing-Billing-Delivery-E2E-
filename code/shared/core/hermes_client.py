"""
hermes_client.py — NousResearch Hermes 3 (local via Ollama) integration

Why Hermes instead of Claude for classification?
  - Cost: $0 per call — runs 100% locally on your machine via Ollama
  - Privacy: client order data never leaves your network
  - Speed: sub-100ms local inference vs 300-600ms Claude API round-trip
  - Specialization: Hermes 3 (LLaMA 3.1 based) is fine-tuned specifically for
    structured JSON output and function calling — outperforms Claude Haiku on
    classification tasks while costing nothing

Current use: Agent 3 _llm_normalize_service_type() fallback
Future use:  Any classification/extraction task that doesn't need Claude's
             writing quality — flag trigger evaluation, county lookup, etc.

Setup: ollama must be running (Ollama app or `ollama serve`)
Model: hermes3 (pulled via `ollama pull hermes3`)
"""

import json
from typing import Any

import ollama as _ollama

from config import settings


# ═══════════════════════════════════════════════════════════════════════════════
#  Core call
# ═══════════════════════════════════════════════════════════════════════════════

def _chat(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """
    Single chat call to Hermes via Ollama.
    Temperature 0.0 by default — deterministic structured output.
    """
    response = _ollama.chat(
        model=model or settings.HERMES_MODEL,
        options={"temperature": temperature},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    return response.message.content or ""


def _chat_json(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Chat with forced JSON output format.
    Returns parsed dict. Raises ValueError on bad JSON.
    """
    response = _ollama.chat(
        model=model or settings.HERMES_MODEL,
        format="json",
        options={"temperature": 0.0},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    raw = response.message.content or "{}"
    return json.loads(raw)


# ═══════════════════════════════════════════════════════════════════════════════
#  Service type normalization — replaces Claude call in Agent 3
# ═══════════════════════════════════════════════════════════════════════════════

_NORMALIZE_SYSTEM = """You are a Florida land surveying service classifier.
Given a raw service type string from a CRM, return the canonical FTF service name.

Canonical names (use EXACTLY as written):
Boundary Survey, ALTA/NSPS Land Title Survey, ALTA Table A Survey,
Topography Survey, Elevation Certificate, Floodplain Study,
Construction Layout, Building Stake Out, Acreage Survey,
Legal Description, Lot Split, Subdivision Platting,
Specific Purpose Survey, Wetland Delineation, Right-of-Way Survey,
Easement Survey, Tree Survey, As-Built Survey, Record Survey,
Mortgage Survey, Permit Survey.

Return JSON: {"canonical": "<name>", "confidence": 0.0-1.0, "unrecognized": false}
If you cannot map it with confidence >= 0.7, set unrecognized to true and canonical to null."""


def normalize_service_type(raw_service: str) -> dict[str, Any]:
    """
    Normalize a raw service type string to a canonical FTF name using Hermes.

    Returns:
        {"canonical": str | None, "confidence": float, "unrecognized": bool}

    Raises RuntimeError if Ollama is not reachable.
    """
    try:
        result = _chat_json(
            system_prompt=_NORMALIZE_SYSTEM,
            user_prompt=f"Raw service type: {raw_service!r}",
        )
        return {
            "canonical":    result.get("canonical"),
            "confidence":   float(result.get("confidence", 0.0)),
            "unrecognized": bool(result.get("unrecognized", False)),
        }
    except Exception as exc:
        raise RuntimeError(f"Hermes normalize_service_type failed: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════════════════
#  Flag trigger evaluation (future use — Sprint 9+)
# ═══════════════════════════════════════════════════════════════════════════════

_FLAG_SYSTEM = """You are a risk classifier for a Florida land surveying company.
Given order details, identify which risk flags apply.

Return JSON: {"flags": ["reason1", "reason2"], "should_flag": true|false}
Only flag when genuinely uncertain or risky — routine orders should not be flagged."""


def evaluate_flags(order_summary: str) -> dict[str, Any]:
    """
    Ask Hermes to evaluate whether an order should be flagged for human review.
    Used as secondary classifier to catch edge cases the deterministic rules miss.
    """
    try:
        return _chat_json(
            system_prompt=_FLAG_SYSTEM,
            user_prompt=f"Order details: {order_summary}",
        )
    except Exception as exc:
        raise RuntimeError(f"Hermes evaluate_flags failed: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════════════════
#  Health check
# ═══════════════════════════════════════════════════════════════════════════════

def health_check() -> bool:
    """Returns True if Ollama is running and hermes3 model is available."""
    try:
        models = _ollama.list()
        names = [m.model for m in models.models]
        return any(settings.HERMES_MODEL in n for n in names)
    except Exception:
        return False
