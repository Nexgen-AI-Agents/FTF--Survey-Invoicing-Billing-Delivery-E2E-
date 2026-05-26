import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone

from config.models import PRICING_MODEL
from config.settings import ELEVATION_CERT_PRICE
from core.db import log_decision, save_order_state
from core.exceptions import PricingError
from core.ftf_client import get_pricing, get_pricing_overrides
from core.logger import get_logger

AGENT_NAME = "agent_05_pricing_engine"
log = get_logger(AGENT_NAME)


def price_order(classification: dict) -> dict:
    """Look up pricing for a classified order; persist result to DB.

    classification keys used:
        order_id, service_type, pricing_tier,
        elevation_cert_required, special_pricing.

    Returns pricing dict: base_amount, elevation_cert_amount, total_amount,
        pricing_tier, override_applied, pricing_source.

    Raises PricingError if the FTF pricing API fails.
    """
    order_id: str = classification["order_id"]
    service_type: str = classification["service_type"]
    pricing_tier: str = classification.get("pricing_tier", "individual")
    elevation_cert_required: bool = classification.get("elevation_cert_required", False)
    special_pricing: bool = classification.get("special_pricing", False)

    override_applied = False
    pricing_source = "ftf_api"

    if special_pricing:
        try:
            overrides = get_pricing_overrides()
        except PricingError as exc:
            # I-057: /pricing/overrides endpoint may not exist on staging/prod.
            # Cannot safely use standard rate for a customer with negotiated pricing
            # — flag for human to confirm the correct rate.
            flag_reason = f"special_pricing=True but overrides API unavailable ({exc}) — human must confirm rate"
            log.warning("price_order overrides unavailable order=%s — flagging", order_id)
            save_order_state(order_id, status="flagged", flag_reason=flag_reason,
                             flagged_at=datetime.now(timezone.utc).isoformat())
            log_decision(agent_name=AGENT_NAME, decision="flagged", order_id=order_id,
                         reason=flag_reason, input_summary=f"service={service_type}",
                         output_summary="flagged — overrides API unavailable", model_used=PRICING_MODEL)
            from core.exceptions import AgentError
            raise AgentError(flag_reason) from exc

        if service_type in overrides:
            raw = overrides[service_type]
            if isinstance(raw, dict):
                base_amount = float(raw.get(pricing_tier, raw.get("individual", 0)))
            else:
                base_amount = float(raw)
            override_applied = True
            pricing_source = "override"
        else:
            # Customer has special_pricing flag but no override for this service — use API
            result = get_pricing(service_type, tier=pricing_tier)
            base_amount = float(result.get("price", result.get("amount", 0)))
    else:
        result = get_pricing(service_type, tier=pricing_tier)
        base_amount = float(result.get("price", result.get("amount", 0)))

    elevation_cert_amount = ELEVATION_CERT_PRICE if elevation_cert_required else 0
    total_amount = base_amount + elevation_cert_amount

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
        input_summary=f"service={service_type} tier={pricing_tier} special={special_pricing}",
        output_summary=f"total={total_amount} source={pricing_source}",
        model_used=PRICING_MODEL,
    )

    log.info(
        "priced order=%s total=%.2f tier=%s source=%s",
        order_id, total_amount, pricing_tier, pricing_source,
    )

    return {
        "order_id": order_id,
        "base_amount": base_amount,
        "elevation_cert_amount": elevation_cert_amount,
        "total_amount": total_amount,
        "pricing_tier": pricing_tier,
        "override_applied": override_applied,
        "pricing_source": pricing_source,
    }


if __name__ == "__main__":
    # Standalone run: orchestrator calls price_order(classification) directly.
    # This entry point exists for manual testing only.
    log.info("pricing engine ready — call price_order(classification) via orchestrator")
