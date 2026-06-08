"""
token_log_hook.py — Claude Code Stop hook

Fires automatically after every Claude Code session turn ends.
Creates today's date block in token_usage.txt if it doesn't already exist.
Commits + pushes only when a NEW block is created (once per day max).

Called by .claude/settings.local.json Stop hook.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(REPO_ROOT, "token_usage.txt")

# Eastern Time — fixed UTC-4 (EDT summer). Close enough for log timestamps.
ET = timezone(timedelta(hours=-4))


def _get_model(payload: dict) -> str:
    return (
        payload.get("model")
        or payload.get("model_id")
        or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    )


def _git(args: list[str]) -> None:
    subprocess.run(["git"] + args, cwd=REPO_ROOT, capture_output=True, check=False)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    model = _get_model(payload)
    now = datetime.now(ET)
    date_str = now.strftime("%Y-%m-%d")
    day_name = now.strftime("%A")
    time_str = now.strftime("%H:%M")

    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    date_header = f"DATE: {date_str} ({day_name})"

    # Only act if today's block is missing
    if date_header in content:
        return

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

    cumulative_marker = "\n================================================================================\nCUMULATIVE"
    if cumulative_marker in content:
        pos = content.index(cumulative_marker)
        content = content[:pos] + new_block + content[pos:]
    else:
        content += new_block

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    # Commit + push the new date block (runs at most once per day)
    _git(["add", TOKEN_FILE])
    _git([
        "commit", "-m",
        f"chore: token log — new session {date_str} [{model}] [skip ci]",
    ])
    _git(["push", "origin", "main"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never crash the hook
