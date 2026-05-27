import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
# Sprint 4 writer must be importable for the retry-rewrite loop
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sprint_04_writer"))

from datetime import datetime, timezone
from pathlib import Path

from agents.agent_06_writer import write_estimate
from config.models import REVIEWER_MODEL
from config.settings import MAX_REVIEWER_RETRIES
from core.db import get_order_by_id, get_written_order, log_decision, save_order_state
from core.exceptions import AgentError, ReviewerFailError
from core.ftf_client import get_order
from core.logger import get_logger

AGENT_NAME = "agent_07_reviewer"
log = get_logger(AGENT_NAME)

_SHARED_ROOT = Path(__file__).parent.parent.parent / "shared"
_CLAUSE_PATH = _SHARED_ROOT / "config" / "knowledge_base" / "change_order_clause.txt"


def _load_clause() -> str:
    return _CLAUSE_PATH.read_text(encoding="utf-8").strip()


def _extract_customer_name(order: dict) -> str:
    name = order.get("customer_name") or ""
    if not name:
        first = order.get("first_name") or ""
        last = order.get("last_name") or ""
        name = f"{first} {last}".strip()
    if not name:
        name = order.get("company_name") or ""
    return name


def _extract_property_address(order: dict) -> str:
    addr = order.get("property_address") or order.get("address") or ""
    if not addr:
        city = order.get("property_city") or ""
        state = order.get("property_state") or "FL"
        addr = f"{city}, {state}".strip(", ")
    return addr


def _run_checks(
    draft: str,
    estimate_amount: float,
    customer_name: str,
    property_address: str,
    clause: str,
) -> list[str]:
    """Run the 4 validation checks. Return list of failure descriptions (empty = all pass)."""
    failures: list[str] = []

    # Check 1 — Price
    amount_fmt = f"{estimate_amount:,.2f}"
    amount_plain = f"{estimate_amount:.2f}"
    if amount_fmt not in draft and amount_plain not in draft:
        failures.append(f"price ${amount_fmt} not found in estimate")

    # Check 2 — Customer name
    if customer_name and customer_name.lower() not in draft.lower():
        failures.append(f"customer name '{customer_name}' not found in estimate")

    # Check 3 — Property address (require at least the first 3 significant tokens)
    if property_address:
        tokens = [t for t in property_address.replace(",", " ").split() if len(t) > 2]
        missing = [t for t in tokens[:3] if t.lower() not in draft.lower()]
        if missing:
            failures.append(f"property address parts {missing} not found in estimate")

    # Check 4 — Change order clause (whitespace-normalized exact match)
    clause_norm = " ".join(clause.split())
    draft_norm = " ".join(draft.split())
    if clause_norm not in draft_norm:
        failures.append("change order clause missing or modified")

    return failures


def review_estimate(order_id: str) -> dict:
    """Validate the draft estimate for an order.

    Runs 4 checks. On failure, triggers a rewrite (Agent 6) and re-checks.
    After MAX_REVIEWER_RETRIES consecutive failures, raises ReviewerFailError
    and escalates the order back to the human gate (status='flagged').

    Returns {"order_id": ..., "status": "reviewed", "checks_passed": 4}.
    Raises ReviewerFailError after exhausting all retries.
    Raises AgentError if the order or its draft_estimate is missing.
    """
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"review_estimate: order {order_id} not found in processed_orders")

    order = get_order(order_id)
    estimate_amount = float(db_row.get("estimate_amount") or 0.0)
    customer_name = _extract_customer_name(order)
    property_address = _extract_property_address(order)
    clause = _load_clause()

    retry_count: int = int(db_row.get("retry_count") or 0)
    pre_correction_draft: str | None = None  # I-028: capture first draft before any correction

    for attempt in range(1, MAX_REVIEWER_RETRIES + 1):
        # Use already-fetched db_row on first attempt; re-fetched below after each rewrite
        draft = db_row.get("draft_estimate") or ""
        if not draft:
            raise AgentError(
                f"review_estimate: order {order_id} has no draft_estimate — Writer must run first"
            )

        # I-028: capture the original draft before any correction loop begins
        if attempt == 1:
            pre_correction_draft = draft

        failures = _run_checks(draft, estimate_amount, customer_name, property_address, clause)

        if not failures:
            save_order_state(
                order_id,
                status="reviewed",
                reviewed_at=datetime.now(timezone.utc).isoformat(),
            )
            # I-028: log pre vs post correction for Sprint 7 demo side-by-side view
            correction_applied = attempt > 1
            if correction_applied:
                log.info(
                    "reviewer correction applied order=%s attempts=%s "
                    "pre_draft_len=%s post_draft_len=%s",
                    order_id, attempt,
                    len(pre_correction_draft or ""),
                    len(draft),
                )
            log_decision(
                agent_name=AGENT_NAME,
                decision="reviewed",
                order_id=order_id,
                reason=f"all 4 checks passed on attempt {attempt}",
                input_summary=f"amount={estimate_amount:.2f} customer={customer_name}",
                output_summary=(
                    f"status=reviewed correction_applied={correction_applied} "
                    f"pre_len={len(pre_correction_draft or '')} post_len={len(draft)}"
                ),
                model_used=REVIEWER_MODEL,
            )
            log.info("estimate reviewed order=%s attempt=%s", order_id, attempt)
            return {
                "order_id": order_id,
                "status": "reviewed",
                "checks_passed": 4,
                "correction_applied": correction_applied,
                "pre_correction_draft": pre_correction_draft if correction_applied else None,
                "post_correction_draft": draft if correction_applied else None,
            }

        # Checks failed
        log.warning(
            "reviewer attempt=%s/%s failures=%s order=%s",
            attempt, MAX_REVIEWER_RETRIES, failures, order_id,
        )

        retry_count += 1

        if attempt >= MAX_REVIEWER_RETRIES:
            flag_reason = (
                f"Reviewer failed {MAX_REVIEWER_RETRIES}x — "
                + "; ".join(failures)
            )
            save_order_state(
                order_id,
                status="flagged",
                flag_reason=flag_reason,
                flagged_at=datetime.now(timezone.utc).isoformat(),
                retry_count=retry_count,
            )
            log_decision(
                agent_name=AGENT_NAME,
                decision="failed",
                order_id=order_id,
                reason=flag_reason,
                input_summary=f"amount={estimate_amount:.2f}",
                output_summary=f"escalated after {attempt} attempts",
                model_used=REVIEWER_MODEL,
            )
            log.error("reviewer escalating order=%s after %s failures", order_id, attempt)
            raise ReviewerFailError(flag_reason)

        # Trigger rewrite with correction feedback, then re-fetch DB row for next attempt
        correction_note = "Fix the following: " + "; ".join(failures)
        save_order_state(order_id, retry_count=retry_count)
        write_estimate(order_id, correction_note=correction_note)
        db_row = get_order_by_id(order_id) or db_row

    # Should be unreachable
    raise ReviewerFailError(f"Review loop exited unexpectedly for order {order_id}")


def run() -> dict | None:
    """Review the next written order. Returns result dict or None."""
    order_rec = get_written_order()
    if not order_rec:
        log.info("no written orders awaiting review")
        return None
    return review_estimate(order_rec["order_id"])


if __name__ == "__main__":
    run()
