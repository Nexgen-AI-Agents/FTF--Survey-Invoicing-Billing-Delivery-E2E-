"""
token_log_hook.py — Claude Code Stop hook

Fires automatically after every Claude Code session turn ends.

Actions (each runs at most once per calendar day):
  1. Creates today's date block in token_usage.txt if missing
  2. Creates today's date block in compact_chat.txt if missing
  3. Commits + pushes both files when either is new

Called by .claude/settings.local.json Stop hook.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE   = os.path.join(REPO_ROOT, "token_usage.txt")
COMPACT_FILE = os.path.join(REPO_ROOT, "compact_chat.txt")

# Eastern Time — fixed UTC-4 (EDT). Close enough for log timestamps.
ET = timezone(timedelta(hours=-4))


def _get_model(payload: dict) -> str:
    return (
        payload.get("model")
        or payload.get("model_id")
        or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    )


def _git(args: list[str]) -> None:
    subprocess.run(["git"] + args, cwd=REPO_ROOT, capture_output=True, check=False)


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _insert_before_cumulative(content: str, new_block: str) -> str:
    marker = "\n================================================================================\nCUMULATIVE"
    if marker in content:
        pos = content.index(marker)
        return content[:pos] + new_block + content[pos:]
    return content + new_block


def update_token_usage(date_header: str, model: str, time_str: str) -> bool:
    """Returns True if a new block was created."""
    content = _read(TOKEN_FILE)
    if date_header in content:
        return False

    new_block = (
        f"\n"
        f"================================================================================\n"
        f"{date_header}\n"
        f"MODEL: {model}\n"
        f"================================================================================\n"
        f"\n"
        f"  SESSION: Active — Claude fills in prompt entries during session\n"
        f"\n"
        f"  [{time_str} ET] | {model} | Session started\n"
        f"\n"
        f"                                                    "
        f"┌─────────────────────────────────┐\n"
        f"                                         DAILY TOTAL "
        f"│  --- tokens (session in progress) │\n"
        f"                                         MODEL       "
        f"│  {model:<31}│\n"
        f"                                                    "
        f"└─────────────────────────────────┘\n"
    )
    _write(TOKEN_FILE, _insert_before_cumulative(content, new_block))
    return True


def update_compact_log(date_header: str, model: str) -> bool:
    """Returns True if a new block was created."""
    content = _read(COMPACT_FILE)
    if date_header in content:
        return False

    new_block = (
        f"\n"
        f"================================================================================\n"
        f"{date_header}\n"
        f"================================================================================\n"
        f"\n"
        f"  No /compact events recorded yet for this date.\n"
        f"  (Claude updates this file when /compact is used — see CLAUDE.md rule)\n"
        f"\n"
    )
    _write(COMPACT_FILE, _insert_before_cumulative(content, new_block))
    return True


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    model    = _get_model(payload)
    now      = datetime.now(ET)
    date_str = now.strftime("%Y-%m-%d")
    day_name = now.strftime("%A")
    time_str = now.strftime("%H:%M")

    date_header = f"DATE: {date_str} ({day_name})"

    changed_token   = update_token_usage(date_header, model, time_str)
    changed_compact = update_compact_log(date_header, model)

    if changed_token or changed_compact:
        files_to_add = []
        if changed_token:
            files_to_add.append(TOKEN_FILE)
        if changed_compact:
            files_to_add.append(COMPACT_FILE)

        _git(["add"] + files_to_add)
        _git([
            "commit", "-m",
            f"chore: session logs — new blocks {date_str} [{model}] [skip ci]",
        ])
        _git(["push", "origin", "main"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never crash the hook
