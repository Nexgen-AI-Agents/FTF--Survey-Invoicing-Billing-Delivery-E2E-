"""Agent A3 — Invoice Compiler (Invoice Pipeline)

Takes the order packet from A2 (data_collected status), builds a complete
invoice draft, and posts it to the Teams group chat for human approval.

Replaces Agent 05 (Pricing Engine) + Agent 06 (Writer) — combined into one
because pricing and drafting cannot be separated from context.

Pricing logic:
  1. Exact match from pricing_examples table (corrections entered by Robert/Ryan)
  2. Historical median from production data for same service + county
  3. Fallback to hardcoded base rates (from production_data_analysis findings)

Invoice draft fields:
  - services: list of {name, description, amount}
  - total_amount: sum
  - client_name, client_email, property_address
  - notes: any uncertainties or questions for the approver
  - gaps: fields that need human confirmation

Status flow: data_collected → invoice_draft_posted
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.models import HUMAN_GATE_MODEL
from config.settings import FTF_ORDER_URL
from core.claude_client import call as llm_call
from core.db import (
    get_orders_by_status, get_order_by_id, get_pricing_examples,
    get_invoice_learnings, save_order_state, log_decision,
)
from core.exceptions import AgentError
from core.logger import get_logger
from core.teams_graph_client import post_chat_message

AGENT_NAME = "agent_a3_invoice_compiler"
log = get_logger(AGENT_NAME)

# Base rates from production data analysis (2025-2026, nexgen_ftf_db, 18,497 orders)
# These are medians — Robert/Ryan corrections in pricing_examples take priority
_BASE_RATES: dict[str, float] = {
    "land survey only":              450.0,   # sweet spot $400-499 (52.7%)
    "land survey and elevation":     400.0,   # wide spread — many under $200 for add-on
    "elevation certificate":         225.0,   # near-uniform $200-299 (88.6%)
    "commercial":                   2100.0,   # 4.1x residential avg
    "boundary survey":               450.0,
    "topographic survey":            600.0,
    "construction staking":          750.0,
    "as-built survey":               500.0,
    "default":                       450.0,   # fallback when service not recognized
}


def _lookup_price(service: str, county: str, client_tier: str) -> tuple[float, str]:
    """Return (price, source) for a service.

    Priority:
      1. pricing_examples (human-entered corrections)
      2. invoice_learnings (learned from past corrections)
      3. Base rates table
    """
    service_lower = service.lower().strip()

    # 1. pricing_examples (most trusted)
    examples = get_pricing_examples(service_type=service, county=county, limit=5)
    if not examples:
        examples = get_pricing_examples(service_type=service, limit=5)
    if examples:
        prices = [e["final_price"] for e in examples if e.get("final_price")]
        if prices:
            median_price = sorted(prices)[len(prices) // 2]
            return median_price, "pricing_examples"

    # 2. invoice_learnings (corrections from past approvals)
    learnings = get_invoice_learnings(service_type=service, county=county, limit=5)
    if learnings:
        # learnings store the correction as text; skip for now (needs price parsing)
        pass

    # 3. Base rates
    for key, rate in _BASE_RATES.items():
        if key in service_lower or service_lower in key:
            multiplier = 1.3 if client_tier == "b2b" else 1.0
            return rate * multiplier, "base_rate"

    return _BASE_RATES["default"], "base_rate_default"


def _ai_build_invoice_draft(
    order_id: str,
    packet: dict,
    link: str,
    pricing_context: str,
) -> dict:
    """Use Claude to build a complete invoice draft from the order packet.

    Returns dict: {services, total_amount, notes, gaps, questions, summary}
    """
    prompt = f"""You are building an invoice for a land surveying order.

ORDER PACKET:
{json.dumps(packet, indent=2, default=str)[:3000]}

PRICING CONTEXT (recent examples and base rates):
{pricing_context}

FTF ORDER LINK: {link}

Build a complete invoice draft. Be specific about services. Flag anything uncertain.

