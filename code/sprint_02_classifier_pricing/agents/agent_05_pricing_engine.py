import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone

from config.models import PRICING_MODEL
from config.settings import COMPLEXITY_FACTORS, ELEVATION_CERT_PRICE, PRICING_COMPLEXITY_ENABLED
from core.db import get_classified_order, log_decision, save_order_state
from core.exceptions import AgentError, PricingError
from core.ftf_client import get_pricing, get_pricing_overrides
from core.logger import get_logger

AGENT_NAME = "agent_05_pricing_engine"
log = get_logger(AGENT_NAME)

# Production county averages — NexGen Land Survey Only (23,353 invoices, May 2025–May 2026)
# Source: nexgen_ftf_db prod DB (florida_pricing_intelligence.md)
_COUNTY_AVG: dict[str, float] = {
    "OKEECHOBEE":   1797, "HIGHLANDS":    1337, "MARION":       1052, "CITRUS":        954,
    "CLAY":          779, "VOLUSIA":        734, "LAKE":          740, "POLK":          743,
    "ST LUCIE":      702, "ST. LUCIE":      702, "DUVAL":         654, "OSCEOLA":       685,
    "COLLIER":       643, "MARTIN":         631, "ORANGE":        607, "PASCO":         608,
    "INDIAN RIVER":  595, "CHARLOTTE":      591, "MANATEE":       584,
    "PALM BEACH":    571, "HILLSBOROUGH":   575, "BREVARD":       560,
    "SARASOTA":      555, "MIAMI-DADE":     547, "HERNANDO":      540,
    "PINELLAS":      527, "LEE":            500, "BROWARD":       512, "SEMINOLE":      479,
    "MONROE":       1735,  # Florida Keys — always flag for human review
}

# Pure boundary/metes survey services eligible for county-avg pricing
# "Land Survey and Elevation" excluded — its production avg ($400) is bundled/partial
_BOUNDARY_SERVICES = frozenset({
    "land survey only", "boundary survey", "re-survey",
    "update survey", "re-survey / update survey",
})

_COMMERCIAL_MULTIPLIER = 4.1   # production: commercial avg $2,159 / residential avg ~$540
_FL_STATEWIDE_AVG      = 616.0  # fallback for unknown Florida county (Land Survey Only prod avg)


