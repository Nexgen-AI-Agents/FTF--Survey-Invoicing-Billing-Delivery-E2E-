import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone
from pathlib import Path

from config.flag_triggers import ALWAYS_FLAG_SERVICES, COMPETITOR_DOMAINS, COMPETITOR_NAMES, NEVER_AUTO_QUOTE
from config.models import CLASSIFIER_MODEL
from config.settings import SERVICE_STATE
from core.claude_client import call as llm_call
from core.db import log_decision, save_order_state

# Hermes (local, free) is preferred for service-type normalization — structured JSON,
# zero API cost, no data egress. Falls back to Claude if Ollama is not running.
try:
    from core.hermes_client import normalize_service_type as _hermes_normalize
    _HERMES_AVAILABLE = True
except Exception:
    _HERMES_AVAILABLE = False
from core.exceptions import FEMAUnavailableError
from core.fema_client import check_flood_zone
from core.ftf_client import get_order
from core.logger import get_logger

AGENT_NAME = "agent_03_classifier"
log = get_logger(AGENT_NAME)

_SHARED_ROOT = Path(__file__).parent.parent.parent / "shared"
_CLASSIFIER_PROMPT_PATH = _SHARED_ROOT / "config" / "prompts" / "classifier.txt"

_UNRECOGNIZED = "UNRECOGNIZED_SERVICE_TYPE"

_CANONICAL_SERVICES: frozenset[str] = frozenset({
    "Acreage", "ALTA Table A Survey", "B-II Title Review", "Boundary Survey",
    "Building Stake Out", "Elevation Certificate", "Elevation Only", "Final Survey",
    "Form Board Survey", "Foundation Tie-In", "Legal Description", "Lot Split",
    "Other Services", "Pad Stake Out", "Property Flagging", "Site Plan",
    "Sketch and Description", "Specific Purpose Survey", "Survey Re-draw",
    "Surveyor's Affidavit", "Topography Survey", "Tree Location", "Update Survey",
    "Wetland Delineation",
})

# Deterministic informal-name -> canonical-name mappings (Robert, Recording 1, 2026-05-25)
_SERVICE_TYPE_ALIASES: dict[str, str] = {
    "land survey only": "Boundary Survey",
    "land survey": "Boundary Survey",
    "special purpose survey": "Specific Purpose Survey",
    "construction survey": "Topography Survey",
    "permitting survey": "Boundary Survey",
    "spot survey": "Foundation Tie-In",
    "topo survey": "Topography Survey",
    "topographic survey": "Topography Survey",
    "topographic boundary survey": "Topography Survey",
    "update/topographic survey": "Update Survey",
    "re-survey": "Update Survey",
    "resurvey": "Update Survey",
    "as-built survey": "Final Survey",
    "boundary": "Boundary Survey",
    "elevation cert": "Elevation Certificate",
}

# customer_type values from FTF API that map to b2b pricing tier
_B2B_TYPES = frozenset({"b2b", "company", "business"})

# Informal survey type labels used in FTF CRM that are NOT in the pricing catalogue.
# Bundle descriptors, not priced services — flag for human to confirm scope.
_INFORMAL_SERVICE_TYPES = frozenset({"construction/permitting"})


def _load_classifier_prompt() -> str:
    return _CLASSIFIER_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _llm_normalize_service_type(raw: str) -> str:
    """Map an unrecognized service_type string to a canonical FTF name.

    Resolution order:
      1. Hermes 3 (local Ollama) — free, fast, zero data egress, structured JSON output
      2. Claude fallback — if Ollama is not running or Hermes model missing

    Returns canonical name if confident (Hermes confidence >= 0.7), else _UNRECOGNIZED.
    """
    # ── 1. Try Hermes (local, free) ───────────────────────────────────────
    if _HERMES_AVAILABLE:
        try:
            result = _hermes_normalize(raw)
            if not result.get("unrecognized") and result.get("canonical") in _CANONICAL_SERVICES:
                log.info(
                    "Hermes normalized '%s' -> '%s' (confidence=%.2f)",
                    raw, result["canonical"], result.get("confidence", 0),
                )
                return result["canonical"]
        except Exception as exc:
            log.debug("Hermes normalization unavailable (%s) — falling back to Claude", exc)

    # ── 2. Fall back to Claude ─────────────────────────────────────────────
    try:
        prompt = _load_classifier_prompt()
        result_str = llm_call(
            model=CLASSIFIER_MODEL,
            system=prompt,
            user=f'Map this FTF order service type to the canonical name: "{raw}"',
            max_tokens=30,
        ).strip()
        if result_str in _CANONICAL_SERVICES:
            log.info("Claude normalized service type '%s' -> '%s'", raw, result_str)
            return result_str
        log.warning("Claude returned non-canonical value '%s' for raw='%s'", result_str, raw)
    except Exception as exc:
        log.warning("LLM service type normalization failed raw=%s error=%s", raw, exc)
    return _UNRECOGNIZED


