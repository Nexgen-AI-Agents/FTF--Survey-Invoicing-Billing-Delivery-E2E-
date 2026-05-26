"""
memory_manager.py — Nightly Decision Log Writer

Runs nightly (via GitHub Actions). Reads today's agent_decision_log,
produces a structured markdown daily log, and writes it to:
  docs/memory/YYYY-MM-DD.md
  docs/memory/latest.md  (always points to today's log)

No external dependencies beyond the DB and filesystem.
"""

import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))

from core.db import get_decisions_for_date, log_decision
from core.logger import get_logger

AGENT_NAME = "memory_manager"
log = get_logger(AGENT_NAME)

# Output directory — workspace only, never .claude/ system folders
_WORKSPACE_ROOT = Path(__file__).resolve().parents[5]
MEMORY_DIR = _WORKSPACE_ROOT / "docs" / "memory"


def _count_by_agent(rows: list[dict]) -> dict[str, dict]:
    """
    Group decision rows by agent_name.
    Returns {agent_name: {total, errors, decisions: [str]}}
    """
    by_agent: dict[str, dict] = defaultdict(lambda: {"total": 0, "errors": 0, "decisions": []})
    for row in rows:
        name = row["agent_name"]
        by_agent[name]["total"] += 1
        by_agent[name]["decisions"].append(row["decision"])
        if row["decision"] in ("error", "failed", "retry"):
            by_agent[name]["errors"] += 1
    return dict(by_agent)


def _build_markdown(target_date: date, rows: list[dict], by_agent: dict) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Daily Agent Log — {target_date}",
        f"",
        f"**Generated:** {ts}  ",
        f"**Total decisions logged:** {len(rows)}  ",
        f"**Agents active:** {len(by_agent)}",
        f"",
        f"---",
        f"",
        f"## By Agent",
        f"",
    ]

    for agent, stats in sorted(by_agent.items()):
        error_pct = (stats["errors"] / stats["total"] * 100) if stats["total"] else 0
        status_icon = "🔴" if error_pct > 10 else "🟡" if error_pct > 0 else "🟢"
        lines += [
            f"### {status_icon} {agent}",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total decisions | {stats['total']} |",
            f"| Errors | {stats['errors']} ({error_pct:.0f}%) |",
            f"",
        ]
        # Unique decision types
        unique = sorted(set(stats["decisions"]))
        if unique:
            lines.append(f"**Decision types:** {', '.join(f'`{d}`' for d in unique)}")
            lines.append(f"")

    lines += [
        f"---",
        f"",
        f"## Raw Log ({len(rows)} entries)",
        f"",
        f"| Time | Agent | Order | Decision | Reason |",
        f"|------|-------|-------|----------|--------|",
    ]
    for row in rows:
        t = row["created_at"].strftime("%H:%M:%S") if hasattr(row["created_at"], "strftime") else str(row["created_at"])[:8]
        order = row.get("order_id") or "—"
        reason = (row.get("reason") or "")[:80].replace("|", "/")
        lines.append(f"| {t} | {row['agent_name']} | {order} | `{row['decision']}` | {reason} |")

    return "\n".join(lines) + "\n"


def write_daily_log(target_date: date | None = None) -> Path:
    """
    Write today's (or target_date's) decision log to docs/memory/YYYY-MM-DD.md.
    Also updates docs/memory/latest.md.
    Returns the path written.
    """
    if target_date is None:
        target_date = date.today()

    rows = get_decisions_for_date(target_date)
    by_agent = _count_by_agent(rows)

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MEMORY_DIR / f"{target_date}.md"
    latest_path = MEMORY_DIR / "latest.md"

    content = _build_markdown(target_date, rows, by_agent)
    out_path.write_text(content, encoding="utf-8")
    latest_path.write_text(content, encoding="utf-8")

    total_errors = sum(s["errors"] for s in by_agent.values())
    log_decision(
        AGENT_NAME, "memory_written",
        reason=f"date={target_date} rows={len(rows)} agents={len(by_agent)} errors={total_errors}",
        output_summary=str(out_path),
    )
    log.info("memory log written path=%s rows=%d agents=%d", out_path, len(rows), len(by_agent))
    return out_path


def run(target_date: date | None = None) -> Path:
    """Entry point called by GitHub Actions and tests."""
    return write_daily_log(target_date)


if __name__ == "__main__":
    path = run()
    print(f"Written: {path}")
