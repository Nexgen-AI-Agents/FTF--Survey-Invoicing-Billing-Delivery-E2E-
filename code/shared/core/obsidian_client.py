"""
obsidian_client.py — Obsidian Local REST API integration

Why Obsidian alongside memory.md?
  - memory.md is a flat file — no search, no linking, no visual graph
  - Obsidian's graph view makes decision relationships visible:
      ADR-001 -> Sprint 3 -> I-025 -> Ryan decision
  - Every agent decision auto-writes a linked note in the vault
  - Humans can open the vault and see the full project knowledge graph
  - Local first — no cloud, no sensitive order data leaving the network

Setup (one-time, 5 minutes):
  1. Open Obsidian → Settings → Community plugins → Browse
  2. Search "Local REST API" → Install → Enable
  3. Go to Local REST API plugin settings → copy the API key
  4. Add to .env: Obsidian=<your-api-key>
  5. Default port: 27123 (configurable via OBSIDIAN_BASE_URL in .env)

Vault structure created by this client:
  vault/
    agents/          -> one note per agent (decisions, errors, stats)
    decisions/       -> ADRs and architectural choices
    issues/          -> mirrors issues/issue.md as linked notes
    memory/          -> persistent agent memory across sessions
    sprints/         -> sprint summaries + status
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import PurePosixPath
from typing import Any

import httpx

from config import settings


class ObsidianError(Exception):
    """Raised when the Obsidian REST API returns an error."""


def _headers() -> dict[str, str]:
    if not settings.OBSIDIAN_API_KEY:
        raise ObsidianError(
            "Obsidian API key not set. Add 'Obsidian=<key>' to .env.\n"
            "See code/shared/core/obsidian_client.py docstring for setup."
        )
    return {
        "Authorization": f"Bearer {settings.OBSIDIAN_API_KEY}",
        "Content-Type": "text/markdown",
    }


def _base() -> str:
    return settings.OBSIDIAN_BASE_URL.rstrip("/")


# ═══════════════════════════════════════════════════════════════════════════════
#  Core CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def read_note(vault_path: str) -> str:
    """
    Read a note from the vault.
    vault_path: relative path within vault, e.g. "memory/agents.md"
    """
    url = f"{_base()}/vault/{vault_path}"
    resp = httpx.get(url, headers=_headers(), verify=False, timeout=10)
    if resp.status_code == 404:
        return ""
    if resp.status_code != 200:
        raise ObsidianError(f"read_note({vault_path}) failed: {resp.status_code} {resp.text}")
    return resp.text


def write_note(vault_path: str, content: str, append: bool = False) -> None:
    """
    Write or append to a note.
    vault_path: e.g. "agents/agent_03_classifier.md"
    """
    url = f"{_base()}/vault/{vault_path}"
    method = "POST" if append else "PUT"
    resp = httpx.request(
        method,
        url,
        headers=_headers(),
        content=content.encode("utf-8"),
        verify=False,
        timeout=10,
    )
    if resp.status_code not in (200, 204):
        raise ObsidianError(f"write_note({vault_path}) failed: {resp.status_code} {resp.text}")


def delete_note(vault_path: str) -> None:
    url = f"{_base()}/vault/{vault_path}"
    resp = httpx.delete(url, headers=_headers(), verify=False, timeout=10)
    if resp.status_code not in (200, 204, 404):
        raise ObsidianError(f"delete_note({vault_path}) failed: {resp.status_code}")


def search(query: str, context_length: int = 200) -> list[dict[str, Any]]:
    """
    Full-text search across the vault.
    Returns list of {filename, score, matches} dicts.
    """
    url = f"{_base()}/search/simple/"
    resp = httpx.post(
        url,
        headers={**_headers(), "Content-Type": "application/json"},
        json={"query": query, "contextLength": context_length},
        verify=False,
        timeout=15,
    )
    if resp.status_code != 200:
        raise ObsidianError(f"search({query!r}) failed: {resp.status_code} {resp.text}")
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
#  Agent decision logging — writes to vault automatically
# ═══════════════════════════════════════════════════════════════════════════════

def log_agent_decision(
    agent_name: str,
    order_id: str,
    decision: str,
    reason: str,
    status: str,
) -> None:
    """
    Append a timestamped decision entry to the agent's vault note.
    Called by agents in addition to DB log_decision() for human-readable history.

    Example vault path: agents/agent_03_classifier.md
    """
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = (
        f"\n## {ts} | {order_id}\n"
        f"- **Decision**: {decision}\n"
        f"- **Reason**: {reason}\n"
        f"- **Status set**: `{status}`\n"
    )
    vault_path = f"agents/{agent_name.lower().replace(' ', '_')}.md"
    try:
        write_note(vault_path, entry, append=True)
    except ObsidianError:
        pass  # Obsidian offline is non-fatal — DB log is the source of truth


# ═══════════════════════════════════════════════════════════════════════════════
#  Vault initializer — creates folder structure on first run
# ═══════════════════════════════════════════════════════════════════════════════

_VAULT_INDEX = """\
# FTF Agentic AI OS — Knowledge Vault

## Structure
- [[agents/]] — per-agent decision history
- [[decisions/]] — Architecture Decision Records (ADRs)
- [[issues/]] — open and closed issues
- [[memory/]] — persistent agent memory across sessions
- [[sprints/]] — sprint summaries and status

## Quick Links
- [[memory/project_memory]] — main project memory (mirrors memory.md)
- [[memory/open_dependencies]] — current open blockers
- [[sprints/sprint_roadmap]] — 14-sprint delivery plan status
"""

def init_vault() -> None:
    """
    Create the vault folder structure + index note.
    Safe to call multiple times — skips existing notes.
    """
    folders = [
        "agents/README.md",
        "decisions/README.md",
        "issues/README.md",
        "memory/README.md",
        "sprints/README.md",
    ]
    try:
        if not read_note("README.md"):
            write_note("README.md", _VAULT_INDEX)
        for f in folders:
            if not read_note(f):
                write_note(f, f"# {f.split('/')[0].title()}\n\nAuto-created by FTF Agentic AI OS.\n")
    except ObsidianError:
        pass  # vault offline — skip silently


# ═══════════════════════════════════════════════════════════════════════════════
#  Health check
# ═══════════════════════════════════════════════════════════════════════════════

def health_check() -> bool:
    """Returns True if Obsidian Local REST API is reachable."""
    try:
        resp = httpx.get(
            f"{_base()}/",
            headers={"Authorization": f"Bearer {settings.OBSIDIAN_API_KEY or ''}"},
            verify=False,
            timeout=3,
        )
        return resp.status_code in (200, 401)  # 401 = online but wrong key
    except Exception:
        return False
