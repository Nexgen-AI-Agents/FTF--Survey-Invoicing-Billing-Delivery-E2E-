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
from zoneinfo import ZoneInfo

_EASTERN = ZoneInfo("America/New_York")
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.models import HUMAN_GATE_MODEL
from config.settings import (
    FTF_ORDER_URL,
    INVOICE_BATCH_SIZE,
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
from core.onedrive_excel_client import (
    append_approval_row, auto_reject_condo_row, get_pending_order_ids, match_pricing_rule,
)

AGENT_NAME = "agent_a3_invoice_compiler"
log = get_logger(AGENT_NAME)

# ── Pre-flight validation ─────────────────────────────────────────────────────

def _detect_condo(order_details: dict) -> Optional[str]:
    """Return rejection reason if order is a condo (cannot survey), else None.

    Only uses reliable DB fields — ng_unit_number (set by FTF admin for true condos)
    and legal description keywords. Address string matching was removed: 'UNIT X' in
    an address is common in mobile home parks and commercial complexes, not condos.
    """
    unit = (order_details.get("ng_unit_number") or "").strip()
    if unit:
        return f"Condo/unit order — unit number '{unit}' detected in ng_unit_number"

    legal = (order_details.get("ng_legal_description") or "").upper()
    for keyword in ("CONDOMINIUM", " CONDO", "UNIT OF ", "AIRSPACE UNIT"):
        if keyword in legal:
            return f"Condo order — legal description contains '{keyword}'"

    return None


def _detect_duplicates(order_id: str, order_details: dict) -> list[dict]:
    """Duplicate check using Latitude, Longitude, and Folio/MLS number."""
    return find_duplicate_orders(
        order_id=order_id,
        lat=order_details.get("ng_lat") or "",
        lng=order_details.get("ng_long") or "",
        folio_mls=order_details.get("ng_folio_mls_number") or "",
    )


# ── Learned rules (from A7 feedback learner) ─────────────────────────────────

_RULES_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "learned_rules.json")


def _load_learned_rules(order_id: str = "") -> str:
    """Return learned rules + order-specific overrides for injection into the pricing prompt.

    Order overrides are listed first (highest priority) and labeled clearly so
    Claude knows they apply only to this order. Global rules follow.
    """
    try:
        with open(_RULES_FILE) as f:
            data = json.load(f)

        lines = []

        # Order-specific overrides (highest priority — one-time instructions)
        if order_id:
            for override in data.get("order_overrides", {}).get(order_id, []):
                lines.append(f"  • [ORDER OVERRIDE — THIS ORDER ONLY] {override}")

        # Global active rules
        active = [r for r in data.get("rules", []) if r.get("status") == "active"]
        for r in active[-20:]:  # cap at 20 most recent so the prompt stays bounded
            label = r["type"].replace("_", " ").upper()
            lines.append(f"  • [{label}] {r['description']}")

        return "\n".join(lines)
    except Exception:
        return ""


# ── Service breakdown string ──────────────────────────────────────────────────

