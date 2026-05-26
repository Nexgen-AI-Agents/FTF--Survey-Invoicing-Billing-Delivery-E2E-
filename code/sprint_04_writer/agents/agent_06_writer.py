import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.models import WRITER_MODEL
from core.claude_client import call as llm_call
from core.db import get_order_by_id, get_ready_to_write_order, log_decision, save_order_state
from core.exceptions import AgentError
from core.ftf_client import get_order
from core.logger import get_logger

AGENT_NAME = "agent_06_writer"
log = get_logger(AGENT_NAME)

_SHARED_ROOT = Path(__file__).parent.parent.parent / "shared"
_CLAUSE_PATH = _SHARED_ROOT / "config" / "knowledge_base" / "change_order_clause.txt"
_PROMPT_PATH = _SHARED_ROOT / "config" / "prompts" / "estimate_writer.txt"

_B2B_TYPES = frozenset({"b2b", "company", "business"})


def _load_clause() -> str:
    return _CLAUSE_PATH.read_text(encoding="utf-8").strip()


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def _extract_customer_name(order: dict) -> str:
    """Best-effort customer name from FTF order fields."""
    name = order.get("customer_name") or ""
    if not name:
        first = order.get("first_name") or ""
        last = order.get("last_name") or ""
        name = f"{first} {last}".strip()
    if not name:
        name = order.get("company_name") or ""
    return name or "Valued Customer"


def _extract_property_address(order: dict) -> str:
    addr = order.get("property_address") or order.get("address") or ""
    if not addr:
        city = order.get("property_city") or ""
        state = order.get("property_state") or "FL"
        addr = f"{city}, {state}".strip(", ")
    return addr or "Address not provided"


def write_estimate(order_id: str, correction_note: Optional[str] = None) -> dict:
    """Generate a survey estimate email for a priced/approved order.

    correction_note: non-None on reviewer-triggered rewrites; injected into prompt
                     so the model knows what to fix.
    Returns {"order_id": ..., "draft_estimate": ..., "status": "written"}.
    Raises AgentError if required data is missing or LLM call fails.
    """
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"write_estimate: order {order_id} not found in processed_orders")

    estimate_amount: float = float(db_row.get("estimate_amount") or 0.0)
    if estimate_amount <= 0:
        raise AgentError(
            f"write_estimate: order {order_id} has no estimate_amount — pricing must run first"
        )

    order = get_order(order_id)

    service_type: str = db_row.get("service_type") or order.get("service_type") or "Survey"
    customer_email: str = db_row.get("customer_email") or order.get("customer_email") or ""
    customer_name: str = _extract_customer_name(order)
    property_address: str = _extract_property_address(order)
    customer_type: str = (order.get("customer_type") or "individual").lower()
    is_flood_zone: bool = bool(db_row.get("is_flood_zone", False))

    tone = "concise and professional" if customer_type in _B2B_TYPES else "warm and friendly"

    clause = _load_clause()
    system_prompt = _load_system_prompt()

    flood_note = "An Elevation Certificate is included in your estimate." if is_flood_zone else ""

    correction_section = ""
    if correction_note:
        correction_section = f"\nCORRECTION REQUIRED — previous version was rejected:\n{correction_note}\n"

    user_msg = (
        f"Generate a survey estimate email for the following order.\n\n"
        f"ORDER DETAILS:\n"
        f"- Order ID: {order_id}\n"
        f"- Customer Name: {customer_name}\n"
        f"- Customer Email: {customer_email}\n"
        f"- Property Address: {property_address}\n"
        f"- Service: {service_type}\n"
        f"- Total Amount: ${estimate_amount:,.2f}\n"
        f"- Flood Zone: {'Yes — ' + flood_note if is_flood_zone else 'No'}\n"
        f"- Tone: {tone}\n"
        f"{correction_section}\n"
        f"IMPORTANT: End the email with the following change order clause EXACTLY as written below — "
        f"do not modify a single word:\n\n"
        f"{clause}\n\n"
        f"Generate the estimate email now."
    )

    draft: str = llm_call(
        model=WRITER_MODEL,
        system=system_prompt,
        user=user_msg,
        max_tokens=1500,
    )

    save_order_state(
        order_id,
        status="written",
        draft_estimate=draft,
        written_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        agent_name=AGENT_NAME,
        decision="written",
        order_id=order_id,
        reason=f"tone={tone} correction={correction_note is not None}",
        input_summary=f"service={service_type} amount={estimate_amount:.2f} flood={is_flood_zone}",
        output_summary=f"draft_len={len(draft)} chars",
        model_used=WRITER_MODEL,
    )

    log.info(
        "estimate written order=%s amount=%.2f tone=%s correction=%s",
        order_id, estimate_amount, tone, correction_note is not None,
    )

    return {
        "order_id": order_id,
        "draft_estimate": draft,
        "status": "written",
    }


def run() -> dict | None:
    """Write the next ready-to-write order. Returns result dict or None."""
    order_rec = get_ready_to_write_order()
    if not order_rec:
        log.info("no orders ready to write")
        return None
    return write_estimate(order_rec["order_id"])


if __name__ == "__main__":
    run()