def _normalize_service_type(raw: str) -> str:
    """Normalize raw FTF service_type to a canonical FTF name.

    Resolution order:
      1. Empty / 'Quote' -> return as-is (downstream flag logic handles it)
      2. Already canonical -> return as-is
      3. In deterministic alias map -> return canonical alias
      4. In _INFORMAL_SERVICE_TYPES -> return as-is (downstream flag logic handles it)
      5. LLM fallback -> canonical name or _UNRECOGNIZED
    """
    if not raw or raw.lower() == "quote":
        return raw
    if raw in _CANONICAL_SERVICES:
        return raw
    alias = _SERVICE_TYPE_ALIASES.get(raw.lower().strip())
    if alias:
        log.info("alias normalized service type '%s' -> '%s'", raw, alias)
        return alias
    if raw.lower().strip() in _INFORMAL_SERVICE_TYPES:
        return raw
    return _llm_normalize_service_type(raw)


def classify_order(order_id: str) -> dict:
    """Fetch order from FTF API, classify it, persist result to DB.

    Flag triggers applied:
      Trigger 1 — ALWAYS_FLAG_SERVICES (ALTA, Other Services)
      Trigger 2 — NEVER_AUTO_QUOTE services
      Trigger 3 — competitor company name match
      Trigger 4 — competitor email domain match
      Trigger 5 — unresolved service_type ("Quote")
      Trigger 8 — FEMA VE coastal zone (I-035); FEMA unavailable
      Trigger 9 — property outside Florida (out-of-state)
      Data quality — missing county (I-036), false FL coordinate (I-037)
      Domain — Monroe County Florida Keys (I-034)

    Returns classification dict.
    """
    order = get_order(order_id)

    raw_service_type: str = (order.get("service_type") or "").strip()
    service_type: str = _normalize_service_type(raw_service_type)  # I-053: alias + LLM normalization

    customer_type: str = (order.get("customer_type") or "individual").strip()
    pricing_tier: str = "b2b" if customer_type.lower() in _B2B_TYPES else "individual"
    special_pricing: bool = bool(order.get("special_pricing", False))

    property_lat = order.get("property_lat")
    property_lng = order.get("property_lng")
    property_state: str = (order.get("property_state") or "").upper().strip()
    # I-050: FTF API returns full state name ("FLORIDA") — normalize to 2-letter code
    if property_state == "FLORIDA":
        property_state = "FL"
    property_county: str = (order.get("property_county") or "").strip()
    customer_email: str = (order.get("customer_email") or "").strip()
    company_name: str = (order.get("company_name") or "").strip()

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
    if not service_type or service_type.lower() == "quote":
        _flag("service_type unresolved as 'Quote' — human must identify correct service")
    elif service_type == _UNRECOGNIZED:
        _flag(
            f"unrecognized service type '{raw_service_type}' — not in FTF catalogue; "
            "human must identify and reclassify"
        )
    elif service_type in ALWAYS_FLAG_SERVICES:
        _flag(f"service requires human review: {service_type}")
    elif service_type in NEVER_AUTO_QUOTE:
        _flag(f"never-auto-quote service: {service_type}")
    elif service_type.lower() in _INFORMAL_SERVICE_TYPES:
        _flag(
            f"informal survey type '{service_type}' — bundle label, not a priced service; "
            "human must confirm scope and select correct service"
        )

    # --- Trigger 3: competitor company name ---
    if company_name:
        company_lower = company_name.lower()
        for name in COMPETITOR_NAMES:
            if name.lower() in company_lower:
                _flag(f"competitor company name match: {name}")
                break

    # --- Trigger 4: competitor email domain ---
    if "@" in customer_email:
        email_domain = customer_email.split("@")[-1].lower()
        if email_domain in COMPETITOR_DOMAINS:
            _flag(f"competitor email domain: {email_domain}")

    # --- Trigger 9: out-of-state property ---
    if property_state and property_state != SERVICE_STATE:
        _flag(f"property_state={property_state} — NexGen is FL-only, cannot auto-quote out-of-state")

    # --- I-034: Monroe County (Florida Keys) — non-standard pricing ---
    if property_county and "monroe" in property_county.lower():
        _flag("Monroe County (Florida Keys) — non-standard pricing, human review required")

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
        "company_name": company_name or None,
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