def _build_breakdown_str(services: list) -> str:
    """Build the 'Service / Breakdown' string for the Excel approval column.

    Single service:  'Boundary Survey: $475.00'
    Multi-service:   'Boundary Survey: $475.00 | Elevation Cert: $150.00'
    No amount:       'Boundary Survey'  (fallback for pricing_needed/condo)
    """
    parts = []
    for svc in services:
        name = (svc.get("name") or "").strip()
        amt  = svc.get("amount", 0.0)
        if name and amt:
            parts.append(f"{name}: ${float(amt):.2f}")
        elif name:
            parts.append(name)
    return " | ".join(p for p in parts if p)


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
    company_name = company_info.get("company_name") or ""

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
    service_type = order_details.get("ng_service_requested") or packet.get("services_requested", {}).get("value") or ""
    lot_size     = order_details.get("ng_size") or packet.get("lot_size", {}).get("value") or ""
    fema_zone    = order_details.get("ng_flood") or packet.get("fema_zone", {}).get("value") or ""
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
  Lot shape: {aerial_analysis.get('lot_shape') or 'not analyzed'}
  Estimated lot size: {aerial_analysis.get('estimated_lot_size') or 'not analyzed'}
  Main structure footprint: {aerial_analysis.get('main_structure_footprint_sqft') or 'not analyzed'} sqft
  Visible structures: {aerial_analysis.get('visible_structures') or 'not analyzed'}
  Pool visible: {aerial_analysis.get('pool_visible', False)}
  Driveway count: {aerial_analysis.get('driveway_count') or 'not analyzed'}
  Apparent encroachments: {aerial_analysis.get('apparent_encroachments') or 'none noted'}
  Access type: {aerial_analysis.get('access_type') or 'not analyzed'}
  Site notes: {aerial_analysis.get('site_notes', '')}
  Confidence: {aerial_analysis.get('confidence') or 'not analyzed'}
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

    # Inject learned rules + any one-time order overrides
    learned_block = _load_learned_rules(order_id=order_id)
    if learned_block:
        context = context.replace(
            "── YOUR TASK ────────────────────────────────────",
            (
                "── FIELD USER RULES (from human feedback — apply as instructed) ────\n"
                f"{learned_block}\n\n"
                "── YOUR TASK ────────────────────────────────────"
            ),
            1,
        )

    return context


# ── AI pricing pass ───────────────────────────────────────────────────────────

_MAX_PRICE_RETRIES = 2


