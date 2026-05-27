"""
agent_18_business_analyst.py — AI Business Analyst Agent

Ryan's request (2026-05-28): "Did you not use an agent with context for this and
just had it report? The agent viewing every order as revenue not paid orders."

This agent:
  1. Connects to the FTF pipeline DB and pulls live metrics
  2. Calls Claude (Anthropic API) with full business/finance/surveying context
  3. Returns genuine AI analysis — not hardcoded strings
  4. Distinguishes INVOICED vs COLLECTED vs POTENTIAL revenue

Usage:
  python -m agents.agent_18_business_analyst
  python -m agents.agent_18_business_analyst --output-json
  python -m agents.agent_18_business_analyst --ask "Why is AR growing faster than revenue?"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.models import CLASSIFIER_MODEL
from core.claude_client import call as llm_call
from core.db import log_decision
from core.logger import get_logger

AGENT_NAME = "agent_18_business_analyst"
log = get_logger(AGENT_NAME)

_SHARED_ROOT = Path(__file__).parent.parent.parent / "shared"
_EXPERT_PROMPT_PATH = _SHARED_ROOT / "config" / "prompts" / "land_surveyor_expert.txt"

# ── Analyst system prompt ──────────────────────────────────────────────────────

_ANALYST_SYSTEM = """
You are NexGen Land Surveying's AI business analyst. You are also a Florida PSM expert
and a business/sales/finance specialist. You have been loaded with the company's full
expert knowledge base.

CRITICAL FINANCIAL DEFINITIONS (never confuse these):
- INVOICED = what NexGen billed customers (from payment records in the DB)
- COLLECTED = actual cash received = INVOICED minus AR outstanding
- POTENTIAL = all open orders × price (includes quotes, pending — not yet billed)
- AR OUTSTANDING = INVOICED minus COLLECTED — money owed but not yet paid

When you see revenue data, always clarify which of these four it represents.
Never say "revenue" without specifying whether it means invoiced or collected.

You ask smart questions when the data is ambiguous. You flag anomalies.
You make recommendations. You are not just a data reporter — you are an analyst.