Return ONLY valid JSON:
{{
  "services": [
    {{"name": "...", "description": "...", "amount": 0.00}},
    ...
  ],
  "total_amount": 0.00,
  "invoice_notes": "any special notes for this order",
  "questions_for_approver": ["Q1 if any", "Q2 if any"],
  "low_confidence_fields": ["list of fields that need human verification"],
  "pricing_rationale": "brief explanation of how prices were determined",
  "ready_to_approve": true
}}

Rules:
- Use pricing examples/base rates provided — don't invent prices
- Mark ready_to_approve=false if any service amount is unknown or confidence is LOW
- questions_for_approver: ask SPECIFIC questions only (e.g. "Is this a rush order?")
- Keep descriptions clear for client — they will see this on the invoice"""

    try:
        result_str = llm_call(
            model=HUMAN_GATE_MODEL,
            system="You are an invoice drafting assistant for a Florida land surveying company.",
            user=prompt,
            max_tokens=600,
        ).strip()

        if result_str.startswith("```"):
            result_str = re.sub(r"^```[a-z]*\n?", "", result_str).rstrip("`").strip()

        draft = json.loads(result_str)

        # Sanity check total
        if draft.get("services"):
            computed_total = sum(s.get("amount", 0) for s in draft["services"])
            if abs(computed_total - draft.get("total_amount", 0)) > 0.01:
                draft["total_amount"] = computed_total

        return draft

    except Exception as exc:
        log.warning("AI draft build failed: %s", exc)
        services_requested = packet.get("services_requested", {}).get("value", ["Land Survey"])
        if isinstance(services_requested, str):
            services_requested = [services_requested]

        services = []
        total = 0.0
        for svc in services_requested:
            price, source = _lookup_price(svc, "", "residential")
            services.append({"name": svc, "description": svc, "amount": price})
            total += price

        return {
            "services": services,
            "total_amount": total,
            "invoice_notes": "AI draft failed — please review all fields",
            "questions_for_approver": ["Please confirm services and pricing"],
            "low_confidence_fields": ["all fields — AI extraction failed"],
            "pricing_rationale": f"Fallback base rate used (AI failed: {exc})",
            "ready_to_approve": False,
        }


def _build_teams_post(
    order_id: str,
    packet: dict,
    draft: dict,
    link: str,
) -> str:
    """Build the Teams message HTML for human review."""
    client  = packet.get("client_name", {}).get("value") or "Unknown"
    address = packet.get("property_address", {}).get("value") or "Unknown"
    county  = packet.get("property_county", {}).get("value") or "Unknown"
    summary = packet.get("summary", "")
    total   = draft.get("total_amount", 0)

    services_lines = ""
    for svc in draft.get("services", []):
        services_lines += f"<li><strong>{svc['name']}</strong> — ${svc['amount']:,.2f}<br>{svc['description']}</li>"

    questions_block = ""
    for q in draft.get("questions_for_approver", []):
        questions_block += f"<li>❓ {q}</li>"

    gaps_block = ""
    for g in draft.get("low_confidence_fields", []):
        gaps_block += f"<li>⚠️ {g}</li>"

    confidence_note = ""
    if not draft.get("ready_to_approve"):
        confidence_note = "<p><strong>⚠️ Some fields have LOW confidence — please review before approving.</strong></p>"

    notes = draft.get("invoice_notes", "")
    rationale = draft.get("pricing_rationale", "")

    html = f"""
<h3>📋 Invoice Draft — Order {order_id}</h3>
<p><a href="{link}">[View in FTF →]</a></p>

<ul>
<li><strong>Client:</strong> {client}</li>
<li><strong>Property:</strong> {address}, {county} County</li>
<li><strong>Summary:</strong> {summary}</li>
</ul>

<h4>Services</h4>
<ul>{services_lines}</ul>
<p><strong>Total: ${total:,.2f}</strong></p>

