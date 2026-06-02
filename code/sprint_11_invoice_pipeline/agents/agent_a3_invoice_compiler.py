"""Agent A3 — Invoice Compiler (Invoice Pipeline)

Takes the order packet from A2 (data_collected status), validates the order,
classifies the client tier, and uses Claude Sonnet to reason a complete invoice
draft from real property data. Posts the draft to Teams for human approval (A4).

Pricing principle: NO fixed table applied mechanically.
  Claude sees: service type, company's negotiated rate, aerial analysis, appraiser
  data, FEMA zone, lot size, legal description, county, notes, duplicate alerts —
  and reasons about the final price. Pricing constants are guidelines for that
  reasoning, not lookup values the code applies directly.

Pre-flight gates (deterministic, before AI runs):
  • Condo detection → reject (no land parcel to survey)
  • Duplicate detection → flag in Teams card; human decides

Client tier classification (deterministic):
  • individual  — ng_company.company_type = 1
  • new_title   — company_type = 0, registered >= NEW_TITLE_YEAR_CUTOFF, low volume
  • old_title   — all other companies

Rate source (passed to AI as context):
  • PRIMARY: ng_company.ng_rate if > $100 (per-client negotiated rate)
  • FALLBACK: $475 (individual/new_title) or $400 (old_title) when ng_rate unset

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
from config.settings import (
    APPROVED_SENDERS,
    FTF_ORDER_URL,
    PRICE_SURVEY_FALLBACK_INDIVIDUAL,
    PRICE_SURVEY_FALLBACK_OLD_TITLE,
    PRICE_EC_BASE,
    COMPLEXITY_REFERENCE,
    TOPO_REFERENCE,
    NEW_TITLE_YEAR_CUTOFF,
    NEW_TITLE_ORDER_CUTOFF,
)
from core.claude_client import call as llm_call
from core.excel_db import (
    get_orders_by_status, get_order_by_id, get_pricing_examples,
    save_order_state, log_decision,
)
from core.exceptions import AgentError
from core.ftf_client import get_historical_pricing_orders
from core.ftf_mysql import get_order_details, get_company_info, find_duplicate_orders
from core.logger import get_logger
from core.teams_graph_client import post_channel_message

AGENT_NAME = "agent_a3_invoice_compiler"
log = get_logger(AGENT_NAME)

# ── Pre-flight validation ─────────────────────────────────────────────────────

def _detect_condo(order_details: dict) -> Optional[str]:
    """Return rejection reason if order is a condo (cannot survey), else None."""
    unit = (order_details.get("ng_unit_number") or "").strip()
    if unit:
        return f"Condo/unit order — unit number '{unit}' detected in ng_unit_number"

    legal = (order_details.get("ng_legal_description") or "").upper()
    for keyword in ("CONDOMINIUM", " CONDO", "UNIT OF ", "AIRSPACE UNIT"):
        if keyword in legal:
            return f"Condo order — legal description contains '{keyword}'"

    address = (order_details.get("ng_property_address") or "").upper()
    for pattern in (" UNIT ", " APT ", " SUITE ", "#"):
        if pattern in address:
            # Only flag if followed by alphanumerics (actual unit indicator)
            idx = address.find(pattern)
            after = address[idx + len(pattern):idx + len(pattern) + 5].strip()
            if after and (after[0].isdigit() or after[0].isalpha()):
                return f"Possible condo — address contains '{pattern.strip()}' indicator"

    return None


def _detect_duplicates(order_id: str, order_details: dict) -> list[dict]:
    """Duplicate check using Latitude, Longitude, and Folio/MLS number."""
    return find_duplicate_orders(
        order_id=order_id,
        lat=order_details.get("ng_lat") or "",
        lng=order_details.get("ng_long") or "",
        folio_mls=order_details.get("ng_folio_mls_number") or "",
    )


# ── Client tier classification ────────────────────────────────────────────────

def _classify_client_tier(company_info: dict) -> str:
    """Return 'individual', 'new_title', or 'old_title'."""
    if not company_info:
        return "individual"  # no company record → treat as one-off

    if company_info.get("company_type") == 1:
        return "individual"

    dtentered = company_info.get("ng_dtentered")
    order_count = company_info.get("ng_order_count", 0)

    if dtentered:
        reg_year = dtentered.year if hasattr(dtentered, "year") else int(str(dtentered)[:4])
        if reg_year >= NEW_TITLE_YEAR_CUTOFF and order_count < NEW_TITLE_ORDER_CUTOFF:
            return "new_title"

    return "old_title"


def _get_fallback_survey_rate(tier: str) -> float:
    """Return default survey rate when ng_company.ng_rate is not set."""
    if tier in ("individual", "new_title"):
        return PRICE_SURVEY_FALLBACK_INDIVIDUAL
    return PRICE_SURVEY_FALLBACK_OLD_TITLE


# ── AI context assembly ───────────────────────────────────────────────────────

def _build_ai_context(
    order_id: str,
    packet: dict,
    data_sources: dict,
    order_details: dict,
    company_info: dict,
    tier: str,
    duplicates: list[dict],
    link: str,
    pricing_history: str,
) -> str:
    """Assemble the full context block fed to Claude Sonnet for price reasoning."""

    ng_rate = company_info.get("ng_rate", 0.0)
    company_name = company_info.get("company_name", "Unknown")

    if ng_rate and ng_rate > 100:
        rate_guidance = (
            f"Company's negotiated survey rate: ${ng_rate:,.2f} — USE THIS as the base survey rate. "
            f"It was agreed upon by management for this specific client."
        )
    else:
        fallback = _get_fallback_survey_rate(tier)
        rate_guidance = (
            f"No negotiated rate on file for this company. "
            f"Use default for {tier} clients: ${fallback:,.2f} as the base survey rate."
        )

    # EC pricing guidance
    ec_guidance = (
        f"Elevation Certificate (EC): always ${PRICE_EC_BASE:,.2f} regardless of client type. "
        f"If FEMA flood zone is VE (coastal), add ${COMPLEXITY_REFERENCE['zone_ve_ec']:,.2f} "
        f"to the EC line item only."
    )

    # Complexity reference (formatted for AI)
    complexity_lines = "\n".join(
        f"  • {k.replace('_', ' ')}: +${v:,.2f}" for k, v in COMPLEXITY_REFERENCE.items()
        if k != "zone_ve_ec"
    )
    topo_lines = "\n".join(
        f"  • {k.replace('_', ' ')}: ${v:,.2f}" for k, v in TOPO_REFERENCE.items()
    )

    # Duplicate alert block
    dup_block = ""
    if duplicates:
        dup_lines = "\n".join(
            f"  • Order {d['order_id']} — {d['address']}, {d['county']} — "
            f"service: {d['service']} — match: {', '.join(d['match_reasons'])}"
            for d in duplicates[:3]
        )
        dup_block = f"\n⚠️ POSSIBLE DUPLICATE ORDERS (flagged for human review):\n{dup_lines}\n"

    # Key order fields
    service_type = order_details.get("ng_service_requested") or packet.get("services_requested", {}).get("value", "Unknown")
    lot_size     = order_details.get("ng_size") or packet.get("lot_size", {}).get("value", "unknown")
    fema_zone    = order_details.get("ng_flood") or packet.get("fema_zone", {}).get("value", "unknown")
    county       = order_details.get("ng_property_county") or packet.get("property_county", {}).get("value", "")
    address      = order_details.get("ng_property_address") or packet.get("property_address", {}).get("value", "")
    legal_desc   = order_details.get("ng_legal_description") or packet.get("legal_description", {}).get("value", "")
    is_commercial = bool(order_details.get("ng_commercial"))
    certifications = (order_details.get("ng_certifications") or "").strip()
    notes        = packet.get("summary", "")

    # A2 analysis blocks — stored at top level of data_sources, not inside packet
    appraiser_data   = data_sources.get("appraiser_data") or {}
    aerial_analysis  = data_sources.get("aerial_analysis") or {}

    aerial_summary = ""
    if aerial_analysis:
        aerial_summary = f"""
