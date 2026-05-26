"""
obsidian_client.py — Obsidian vault integration (dual-mode)

Why Obsidian?
  - memory.md is a flat file — no search, no linking, no visual graph
  - Obsidian's graph view makes every agent decision visible and linked:
      ADR-001 -> Sprint 3 -> I-025 -> Ryan approval -> Agent 4 log
  - Local first — no sensitive order data leaving the network

Two modes (auto-detected, no config needed):
  1. REST API mode  — when Obsidian app is open with Local REST API plugin enabled
                      reads/writes via HTTP to localhost:27123
  2. Direct file mode — always works; writes markdown files directly into the vault
                        folder. Obsidian picks them up live when the app is open.

Vault location: C:/Users/Prateek Chandra/Documents/FTF-AgentVault/
Obsidian setup (open vault in app, one-time):
  1. Launch Obsidian → "Open folder as vault" → select FTF-AgentVault
  2. Settings → Community Plugins → enable Local REST API plugin
  For now: direct file mode works without Obsidian being open at all.
"""

from __future__ import annotations

import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from config import settings

# ── vault root ────────────────────────────────────────────────────────────────
VAULT_ROOT = Path(os.getenv("OBSIDIAN_VAULT_PATH",
    r"C:\Users\Prateek Chandra\Documents\FTF-AgentVault"))


class ObsidianError(Exception):
    pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Mode detection
# ═══════════════════════════════════════════════════════════════════════════════

def _api_available() -> bool:
    """Return True if the Obsidian Local REST API is reachable."""
    if not settings.OBSIDIAN_API_KEY:
        return False
    try:
        import httpx
        r = httpx.get(f"{settings.OBSIDIAN_BASE_URL}/", timeout=2,
                      headers={"Authorization": f"Bearer {settings.OBSIDIAN_API_KEY}"},
                      verify=False)
        return r.status_code in (200, 401)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  Direct file I/O (always available — no Obsidian app required)
# ═══════════════════════════════════════════════════════════════════════════════

def _file_path(vault_path: str) -> Path:
    p = VAULT_ROOT / vault_path
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _file_read(vault_path: str) -> str:
    p = _file_path(vault_path)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _file_write(vault_path: str, content: str, append: bool = False) -> None:
    p = _file_path(vault_path)
    if append and p.exists():
        existing = p.read_text(encoding="utf-8")
        p.write_text(existing + content, encoding="utf-8")
    else:
        p.write_text(content, encoding="utf-8")


def _file_delete(vault_path: str) -> None:
    p = _file_path(vault_path)
    if p.exists():
        p.unlink()


def _file_search(query: str) -> list[dict[str, Any]]:
    results = []
    q = query.lower()
    for md in VAULT_ROOT.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
            if q in text.lower():
                rel = md.relative_to(VAULT_ROOT).as_posix()
                idx = text.lower().find(q)
                snippet = text[max(0, idx-60):idx+140].strip()
                results.append({"filename": rel, "score": 1.0, "matches": [snippet]})
        except Exception:
            pass
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API I/O (when Obsidian is open with Local REST API plugin)
# ═══════════════════════════════════════════════════════════════════════════════

def _api_read(vault_path: str) -> str:
    import httpx
    url = f"{settings.OBSIDIAN_BASE_URL}/vault/{vault_path}"
    r = httpx.get(url, headers={"Authorization": f"Bearer {settings.OBSIDIAN_API_KEY}"},
                  verify=False, timeout=10)
    return "" if r.status_code == 404 else r.text


def _api_write(vault_path: str, content: str, append: bool = False) -> None:
    import httpx
    url = f"{settings.OBSIDIAN_BASE_URL}/vault/{vault_path}"
    method = "POST" if append else "PUT"
    httpx.request(method, url,
                  headers={"Authorization": f"Bearer {settings.OBSIDIAN_API_KEY}",
                            "Content-Type": "text/markdown"},
                  content=content.encode("utf-8"),
                  verify=False, timeout=10)


def _api_search(query: str) -> list[dict[str, Any]]:
    import httpx
    r = httpx.post(f"{settings.OBSIDIAN_BASE_URL}/search/simple/",
                   headers={"Authorization": f"Bearer {settings.OBSIDIAN_API_KEY}",
                             "Content-Type": "application/json"},
                   json={"query": query, "contextLength": 200},
                   verify=False, timeout=15)
    return r.json() if r.status_code == 200 else []


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API — auto-selects mode
# ═══════════════════════════════════════════════════════════════════════════════

def read_note(vault_path: str) -> str:
    if _api_available():
        return _api_read(vault_path)
    return _file_read(vault_path)


def write_note(vault_path: str, content: str, append: bool = False) -> None:
    # Always write to file (so vault stays up to date even when app is closed)
    _file_write(vault_path, content, append)
    # Also push via API if Obsidian is open (triggers live graph refresh)
    if _api_available():
        try:
            _api_write(vault_path, content, append)
        except Exception:
            pass


def delete_note(vault_path: str) -> None:
    _file_delete(vault_path)
    if _api_available():
        try:
            import httpx
            httpx.delete(f"{settings.OBSIDIAN_BASE_URL}/vault/{vault_path}",
                         headers={"Authorization": f"Bearer {settings.OBSIDIAN_API_KEY}"},
                         verify=False, timeout=10)
        except Exception:
            pass


def search(query: str) -> list[dict[str, Any]]:
    if _api_available():
        return _api_search(query)
    return _file_search(query)


# ═══════════════════════════════════════════════════════════════════════════════
#  Agent decision logging
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
    Works even when Obsidian is closed — file is written directly.
    When user opens Obsidian, they see the full history in graph view.
    """
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = (
        f"\n## {ts} | {order_id}\n"
        f"- **Decision**: {decision}\n"
        f"- **Reason**: {reason}\n"
        f"- **Status**: `{status}`\n"
    )
    vault_path = f"agents/{agent_name.lower().replace(' ', '_')}.md"
    try:
        write_note(vault_path, entry, append=True)
    except Exception:
        pass  # non-fatal — DB is source of truth


# ═══════════════════════════════════════════════════════════════════════════════
#  Vault initializer
# ═══════════════════════════════════════════════════════════════════════════════

_VAULT_INDEX = """\
# FTF Agentic AI OS — Knowledge Vault

Auto-managed by the FTF pipeline agents.

## Structure
- **[[agents/]]** — per-agent decision history (auto-written on every run)
- **[[decisions/]]** — Architecture Decision Records (ADRs 001-007+)
- **[[issues/]]** — open and closed issues (mirrors issues/issue.md)
- **[[memory/]]** — persistent agent memory across sessions
- **[[sprints/]]** — sprint summaries and delivery status

## Open in Obsidian
Vault path: `C:/Users/Prateek Chandra/Documents/FTF-AgentVault`
→ File → Open Vault → Open folder as vault → select above path
"""

def init_vault() -> None:
    """Create vault structure. Safe to call multiple times."""
    if not (VAULT_ROOT / "README.md").exists():
        write_note("README.md", _VAULT_INDEX)
    for folder in ["agents", "decisions", "issues", "memory", "sprints"]:
        readme = f"{folder}/README.md"
        if not (VAULT_ROOT / readme).exists():
            write_note(readme, f"# {folder.title()}\n\nAuto-managed by FTF agents.\n")


def health_check() -> dict[str, bool]:
    """Check both modes."""
    return {
        "vault_folder": VAULT_ROOT.exists(),
        "rest_api":     _api_available(),
    }