def price_order(classification: dict) -> dict:
    """Look up pricing for a classified order; persist result to DB.

    classification keys used:
        order_id, service_type, pricing_tier, property_county,
        elevation_cert_required, special_pricing.

    Returns pricing dict: base_amount, elevation_cert_amount, total_amount,
        pricing_tier, override_applied, pricing_source, county_applied, complexity_note.

    Raises AgentError if order must be flagged for human review.
    Raises PricingError if FTF pricing API fails (non-flag scenarios).
    """
    order_id:               str  = classification["order_id"]
    service_type:           str  = classification["service_type"]
    pricing_tier:           str  = classification.get("pricing_tier", "individual")
    elevation_cert_required: bool = classification.get("elevation_cert_required", False)
    special_pricing:        bool  = classification.get("special_pricing", False)
    raw_county:             str  = (classification.get("property_county") or "").strip().upper()
    property_county: str | None  = raw_county or None

    override_applied = False
    pricing_source   = "ftf_api"
    county_applied   = ""
    complexity_note  = ""

    # Monroe County — always flag; pricing is non-standard (avg $1,735, Keys premium)
    if property_county == "MONROE":
        _flag_order(
            order_id, service_type, property_county,
            "Monroe County (Florida Keys) — non-standard pricing; human must confirm rate",
        )

    # Special / override pricing — customer-negotiated rates take precedence over county data
    if special_pricing:
        try:
            overrides = get_pricing_overrides()
        except PricingError as exc:
            _flag_order(
                order_id, service_type, property_county,
                f"special_pricing=True but overrides API unavailable ({exc}) — human must confirm rate",
                cause=exc,
            )

        if service_type in overrides:
            raw = overrides[service_type]
            if isinstance(raw, dict):
                base_amount = float(raw.get(pricing_tier, raw.get("individual", 0)))
            else:
                base_amount = float(raw)
            override_applied = True
            pricing_source   = "override"
        else:
            result      = get_pricing(service_type, tier=pricing_tier)
            base_amount = float(result.get("price", result.get("amount", 0)))

    else:
        # County-based pricing for boundary/land survey services
        if service_type.lower().strip() in _BOUNDARY_SERVICES and property_county:
            county_avg = _COUNTY_AVG.get(property_county)
            if county_avg:
                base_amount    = county_avg
                county_applied = property_county
                pricing_source = "county_avg"
                complexity_note = (
                    f"County avg: {property_county} ${county_avg:,.0f} "
                    f"(NexGen prod baseline). Property features (pool, structures, "
                    f"terrain, distance) may warrant adjustment — Robert reviews before sending."
                )
            else:
                # County not in production table — FL statewide avg as fallback
                base_amount    = _FL_STATEWIDE_AVG
                pricing_source = "fl_statewide_avg"
                complexity_note = (
                    f"County '{property_county}' not in pricing table — "
                    f"FL statewide avg ${_FL_STATEWIDE_AVG:,.0f} used. Verify with Robert."
                )
        else:
            result      = get_pricing(service_type, tier=pricing_tier)
            base_amount = float(result.get("price", result.get("amount", 0)))

    # Complexity upcharges (I-065) — gated by PRICING_COMPLEXITY_ENABLED
    # Robert must confirm factor weights before enabling. Features from order properties.
    complexity_upcharge = 0.0
    complexity_parts: list[str] = []
    if PRICING_COMPLEXITY_ENABLED:
        features = classification.get("property_features") or {}
        if features.get("has_pool"):
            complexity_upcharge += COMPLEXITY_FACTORS["pool"]
            complexity_parts.append(f"pool +${COMPLEXITY_FACTORS['pool']}")
        shed_count = int(features.get("shed_count") or 0)
        if shed_count > 0:
            upcharge = shed_count * COMPLEXITY_FACTORS["shed"]
            complexity_upcharge += upcharge
            complexity_parts.append(f"{shed_count} shed(s) +${upcharge}")
        extra_driveways = max(0, int(features.get("driveway_count") or 1) - 1)
        if extra_driveways > 0:
            upcharge = extra_driveways * COMPLEXITY_FACTORS["driveway_extra"]
            complexity_upcharge += upcharge
            complexity_parts.append(f"{extra_driveways} extra driveway(s) +${upcharge}")
        wall_count = int(features.get("wall_count") or 4)
        if wall_count > 4:
            extra_10s = (wall_count - 4) // 10
            if extra_10s > 0:
                upcharge = extra_10s * COMPLEXITY_FACTORS["walls_per_10"]
                complexity_upcharge += upcharge
                complexity_parts.append(f"{wall_count} walls +${upcharge}")
        if features.get("large_patio"):
            complexity_upcharge += COMPLEXITY_FACTORS["patio_large"]
            complexity_parts.append(f"large patio +${COMPLEXITY_FACTORS['patio_large']}")
        if features.get("remote_rural"):
            complexity_upcharge += COMPLEXITY_FACTORS["remote_rural"]
            complexity_parts.append(f"remote/rural +${COMPLEXITY_FACTORS['remote_rural']}")
        if complexity_upcharge > 0:
            base_amount += complexity_upcharge
            if complexity_note:
                complexity_note += f" Complexity upcharges: {', '.join(complexity_parts)}."
            else:
                complexity_note = f"Complexity upcharges: {', '.join(complexity_parts)}."

    # B2B / commercial multiplier (production data: commercial avg $2,159 vs residential avg $540)
    if pricing_tier == "b2b" and not override_applied:
        base_amount    = round(base_amount * _COMMERCIAL_MULTIPLIER, 2)
        pricing_source = f"{pricing_source}+b2b_{_COMMERCIAL_MULTIPLIER}x"
        if complexity_note:
            complexity_note += f" B2B {_COMMERCIAL_MULTIPLIER}x multiplier applied."
        else:
            complexity_note = f"B2B/commercial {_COMMERCIAL_MULTIPLIER}x multiplier applied to base rate."

    elevation_cert_amount = ELEVATION_CERT_PRICE if elevation_cert_required else 0
    total_amount          = base_amount + elevation_cert_amount

    save_order_state(
        order_id,
        estimate_amount=total_amount,
        priced_at=datetime.now(timezone.utc).isoformat(),
        status="priced",
    )

    log_decision(
        agent_name=AGENT_NAME,
        decision="priced",
        order_id=order_id,
        reason=f"base={base_amount} elev={elevation_cert_amount} total={total_amount}",
        input_summary=(
            f"service={service_type} tier={pricing_tier} "
            f"county={property_county} special={special_pricing}"
        ),
        output_summary=(
            f"total={total_amount} source={pricing_source} county={county_applied} "
            f"note={complexity_note[:120] if complexity_note else ''}"
        ),
        model_used=PRICING_MODEL,
    )

    log.info(
        "priced order=%s total=%.2f tier=%s source=%s county=%s",
        order_id, total_amount, pricing_tier, pricing_source, county_applied or "n/a",
    )

    return {
        "order_id":             order_id,
        "base_amount":          base_amount,
        "elevation_cert_amount": elevation_cert_amount,
        "total_amount":         total_amount,
        "pricing_tier":         pricing_tier,
        "override_applied":     override_applied,
        "pricing_source":       pricing_source,
        "county_applied":       county_applied,
        "complexity_note":      complexity_note,
    }


def _flag_order(
    order_id: str,
    service_type: str,
    property_county: str | None,
    reason: str,
    cause: Exception | None = None,
) -> None:
    """Persist flagged status and raise AgentError (never returns)."""
    log.warning("price_order flagging order=%s reason=%s", order_id, reason)
    save_order_state(
        order_id,
        status="flagged",
        flag_reason=reason,
        flagged_at=datetime.now(timezone.utc).isoformat(),
    )
    log_decision(
        agent_name=AGENT_NAME,
        decision="flagged",
        order_id=order_id,
        reason=reason,
        input_summary=f"service={service_type} county={property_county}",
        output_summary="flagged — human review required",
        model_used=PRICING_MODEL,
    )
    if cause:
        raise AgentError(reason) from cause
    raise AgentError(reason)


def run() -> dict | None:
    """Price the next classified order from DB. Returns pricing dict or None."""
    order_rec = get_classified_order()
    if not order_rec:
        log.info("no classified orders awaiting pricing")
        return None

    classification = {
        "order_id":               order_rec["order_id"],
        "service_type":           order_rec.get("service_type") or "",
        "pricing_tier":           order_rec.get("pricing_tier") or "individual",
        "elevation_cert_required": bool(order_rec.get("elevation_cert_required", False)),
        "special_pricing":        bool(order_rec.get("special_pricing", False)),
        "property_county":        order_rec.get("property_county") or "",
    }
    return price_order(classification)


if __name__ == "__main__":
    # Standalone run: orchestrator calls price_order(classification) directly.
    # This entry point exists for manual testing only.
    log.info("pricing engine ready — call price_order(classification) via orchestrator")