AERIAL IMAGE ANALYSIS (Google satellite, zoom 19):
  Lot shape: {aerial_analysis.get('lot_shape', 'unknown')}
  Estimated lot size: {aerial_analysis.get('estimated_lot_size', 'unknown')}
  Main structure footprint: {aerial_analysis.get('main_structure_footprint_sqft', 'unknown')} sqft
  Visible structures: {aerial_analysis.get('visible_structures', 'unknown')}
  Pool visible: {aerial_analysis.get('pool_visible', False)}
  Driveway count: {aerial_analysis.get('driveway_count', 'unknown')}
  Apparent encroachments: {aerial_analysis.get('apparent_encroachments', 'none noted')}
  Access type: {aerial_analysis.get('access_type', 'unknown')}
  Site notes: {aerial_analysis.get('site_notes', '')}
  Confidence: {aerial_analysis.get('confidence', 'unknown')}
"""

    appraiser_summary = ""
    if appraiser_data and appraiser_data.get("confidence") not in ("LOW", None):
        appraiser_summary = f"""
PROPERTY APPRAISER DATA:
  Legal description: {appraiser_data.get('legal_description', '')}
  Lot size: {appraiser_data.get('lot_size', '')}
  Structure sqft: {appraiser_data.get('structure_sqft', '')}
  Parcel ID: {appraiser_data.get('parcel_id', '')}
  Year built: {appraiser_data.get('year_built', '')}
  Confidence: {appraiser_data.get('confidence', '')}
