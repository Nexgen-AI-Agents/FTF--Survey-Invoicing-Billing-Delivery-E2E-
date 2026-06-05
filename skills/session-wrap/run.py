#!/usr/bin/env python3
"""session-wrap: Force end-of-session learning capture.

Run before ending every Claude Code session. Shows recent learnings,
prints the entry template, checks for uncommitted changes, and
optionally appends a new entry to learnings.md.
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import date

BASE_DIR       = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEARNINGS_PATH = os.path.join(BASE_DIR, "learnings.md")

TODAY = date.today().strftime("%Y-%m-%d")

TEMPLATE = """## [{today}] — <SHORT TITLE>

- **What happened / bug found:**
- **Root cause:**
- **Fix:**
- **Pattern to watch / rule going forward:**"""


def _read_recent_entries(path: str, n: int = 2) -> str:
    """Return the last n dated sections from a markdown file."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    sections = re.split(r'\n(?=## \[)', content)
    entries = [s for s in sections if re.match(r'## \[\d{4}-\d{2}-\d{2}\]', s.strip())]
    return "\n\n".join(entries[-n:]) if entries else "(no entries yet)"


def _git_status() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", BASE_DIR, "status", "--short"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or "(clean — nothing uncommitted)"
    except Exception as exc:
        return f"(git status failed: {exc})"


def _append_entry(title: str, body: str) -> None:
    with open(LEARNINGS_PATH, encoding="utf-8") as f:
        content = f.read()
    entry = f"\n\n## [{TODAY}] — {title}\n\n{body}\n"
    with open(LEARNINGS_PATH, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + entry)
    print(f"  Appended to learnings.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", help="Title for new learnings.md entry")
    parser.add_argument("--body",  help="Body text (use \\n for line breaks)")
    args = parser.parse_args()

    print(f"\n{'='*66}")
    print("  SESSION WRAP — End-of-session learning capture")
    print(f"{'='*66}\n")

    print("RECENT LEARNINGS (last 2 entries):\n")
    print(_read_recent_entries(LEARNINGS_PATH))
    print()

    print("─" * 66)
    print("TEMPLATE — copy and fill in:\n")
    print(TEMPLATE.format(today=TODAY))
    print()

    print("─" * 66)
    print("GIT STATUS (uncommitted changes):\n")
    print(_git_status())
    print()

    print("─" * 66)
    print("END-OF-SESSION CHECKLIST:\n")
    for item in [
        "[ ] New bug/fix logged in learnings.md",
        "[ ] memory.md updated if any rules changed",
        "[ ] developer_review.md updated if any code patterns changed",
        "[ ] All modified files committed and pushed",
        "[ ] Skills added/modified have updated SKILL.md",
    ]:
        print(f"  {item}")
    print()

    if args.title or args.body:
        if not (args.title and args.body):
            sys.exit("Error: --title and --body must both be provided.")
        print("─" * 66)
        print("APPENDING NEW ENTRY TO learnings.md ...\n")
        _append_entry(args.title, args.body.replace("\\n", "\n"))
        print("  Done. Commit learnings.md to save.\n")
    else:
        print("Tip: add --title 'Short title' --body '- bullet 1\\n- bullet 2' to auto-append.\n")


if __name__ == "__main__":
    main()