Respond in structured sections:
1. WHAT I SEE — factual summary of the data provided
2. WHAT IT MEANS — business interpretation (distinguish invoiced vs collected)
3. ANOMALIES & QUESTIONS — what looks wrong or needs clarification
4. RECOMMENDATIONS — specific actions for Ryan, Jessica, Robert, or Bobby
"""


def _load_expert_context() -> str:
    """Load the FL PSM + business expert knowledge base."""
    try:
        return _EXPERT_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        log.warning("Expert prompt not found at %s — using minimal context", _EXPERT_PROMPT_PATH)
        return "You are NexGen Land Surveying's AI business analyst. Distinguish invoiced from collected revenue."


def _pull_pipeline_metrics() -> dict:
    """Pull live metrics from the pipeline DB."""
    from core.db import _get_connection  # noqa: PLC0415

    metrics: dict = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "status_counts": {},
        "flagged_count": 0,
        "avg_estimate_amount": 0.0,
        "total_estimated": 0.0,
        "sent_count": 0,
        "pending_count": 0,
        "total_orders": 0,
        "error": None,
    }

    try:
        conn = _get_connection()
        with conn:
            with conn.cursor() as cur:
                # Status breakdown
                cur.execute(
                    "SELECT status, COUNT(*) FROM processed_orders GROUP BY status ORDER BY COUNT(*) DESC"
                )
                metrics["status_counts"] = {row[0]: row[1] for row in cur.fetchall()}
                metrics["total_orders"] = sum(metrics["status_counts"].values())

                # Flagged orders
                cur.execute("SELECT COUNT(*) FROM processed_orders WHERE flag_reason IS NOT NULL")
                metrics["flagged_count"] = cur.fetchone()[0]

                # Estimate amounts (priced/written/reviewed/sent)
                cur.execute(
                    "SELECT COUNT(*), AVG(estimate_amount), SUM(estimate_amount) "
                    "FROM processed_orders WHERE estimate_amount > 0"
                )
                row = cur.fetchone()
                if row and row[0]:
                    metrics["priced_count"] = row[0]
                    metrics["avg_estimate_amount"] = float(row[1] or 0)
                    metrics["total_estimated"] = float(row[2] or 0)

                # Sent count
                cur.execute("SELECT COUNT(*) FROM processed_orders WHERE sent_at IS NOT NULL")
                metrics["sent_count"] = cur.fetchone()[0]

                # Pending (in-flight)
                cur.execute(
                    "SELECT COUNT(*) FROM processed_orders WHERE status IN ('pending','classified','priced','written','reviewed')"
                )
                metrics["pending_count"] = cur.fetchone()[0]

                # Top service types
                cur.execute(
                    "SELECT service_type, COUNT(*) as cnt, AVG(estimate_amount) as avg_amt "
                    "FROM processed_orders WHERE service_type IS NOT NULL "
                    "GROUP BY service_type ORDER BY cnt DESC LIMIT 10"
                )
                metrics["top_services"] = [
                    {"service": r[0], "count": r[1], "avg_amount": float(r[2] or 0)}
                    for r in cur.fetchall()
                ]

                # AR proxy: sent but not marked paid (pipeline proxy — not actual AR)
                cur.execute(
                    "SELECT COUNT(*), SUM(estimate_amount) FROM processed_orders "
                    "WHERE sent_at IS NOT NULL AND estimate_amount > 0"
                )
                row = cur.fetchone()
                metrics["sent_value"] = float(row[1] or 0) if row and row[0] else 0.0

                # Recent decision log activity
                cur.execute(
                    "SELECT agent_name, COUNT(*) as cnt FROM agent_decision_log "
                    "GROUP BY agent_name ORDER BY cnt DESC LIMIT 8"
                )
                metrics["agent_activity"] = [
                    {"agent": r[0], "decisions": r[1]} for r in cur.fetchall()
                ]

    except Exception as exc:
        log.warning("DB pull failed: %s — using empty metrics", exc)
        metrics["error"] = str(exc)

    return metrics


def _format_metrics_for_prompt(metrics: dict) -> str:
    """Convert DB metrics to a structured text block for the LLM."""
    lines = [
        f"PIPELINE METRICS (pulled {metrics['pulled_at']})",
        f"Total pipeline orders: {metrics['total_orders']}",
        f"Status breakdown: {json.dumps(metrics['status_counts'], indent=2)}",
        f"Flagged for human review: {metrics['flagged_count']}",
        f"Orders with estimates: {metrics.get('priced_count', 0)}",
        f"Avg estimate amount: ${metrics['avg_estimate_amount']:,.2f}",
        f"Total pipeline estimate value (INVOICED, not collected): ${metrics['total_estimated']:,.2f}",
        f"Orders sent to clients: {metrics['sent_count']}",
        f"Orders in-flight (not yet sent): {metrics['pending_count']}",
        f"Sent estimate value (potential invoiced): ${metrics.get('sent_value', 0):,.2f}",
    ]

    if metrics.get("top_services"):
        lines.append("\nTop service types in pipeline:")
        for s in metrics["top_services"]:
            lines.append(f"  {s['service']}: {s['count']} orders, avg ${s['avg_amount']:,.2f}")

    if metrics.get("agent_activity"):
        lines.append("\nAgent decision log activity:")
        for a in metrics["agent_activity"]:
            lines.append(f"  {a['agent']}: {a['decisions']} decisions logged")

    if metrics.get("error"):
        lines.append(f"\nDB ERROR: {metrics['error']} — metrics may be incomplete")

    return "\n".join(lines)


def analyze(question: str | None = None) -> dict:
    """Run the AI business analyst. Returns structured analysis dict.

    question: optional specific question to answer. If None, runs full analysis.
    """
    expert_context = _load_expert_context()
    metrics = _pull_pipeline_metrics()
    metrics_text = _format_metrics_for_prompt(metrics)

    system_prompt = f"{_ANALYST_SYSTEM}\n\n---\n\n{expert_context}"

    if question:
        user_msg = (
            f"I have a specific question about NexGen's business data:\n\n"
            f"QUESTION: {question}\n\n"
            f"CURRENT PIPELINE DATA:\n{metrics_text}\n\n"
            f"Answer as the AI business analyst. Distinguish invoiced from collected. "
            f"Ask follow-up questions if the data is insufficient to answer fully."
        )
    else:
        user_msg = (
            f"Run a full business analysis of NexGen's current pipeline state.\n\n"
            f"CURRENT PIPELINE DATA:\n{metrics_text}\n\n"
            f"Provide your analysis in the four structured sections:\n"
            f"1. WHAT I SEE\n2. WHAT IT MEANS\n3. ANOMALIES & QUESTIONS\n4. RECOMMENDATIONS\n\n"
            f"Remember: distinguish INVOICED from COLLECTED throughout. "
            f"Flag anything that looks wrong. Ask the team questions where data is missing."
        )

    log.info("running business analysis question=%s", question or "full-analysis")

    analysis_text = llm_call(
        model=CLASSIFIER_MODEL,
        system=system_prompt,
        user=user_msg,
        max_tokens=2000,
        cache_system=True,
    )

    result = {
        "analysis": analysis_text,
        "metrics": metrics,
        "question": question,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    log_decision(
        agent_name=AGENT_NAME,
        decision="analysis_complete",
        order_id="SYSTEM",
        reason=f"question={question or 'full-analysis'}",
        input_summary=f"pipeline_orders={metrics['total_orders']} flagged={metrics['flagged_count']}",
        output_summary=f"analysis_len={len(analysis_text)} chars",
        model_used=CLASSIFIER_MODEL,
    )

    return result


def run(question: str | None = None, output_json: bool = False) -> None:
    """CLI entry point."""
    result = analyze(question)

    if output_json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print()
        print("=" * 72)
        print("  NexGen AI Business Analyst")
        print(f"  Generated: {result['generated_at']}")
        if result["question"]:
            print(f"  Question: {result['question']}")
        print("=" * 72)
        print()
        print(result["analysis"])
        print()
        print(f"  [Pipeline orders: {result['metrics']['total_orders']} | "
              f"Flagged: {result['metrics']['flagged_count']} | "
              f"Sent: {result['metrics']['sent_count']}]")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NexGen AI Business Analyst Agent")
    parser.add_argument(
        "--ask", metavar="QUESTION",
        help="Ask a specific business question (default: full analysis)"
    )
    parser.add_argument(
        "--output-json", action="store_true",
        help="Output raw JSON instead of formatted text"
    )
    args = parser.parse_args()
    run(question=args.ask, output_json=args.output_json)