"""

    context = f"""You are pricing a Florida land survey invoice for NexGen Surveying.
Reason carefully through every relevant factor. Propose a final price with itemized line items.

ORDER: {order_id}
FTF LINK: {link}

── ORDER DETAILS ────────────────────────────────
Service requested: {service_type}
Property address:  {address}
County:            {county}
Lot size (DB):     {lot_size} acres
FEMA flood zone:   {fema_zone}
Legal description: {legal_desc[:300] if legal_desc else 'not available'}
Commercial flag:   {is_commercial}
Certifications:    {certifications[:200] if certifications else 'none (individual/direct order)'}
Order notes:       {notes[:300] if notes else 'none'}
{aerial_summary}{appraiser_summary}
── CLIENT ───────────────────────────────────────
Company: {company_name}
Client tier: {tier.upper()} ({tier} = {'individual homeowner' if tier == 'individual' else ('new/low-volume title company' if tier == 'new_title' else 'established title company')})
Order count: {company_info.get('ng_order_count', 0)} total orders with NexGen
{rate_guidance}

── PRICING GUIDELINES (use as context for your reasoning) ───
{ec_guidance}

Complexity upcharge reference ranges (validate against actual property data — do NOT apply mechanically):
{complexity_lines}

Topographic Survey reference pricing by lot size:
{topo_lines}
Topo lots > 1.00 acre: ESCALATE — do not price, flag for management.

Lot > 5.00 acres: ESCALATE — do not price for any service type.
{dup_block}
── PRICING HISTORY (recent FTF + internal examples) ─────────
{pricing_history}

── YOUR TASK ────────────────────────────────────
1. Identify the service route: is this a standard boundary/survey, EC-only, combined, TOPO, or should it ESCALATE?
2. Start from the company's rate (or fallback) — then assess what the aerial image, legal description, lot size, county, and FEMA zone tell you about actual field complexity.
3. Apply complexity upcharges only where the data supports them — explain each one.
4. If Zone VE, add ${COMPLEXITY_REFERENCE['zone_ve_ec']:,.2f} to any EC line item.
5. If Monroe County, add ~${COMPLEXITY_REFERENCE['monroe_county']:,.2f} for remote mobilisation.
6. If anything is unclear or the job clearly needs management quoting, set escalate_flag=true and explain why.
7. Flag duplicates if found — do not reject, just note in flags.