def _ai_compile_price(context: str) -> dict:
    """Claude Sonnet reasons from real order data and returns a pricing decision."""
    last_exc: Exception | None = None

    for attempt in range(_MAX_PRICE_RETRIES + 1):
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
                max_tokens=2000,
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
            last_exc = exc
            if attempt < _MAX_PRICE_RETRIES:
                log.warning("_ai_compile_price attempt %d/%d failed: %s — retrying",
                            attempt + 1, _MAX_PRICE_RETRIES + 1, exc)
            else:
                log.error("_ai_compile_price failed after %d attempts: %s",
                          _MAX_PRICE_RETRIES + 1, exc)

    return {
        "total_amount": 0.0,
        "services": [],
        "pricing_reasoning": f"AI pricing failed: {last_exc}. Manual review required.",
        "confidence": "LOW",
        "escalate_flag": True,
        "escalate_reason": "AI pricing error — needs manual quote",
        "flags": ["ai_error"],
    }


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
    link   = f"{FTF_ORDER_URL}/?order={order_id}"

    # ── 1. Fetch live order + company data from MySQL ─────────────────────────
    order_details = get_order_details(order_id)

    # Guard: order may have been canceled in FTF after A1 queued it — never post to Excel.
    if int(order_details.get("ng_status") or 1) == 0:
        log.info("order=%s Canceled in FTF — marking permanently_excluded, skipping Excel post", order_id)
        save_order_state(order_id, status="permanently_excluded")
        return {}

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
        save_order_state(
            order_id,
            status="condo_rejected",
            invoice_draft=json.dumps(stop_result, default=str),
            modification_count=0,
            estimate_amount=0.0,
            draft_posted_at=datetime.now(timezone.utc).isoformat(),
        )
        # Write to Excel so the team sees it and can action it — without this, condos
        # are invisible and the client is left waiting with no response.
        _condo_client    = packet.get("client_name", {}).get("value") or db_row.get("client_name", "")
        _condo_addr      = (
            packet.get("property_address", {}).get("value")
            or order_details.get("ng_property_address", "")
        )
        _condo_ftf_status = str(order_details.get("ng_status_desc") or "")
        _condo_notes = (
            f"CONDO ORDER — Cannot survey. {condo_reason}. "
            "AUTO-REJECTED. ACTION REQUIRED: Contact client to explain that a boundary "
            "survey is not possible on a condo/airspace unit. Arrange refund or redirect "
            "to an appropriate service (e.g. interior unit measurement)."
        )
        try:
            append_approval_row(
                order_id     = order_id,
                client_name  = _condo_client,
                address      = _condo_addr,
                service      = "CONDO — Cannot Survey",
                amount       = 0.0,
                confidence   = "N/A",
                escalate     = True,
                ftf_link     = link,
                order_status = _condo_ftf_status,   # real FTF status, not "Condo Rejected"
                notes        = _condo_notes,
            )
            log.info("order=%s condo written to Excel, auto-rejecting", order_id)
            auto_reject_condo_row(order_id)         # immediately set Action=Reject + Processed At
        except Exception as exc:
            log.warning("condo Excel write failed order=%s: %s (non-fatal)", order_id, exc)
        log.info("order=%s hard-stop condo_rejected: %s", order_id, condo_reason)
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

    # ── 4. Check Pricing Rules tab first (user-defined overrides beat AI) ────
    company_name_for_rule = company_info.get("company_name") or packet.get("client_name", {}).get("value", "")
    pricing_rule = match_pricing_rule(
        service=service_type or ", ".join(str(s) for s in (packet.get("services_requested", {}).get("value") or [])),
        county=county_val,
        client=company_name_for_rule,
    )
    if pricing_rule and pricing_rule["price"] > 0:
        log.info(
            "order=%s matched pricing rule id=%s price=%.2f (service=%r county=%r client=%r)",
            order_id, pricing_rule["rule_id"], pricing_rule["price"],
            pricing_rule["service"], pricing_rule["county"], pricing_rule["client"],
        )
        ai_result = {
            "total_amount":      pricing_rule["price"],
            "services":          [{"name": service_type or "Survey", "amount": pricing_rule["price"]}],
            "pricing_reasoning": f"Pricing rule #{pricing_rule['rule_id']} applied: {pricing_rule['notes'] or 'manual override'}",
            "confidence":        "HIGH",
            "escalate_flag":     False,
            "escalate_reason":   "",
            "flags":             ["pricing_rule"],
        }
    else:
        # ── 4b. AI pricing pass ───────────────────────────────────────────────
        context   = _build_ai_context(
            order_id, packet, data_sources, order_details, company_info, tier,
            duplicates, link, pricing_ctx,
        )
        ai_result = _ai_compile_price(context)

    # ── 4c. Pricing failed — write to Excel for manual pricing ──────────────
    total = ai_result.get("total_amount", 0)
    no_services = not ai_result.get("services")
    if total == 0 or no_services:
        save_order_state(
            order_id,
            status="pricing_needed",
            invoice_draft=json.dumps(ai_result, default=str),
            modification_count=0,
            estimate_amount=0.0,
            draft_posted_at=datetime.now(timezone.utc).isoformat(),
        )
        # Write to Excel so human can see and manually set the price.
        # Without this, pricing_needed orders are invisible to the team.
        _pn_client  = packet.get("client_name", {}).get("value") or db_row.get("client_name", "")
        _pn_addr    = (
            packet.get("property_address", {}).get("value")
            or order_details.get("ng_property_address", "")
        )
        _pn_svc     = service_type or ", ".join(
            str(s) for s in packet.get("services_requested", {}).get("value", []) if s
        )
        _pn_reason  = ai_result.get("escalate_reason") or ai_result.get("pricing_reasoning") or "AI could not determine price"
        _pn_ftf_status = str(order_details.get("ng_status_desc") or "")
        _pn_is_delivered = _pn_ftf_status.strip().lower() == "delivered"
        if _pn_is_delivered:
            _pn_notes = (
                f"⚠️ Invoice can't be created for the delivered order — "
                f"MANUAL PRICING REQUIRED — {_pn_reason}. "
                "Enter the correct amount in the Amount column, then set Action = Approve."
            )
        else:
            _pn_notes = (
                f"MANUAL PRICING REQUIRED — {_pn_reason}. "
                "Enter the correct amount in the Amount column, then set Action = Approve."
            )
        try:
            append_approval_row(
                order_id      = order_id,
                client_name   = _pn_client,
                address       = _pn_addr,
                service       = _pn_svc or "Unknown — see notes",
                amount        = 0.0,
                confidence    = "LOW",
                escalate      = True,
                ftf_link      = link,
                order_status  = _pn_ftf_status,
                notes         = _pn_notes,
                highlight_red = _pn_is_delivered,
            )
            log.info("order=%s pricing_needed written to Excel for manual pricing", order_id)
        except Exception as exc:
            log.warning("pricing_needed Excel write failed order=%s: %s (non-fatal)", order_id, exc)
        log.info("order=%s pricing_needed: held for manual pricing via spreadsheet", order_id)
        return ai_result

    # ── 5. Write row to OneDrive approval spreadsheet ─────────────────────────
    client_name   = packet.get("client_name", {}).get("value") or company_info.get("company_name") or ""
    address       = packet.get("property_address", {}).get("value") or order_details.get("ng_property_address") or ""
    svc_breakdown = _build_breakdown_str(ai_result.get("services", []))
    posted_at     = datetime.now(_EASTERN).strftime("%Y-%m-%d %H:%M %Z")

    escalate_flag   = bool(ai_result.get("escalate_flag"))
    if escalate_flag:
        _esc_reason = ai_result.get("escalate_reason") or "unusual order characteristics detected"
        escalation_note = (
            f"ESCALATE — {_esc_reason}. "
            "Needs Robert or Ryan review before approving."
        )
    else:
        escalation_note = ""
    ftf_order_status = str(order_details.get("ng_status_desc") or "")

    excel_write_ok = False
    try:
        append_approval_row(
            order_id     = order_id,
            client_name  = client_name,
            address      = address,
            service      = svc_breakdown or service_type or "",
            amount       = ai_result.get("total_amount", 0),
            confidence   = ai_result.get("confidence", "MEDIUM"),
            escalate     = escalate_flag,
            ftf_link     = link,
            order_status = ftf_order_status,
            posted_at    = posted_at,
            notes        = escalation_note,
        )
        excel_write_ok = True
    except Exception as exc:
        log.error("failed to write Excel row order=%s: %s — order stays data_collected for retry", order_id, exc)

    if not excel_write_ok:
        return ai_result  # do NOT mark invoice_draft_posted — let next run retry

    # ── 6. Save state (only reached if Excel write succeeded) ─────────────────
    save_order_state(
        order_id,
        status="invoice_draft_posted",
        invoice_draft=json.dumps(ai_result, default=str),
        approval_message_id=order_id,   # no Teams message ID; use order_id as ref
        modification_count=0,
        estimate_amount=ai_result.get("total_amount"),
        draft_posted_at=posted_at,
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
        output_summary=f"Excel row appended order={order_id}",
        model_used=HUMAN_GATE_MODEL,
    )
    log.info(
        "invoice draft posted order=%s total=%.2f tier=%s confidence=%s",
        order_id, ai_result.get("total_amount", 0), tier,
        ai_result.get("confidence"),
    )
    return ai_result


def run() -> dict:
    """Process up to INVOICE_BATCH_SIZE orders with status=data_collected.

    Dedup source: OneDrive Excel (Excel = truth).
    An order is skipped only if its ID is already in the approval sheet,
    regardless of what the pipeline state says.
    """
    orders  = get_orders_by_status("data_collected")[:INVOICE_BATCH_SIZE]
    summary = {"processed": 0, "posted": 0, "skipped_excel": 0, "errors": 0}

    pending_ids = get_pending_order_ids()   # IDs currently in the OneDrive approval sheet

    for db_row in orders:
        order_id = db_row["order_id"]
        # Excel is the authoritative dedup source — if already in sheet, sync state and skip
        if str(order_id) in pending_ids:
            log.info("skipping order=%s — already in OneDrive Excel", order_id)
            save_order_state(order_id, status="invoice_draft_posted")
            summary["skipped_excel"] += 1
            summary["processed"] += 1
            continue
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