<h4>Pricing Rationale</h4>
<p>{rationale}</p>
""".strip()

    if notes:
        html += f"\n<h4>Notes</h4><p>{notes}</p>"

    if questions_block:
        html += f"\n<h4>Questions for Approver</h4><ul>{questions_block}</ul>"

    if gaps_block:
        html += f"\n<h4>Needs Verification</h4><ul>{gaps_block}</ul>"

    html += confidence_note

    html += """
<hr>
<p><strong>Reply to this message to approve, reject, or request changes:</strong><br>
• <code>APPROVE</code> — send invoice as-is<br>
• <code>REJECT [reason]</code> — hold, don't send<br>
• <code>change price to $XXX</code> — I'll update and repost<br>
• <code>add [service]</code> or <code>remove [service]</code><br>
• Any other instruction — I'll interpret and update<br>
Only Robert, Ryan, or Prateek can approve.</p>"""

    return html


def compile_for_order(order_id: str) -> dict:
    """Build and post invoice draft for one order.

    Returns the draft dict.
    """
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"compile_for_order: order {order_id} not in DB")

    raw_sources = db_row.get("data_sources")
    if not raw_sources:
        raise AgentError(f"compile_for_order: order {order_id} has no data_sources — run A2 first")

    data_sources = json.loads(raw_sources) if isinstance(raw_sources, str) else raw_sources
    packet       = data_sources.get("packet", {})
    link         = f"{FTF_ORDER_URL}/{order_id}"

    # Pricing context for AI prompt
    service_list   = packet.get("services_requested", {}).get("value", [])
    county_val     = packet.get("property_county", {}).get("value", "")
    pricing_ctx    = f"Base rates: {json.dumps(_BASE_RATES)}\n"
    for svc in (service_list if isinstance(service_list, list) else [service_list]):
        examples = get_pricing_examples(service_type=str(svc), county=county_val, limit=3)
        if examples:
            pricing_ctx += f"\n{svc} recent examples: {[e['final_price'] for e in examples]}"

    # Build draft
    draft = _ai_build_invoice_draft(order_id, packet, link, pricing_ctx)

    # Post to Teams
    teams_html  = _build_teams_post(order_id, packet, draft, link)
    post_result = post_chat_message(teams_html, subject=f"Invoice Draft — Order {order_id}")
    message_id  = post_result.get("id", "")

    # Save
    save_order_state(
        order_id,
        status="invoice_draft_posted",
        invoice_draft=json.dumps(draft, default=str),
        approval_message_id=message_id,
        modification_count=0,
        estimate_amount=draft.get("total_amount"),
        draft_posted_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        AGENT_NAME,
        decision="invoice_draft_posted",
        order_id=order_id,
        reason=f"total=${draft.get('total_amount', 0):.2f} services={len(draft.get('services', []))} ready={draft.get('ready_to_approve')}",
        input_summary=f"packet confidence={packet.get('source_of_truth')}",
        output_summary=f"Teams message_id={message_id}",
        model_used=HUMAN_GATE_MODEL,
    )
    log.info("invoice draft posted order=%s total=%.2f message_id=%s", order_id, draft.get("total_amount", 0), message_id)
    return draft


def run() -> dict:
    """Process all orders with status=data_collected."""
    orders  = get_orders_by_status("data_collected")
    summary = {"processed": 0, "posted": 0, "errors": 0}

    for db_row in orders:
        order_id = db_row["order_id"]
        try:
            compile_for_order(order_id)
            summary["posted"] += 1
        except Exception as exc:
            log.error("invoice compile failed order=%s: %s", order_id, exc)
            summary["errors"] += 1
        summary["processed"] += 1

    log.info("invoice_compiler complete: %s", summary)
    return summary


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="A3 Invoice Compiler — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--order-id", help="Compile for a specific order ID")
    args = parser.parse_args(argv)

    if args.order_id:
        draft = compile_for_order(args.order_id)
        print(json.dumps(draft, indent=2))
    elif args.run_now:
        summary = run()
        print(summary)


if __name__ == "__main__":
    main()