Return ONLY valid JSON (no markdown, no explanation outside JSON):
{{
  "total_amount": 0.00,
  "services": [
    {{"name": "...", "description": "...", "amount": 0.00}}
  ],
  "pricing_reasoning": "2-3 sentence explanation of how you determined the price",
  "confidence": "HIGH|MEDIUM|LOW",
  "escalate_flag": false,
  "escalate_reason": null,
  "flags": []
}}"""

    return context


# ── AI pricing pass ───────────────────────────────────────────────────────────

def _ai_compile_price(context: str) -> dict:
    """Claude Sonnet reasons from real order data and returns a pricing decision."""
    try:
        raw = llm_call(
            model=HUMAN_GATE_MODEL,
            system=(
                "You are a pricing expert for a Florida land surveying company. "
                "You reason from real property data — aerial analysis, legal descriptions, "
                "lot size, county, FEMA zone — to propose accurate invoice prices. "
                "Your output is always valid JSON."
            ),
            user=context,
            max_tokens=800,
        ).strip()

        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()

        result = json.loads(raw)

        # Sanity check: recompute total from services
        if result.get("services"):
            computed = sum(item.get("amount", 0) for item in result["services"])
            if abs(computed - result.get("total_amount", 0)) > 0.01:
                result["total_amount"] = round(computed, 2)

        return result

    except Exception as exc:
        log.warning("_ai_compile_price failed: %s", exc)
        return {
            "total_amount": 0.0,
            "services": [],
            "pricing_reasoning": f"AI pricing failed: {exc}. Manual review required.",
            "confidence": "LOW",
            "escalate_flag": True,
            "escalate_reason": "AI pricing error — needs manual quote",
            "flags": ["ai_error"],
        }


# ── Teams card ────────────────────────────────────────────────────────────────

def _build_teams_post(
    order_id: str,
    packet: dict,
    ai_result: dict,
    link: str,
    company_info: dict,
    tier: str,
    duplicates: list[dict],
    condo_reason: Optional[str] = None,
) -> str:
    """Build the Teams approval card HTML."""
    client  = packet.get("client_name", {}).get("value") or company_info.get("company_name") or "Unknown"
    address = packet.get("property_address", {}).get("value") or "Unknown"
    county  = packet.get("property_county", {}).get("value") or "Unknown"
    summary = packet.get("summary", "")
    total   = ai_result.get("total_amount", 0)

    # Header and status tag
    if condo_reason:
        status_tag = "<p><strong>🚫 REJECTED — CONDO ORDER (no land parcel to survey)</strong></p>"
    elif ai_result.get("escalate_flag"):
        reason = ai_result.get("escalate_reason") or "AI flagged for manual review"
        status_tag = f"<p><strong>📤 ESCALATED — {reason}</strong></p>"
    else:
        confidence = ai_result.get("confidence", "MEDIUM")
        conf_icon = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❌"}.get(confidence, "⚠️")
        status_tag = f"<p>{conf_icon} AI confidence: <strong>{confidence}</strong></p>"

    # Client tier display
    tier_labels = {
        "individual": "Individual / One-off",
        "new_title":  f"New Title Company ({NEW_TITLE_YEAR_CUTOFF}+, low volume)",
        "old_title":  "Established Title Company",
    }
    ng_rate = company_info.get("ng_rate", 0)
    if ng_rate and ng_rate > 100:
        rate_source = f"Negotiated rate: <strong>${ng_rate:,.2f}</strong> (from account profile)"
    else:
        fallback = _get_fallback_survey_rate(tier)
        rate_source = f"Default rate: <strong>${fallback:,.2f}</strong> (no rate on file — tier default)"

    # Line items
    items_html = ""
    for item in ai_result.get("services", []):
        items_html += f"<li><strong>{item['name']}</strong> — ${item['amount']:,.2f}<br><small>{item['description']}</small></li>"
    if not items_html:
        items_html = "<li>No line items — see escalation/rejection reason above</li>"

    # Duplicate alert
    dup_html = ""
    if duplicates:
        dup_html = "<h4>⚠️ Possible Duplicate Orders</h4><ul>"
        for d in duplicates[:3]:
            dup_html += (
                f"<li>Order <strong>{d['order_id']}</strong> — {d['address']}, {d['county']} "
                f"— {', '.join(d['match_reasons'])}</li>"
            )
        dup_html += "</ul>"

    # Flags
    flags = ai_result.get("flags", [])
    flags_html = ""
    if flags:
        flags_html = "<h4>Flags</h4><ul>" + "".join(f"<li>🔸 {f}</li>" for f in flags) + "</ul>"

    html = f"""
<h3>📋 Invoice Draft — Order {order_id}</h3>
<p><a href="{link}">[View in FTF →]</a></p>

<ul>
<li><strong>Client:</strong> {client}</li>
<li><strong>Tier:</strong> {tier_labels.get(tier, tier)}</li>
<li><strong>Rate source:</strong> {rate_source}</li>
<li><strong>Property:</strong> {address}, {county} County</li>
<li><strong>Summary:</strong> {summary}</li>
</ul>

{status_tag}

<h4>Services</h4>
<ul>{items_html}</ul>
<p><strong>Total: ${total:,.2f}</strong></p>

