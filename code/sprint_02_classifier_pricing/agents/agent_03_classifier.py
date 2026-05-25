import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone

from config.flag_triggers import ALWAYS_FLAG_SERVICES, NEVER_AUTO_QUOTE
from config.models import CLASSIFIER_MODEL
from config.settings import SERVICE_STATE
from core.db import log_decision, save_order_state
from core.exceptions import FEMAUnavailableError
from core.fema_client import check_flood_zone
from core.ftf_client import get_order
from core.logger import get_logger

AGENT_NAME = "agent_03_classifier"
log = get_logger(AGENT_NAME)

# customer_type values from FTF API that map to b2b pricing tier
_B2B_TYPES = frozenset({"b2b", "company", "business"})


def classify_order(order_id: str) -> dict:
    """Fetch order from FTF API, classify it, persist result to DB.

    Applies flag triggers: ALWAYS_FLAG_SERVICES, NEVER_AUTO_QUOTE, unresolved
    service_type, missing county (I-036), false FL coordinate (I-037),
    FEMA VE coastal zone (I-035), and FEMA unavailability.

    Returns classification dict.
    """
    order = get_order(order_id)

    service_type: str = (order.get("service_type") or "").strip()
    customer_type: str = (order.get("customer_type") or "individual").strip()
    pricing_tier: str = "b2b" if customer_type.lower() in _B2B_TYPES else "individual"
    special_pricing: bool = bool(order.get("special_pricing", False))

    property_lat = order.get("property_lat")
    property_lng = order.get("property_lng")
    property_state: str = (order.get("property_state") or "").upper().strip()
    property_county: str = (order.get("property_county") or "").strip()
    customer_email: str = (order.get("customer_email") or "").strip()

    flag_for_human = False
    flag_reasons: list[str] = []
    flood_zone = "UNKNOWN"
    is_flood_zone = False
    elevation_cert_required = False

    def _flag(reason: str) -> None:
        nonlocal flag_for_human
        flag_for_human = True
        flag_reasons.append(reason)

    # --- Static service flags ---
    if service_type in ALWAYS_FLAG_SERVICES:
        _flag(f"service requires human review: {service_type}")
    elif service_type in NEVER_AUTO_QUOTE:
        _flag(f"never-auto-quote service: {service_type}")
    elif not service_type or service_type.lower() == "quote":
        _flag("service_type unresolved as 'Quote' — human must identify correct service")

    # --- Data quality flags ---
    if not property_county:
        _flag("missing property_county — cannot determine price without county")  # I-036

    if property_state == SERVICE_STATE and property_lat is not None:
        try:
            if float(property_lat) > 31.0:
                _flag(
                    f"property_state=FL but lat={float(property_lat):.4f} is outside Florida bounds — data entry error"
                )  # I-037
        except (TypeError, ValueError):
            pass

    # --- FEMA flood zone ---
    if property_lat is not None and property_lng is not None:
        try:
            flood_zone = check_flood_zone(float(property_lat), float(property_lng))
            is_flood_zone = flood_zone.startswith(("A", "V"))
            elevation_cert_required = is_flood_zone
            if flood_zone.startswith("V"):
                _flag(f"FEMA zone {flood_zone} — coastal/tidal high-hazard, human review required")  # I-035
        except FEMAUnavailableError:
            flood_zone = "UNAVAILABLE"
            _flag("FEMA API unavailable — cannot determine flood zone")

    flag_reason: str | None = "; ".join(flag_reasons) if flag_reasons else None
    new_status = "flagged" if flag_for_human else "classified"

    # --- Persist to DB ---
    save_kwargs: dict = dict(
        status=new_status,
        service_type=service_type,
        is_flood_zone=is_flood_zone,
        classified_at=datetime.now(timezone.utc).isoformat(),
    )
    if customer_email:
        save_kwargs["customer_email"] = customer_email
    if property_lat is not None:
        save_kwargs["property_lat"] = property_lat
    if property_lng is not None:
        save_kwargs["property_lng"] = property_lng
    if flag_for_human:
        save_kwargs["flag_reason"] = flag_reason
        save_kwargs["flagged_at"] = datetime.now(timezone.utc).isoformat()

    save_order_state(order_id, **save_kwargs)

    log_decision(
        agent_name=AGENT_NAME,
        decision=new_status,
        order_id=order_id,
        reason=flag_reason if flag_for_human else f"tier={pricing_tier} zone={flood_zone}",
        input_summary=f"service={service_type} county={property_county or 'MISSING'} state={property_state}",
        output_summary=f"tier={pricing_tier} flood={flood_zone} flag={flag_for_human}",
        model_used=CLASSIFIER_MODEL,
    )

    log.info(
        "classified order=%s status=%s flood=%s flag=%s",
        order_id, new_status, flood_zone, flag_for_human,
    )

    return {
        "order_id": order_id,
        "service_type": service_type,
        "customer_type": customer_type,
        "pricing_tier": pricing_tier,
        "special_pricing": special_pricing,
        "is_flood_zone": is_flood_zone,
        "flood_zone": flood_zone,
        "elevation_cert_required": elevation_cert_required,
        "flag_for_human": flag_for_human,
        "flag_reason": flag_reason,
        "property_county": property_county or None,
        "property_state": property_state,
        "customer_email": customer_email,
    }


def run() -> str | None:
    """Classify the next pending order from DB. Returns order_id or None."""
    from core.db import get_pending_order

    order_rec = get_pending_order()
    if not order_rec:
        log.info("no pending orders")
        return None
    return classify_order(order_rec["order_id"])["order_id"]


if __name__ == "__main__":
    run()
