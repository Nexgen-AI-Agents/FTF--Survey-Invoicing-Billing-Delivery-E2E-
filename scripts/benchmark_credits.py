"""benchmark_credits.py — Claude API token usage and cost estimator

Queries agent_decision_log for the last N days, groups by agent_name,
counts model calls, and estimates monthly Claude API cost.

Usage:
    python scripts/benchmark_credits.py [--days 7] [--model sonnet]

Output: table to stdout + docs/benchmark_credits_YYYY-MM-DD.md
"""

import argparse
import os
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.db import get_decisions_since
from core.logger import get_logger

logger = get_logger("benchmark_credits")

# Pricing as of 2026-05 — update when Anthropic changes rates
_PRICES = {
    "claude-sonnet-4-6": {"input_mtok": 3.00,  "output_mtok": 15.00},
    "claude-haiku-4-5":  {"input_mtok": 0.80,  "output_mtok": 4.00},
    "claude-opus-4-7":   {"input_mtok": 15.00, "output_mtok": 75.00},
}
_DEFAULT_MODEL  = "claude-sonnet-4-6"
_AVG_INPUT_TOK  = 1_200   # estimated per agent call
_AVG_OUTPUT_TOK = 400     # estimated per agent call

# Known agent → model assignments (matches TEAM agent files)
_AGENT_MODELS: dict[str, str] = {
    "agent_02_monitor":            "claude-haiku-4-5",
    "agent_03_classifier":         "claude-sonnet-4-6",
    "agent_04_human_gate":         "claude-sonnet-4-6",
    "agent_05_pricing":            "claude-sonnet-4-6",
    "agent_06_writer":             "claude-sonnet-4-6",
    "agent_07_reviewer":           "claude-sonnet-4-6",
    "agent_08_sender":             "claude-haiku-4-5",
    "agent_09_reporter":           "claude-sonnet-4-6",
    "agent_10_ar_scanner":         "claude-sonnet-4-6",
    "agent_11_ar_escalation":      "claude-sonnet-4-6",
    "agent_15_statement_generator":"claude-sonnet-4-6",
    "agent_16_statement_reviewer": "claude-sonnet-4-6",
    "agent_17_statement_sender":   "claude-sonnet-4-6",
    "agent_01_orchestrator":       "claude-sonnet-4-6",
    "memory_manager":              "claude-sonnet-4-6",
    "dream_processor":             "claude-sonnet-4-6",
}


def _estimate_cost(calls: int, model: str) -> float:
    prices = _PRICES.get(model, _PRICES[_DEFAULT_MODEL])
    input_cost  = (calls * _AVG_INPUT_TOK  / 1_000_000) * prices["input_mtok"]
    output_cost = (calls * _AVG_OUTPUT_TOK / 1_000_000) * prices["output_mtok"]
    return round(input_cost + output_cost, 4)


def run(days: int = 7, target_model: str = _DEFAULT_MODEL) -> dict:
    decisions = get_decisions_since(days)

    agent_counts: dict[str, int] = {}
    for d in decisions:
        agent = d.get("agent_name", "unknown")
        agent_counts[agent] = agent_counts.get(agent, 0) + 1

    total_calls = sum(agent_counts.values())
    daily_avg   = round(total_calls / max(days, 1), 1)

    rows = []
    total_cost_period = 0.0
    for agent, count in sorted(agent_counts.items(), key=lambda x: -x[1]):
        model = _AGENT_MODELS.get(agent, target_model)
        cost  = _estimate_cost(count, model)
        total_cost_period += cost
        rows.append({
            "agent":  agent,
            "calls":  count,
            "model":  model,
            "cost_usd": cost,
        })

    monthly_factor      = 30 / max(days, 1)
    est_monthly_cost    = round(total_cost_period * monthly_factor, 2)
    est_daily_cost      = round(total_cost_period / max(days, 1), 4)

    return {
        "period_days":        days,
        "total_calls":        total_calls,
        "daily_avg_calls":    daily_avg,
        "period_cost_usd":    round(total_cost_period, 2),
        "est_daily_cost_usd": est_daily_cost,
        "est_monthly_cost_usd": est_monthly_cost,
        "by_agent":           rows,
    }


def _write_report(result: dict, output_dir: str = "docs") -> str:
    os.makedirs(output_dir, exist_ok=True)
    today = date.today().isoformat()
    path  = os.path.join(output_dir, f"benchmark_credits_{today}.md")

    lines = [
        f"# Claude API Cost Benchmark — {today}",
        f"",
        f"**Period:** last {result['period_days']} days  ",
        f"**Total API calls:** {result['total_calls']}  ",
        f"**Daily average:** {result['daily_avg_calls']} calls/day  ",
        f"",
        f"## Cost Estimates",
        f"",
        f"| Period | Cost (USD) |",
        f"|--------|-----------|",
        f"| {result['period_days']}-day period | ${result['period_cost_usd']:.2f} |",
        f"| Per day (avg) | ${result['est_daily_cost_usd']:.4f} |",
        f"| **Estimated monthly** | **${result['est_monthly_cost_usd']:.2f}** |",
        f"",
        f"## By Agent",
        f"",
        f"| Agent | Calls | Model | Period Cost |",
        f"|-------|-------|-------|-------------|",
    ]
    for row in result["by_agent"]:
        lines.append(
            f"| {row['agent']} | {row['calls']} | {row['model']} | ${row['cost_usd']:.4f} |"
        )

    lines += [
        f"",
        f"---",
        f"*Prices use Anthropic list rates (May 2026). Actual usage varies by prompt length.*",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


def _print_summary(result: dict) -> None:
    print(f"\n=== Claude API Cost Benchmark — last {result['period_days']} days ===")
    print(f"Total calls: {result['total_calls']}  |  Daily avg: {result['daily_avg_calls']}")
    print(f"\nEst. monthly cost: ${result['est_monthly_cost_usd']:.2f} USD")
    print(f"\n{'Agent':<40} {'Calls':>6}  {'Model':<22} {'Cost':>10}")
    print("-" * 82)
    for row in result["by_agent"]:
        print(f"{row['agent']:<40} {row['calls']:>6}  {row['model']:<22} ${row['cost_usd']:>9.4f}")
    print("-" * 82)
    print(f"{'TOTAL':<40} {result['total_calls']:>6}  {'':22} ${result['period_cost_usd']:>9.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Claude API credit usage")
    parser.add_argument("--days",  type=int, default=7,            help="lookback window in days")
    parser.add_argument("--model", type=str, default=_DEFAULT_MODEL, help="default model for unknown agents")
    args = parser.parse_args()

    result = run(days=args.days, target_model=args.model)
    _print_summary(result)
    report_path = _write_report(result)
    print(f"\nReport saved: {report_path}")