<h4>Pricing Reasoning</h4>
<p><em>{ai_result.get('pricing_reasoning', '')}</em></p>
{dup_html}{flags_html}
<hr>
<p><strong>Reply to approve, reject, or change:</strong><br>
• <code>APPROVE</code> — send invoice as-is<br>
• <code>REJECT [reason]</code> — hold, don't send<br>
• <code>change price to $XXX</code> — update and repost<br>
• <code>add [service]</code> / <code>remove [service]</code><br>
• Any other instruction — I'll interpret and update<br>
<em>Only {", ".join(s.capitalize() for s in APPROVED_SENDERS)} can approve.</em></p>
""".strip()

    return html


# ── Main entry point ──────────────────────────────────────────────────────────

def compile_for_order(order_id: str) -> dict:
    """Validate, price, and post invoice draft for one order. Returns result dict."""
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"compile_for_order: order {order_id} not in state DB")

    raw_sources = db_row.get("data_sources")
    if not raw_sources:
        raise AgentError(f"compile_for_order: order {order_id} has no data_sources — run A2 first")

    data_sources = json.loads(raw_sources) if isinstance(raw_sources, str) else raw_sources
    packet = data_sources.get("packet", {})
    link   = f"{FTF_ORDER_URL}/{order_id}"

    # ── 1. Fetch live order + company data from MySQL ─────────────────────────
    order_details = get_order_details(order_id)
    company_id    = int(order_details.get("ng_company_id") or 0)
    company_info  = get_company_info(company_id) if company_id else {}
    tier          = _classify_client_tier(company_info)

    # ── 2. Pre-flight validation ──────────────────────────────────────────────
    service_type = order_details.get("ng_service_requested") or ""
    condo_reason = _detect_condo(order_details)
    duplicates   = _detect_duplicates(order_id, order_details)

    # Hard stop — condo orders cannot be surveyed
    if condo_reason:
        stop_result = {
            "total_amount": 0.0,
            "services": [],
            "pricing_reasoning": condo_reason,
            "confidence": "N/A",
            "escalate_flag": True,
            "escalate_reason": condo_reason,
            "flags": ["condo_rejected"],
        }
        teams_html = _build_teams_post(
            order_id, packet, stop_result, link, company_info, tier,
            duplicates, condo_reason,
        )
        post_result = post_channel_message(teams_html, subject=f"Invoice — Order {order_id}")
        save_order_state(
            order_id,
            status="invoice_draft_posted",
            invoice_draft=json.dumps(stop_result, default=str),
            approval_message_id=post_result.get("id", ""),
            modification_count=0,
            estimate_amount=0.0,
            draft_posted_at=datetime.now(timezone.utc).isoformat(),
        )
        log.info("order=%s hard-stop: %s", order_id, condo_reason)
        return stop_result

    # ── 3. Pricing history context ────────────────────────────────────────────
    county_val   = order_details.get("ng_property_county") or ""
    pricing_ctx  = ""
    svc_list = [service_type] if service_type else (
        packet.get("services_requested", {}).get("value", [])
    )
    if isinstance(svc_list, str):
        svc_list = [svc_list]
    for svc in svc_list[:2]:
        hist = get_historical_pricing_orders(service_type=svc, county=county_val, months=24, max_results=20)
        if hist:
            amounts = sorted(o["amount"] for o in hist)
            median  = amounts[len(amounts) // 2]
            pricing_ctx += (
                f"{svc} — FTF history (24mo, n={len(amounts)}, county={county_val or 'any'}): "
                f"min=${min(amounts):,.0f} median=${median:,.0f} max=${max(amounts):,.0f}\n"
            )
        examples = get_pricing_examples(service_type=svc, county=county_val, limit=3)
        if examples:
            pricing_ctx += f"{svc} — internal examples: {[e['final_price'] for e in examples]}\n"

    # ── 4. AI pricing pass ────────────────────────────────────────────────────
    context   = _build_ai_context(
        order_id, packet, data_sources, order_details, company_info, tier,
        duplicates, link, pricing_ctx,
    )
    ai_result = _ai_compile_price(context)

    # ── 5. Post to Teams ──────────────────────────────────────────────────────
    teams_html  = _build_teams_post(
        order_id, packet, ai_result, link, company_info, tier,
        duplicates,
    )
    post_result = post_channel_message(teams_html, subject=f"Invoice Draft — Order {order_id}")
    message_id  = post_result.get("id", "")

    # ── 6. Save state ─────────────────────────────────────────────────────────
    save_order_state(
        order_id,
        status="invoice_draft_posted",
        invoice_draft=json.dumps(ai_result, default=str),
        approval_message_id=message_id,
        modification_count=0,
        estimate_amount=ai_result.get("total_amount"),
        draft_posted_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        AGENT_NAME,
        decision="invoice_draft_posted",
        order_id=order_id,
        reason=(
            f"tier={tier} rate_source={'negotiated' if company_info.get('ng_rate', 0) > 100 else 'default'} "
            f"total=${ai_result.get('total_amount', 0):.2f} "
            f"confidence={ai_result.get('confidence')} "
            f"escalate={ai_result.get('escalate_flag')} "
            f"duplicates={len(duplicates)}"
        ),
        input_summary=f"service={service_type} county={county_val} tier={tier}",
        output_summary=f"Teams message_id={message_id}",
        model_used=HUMAN_GATE_MODEL,
    )
    log.info(
        "invoice draft posted order=%s total=%.2f tier=%s confidence=%s message_id=%s",
        order_id, ai_result.get("total_amount", 0), tier,
        ai_result.get("confidence"), message_id,
    )
    return ai_result


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
        result = compile_for_order(args.order_id)
        print(json.dumps(result, indent=2))
    elif args.run_now:
        summary = run()
        print(summary)


if __name__ == "__main__":
    main()
