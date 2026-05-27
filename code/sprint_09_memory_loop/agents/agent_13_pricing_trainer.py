"""Agent 13 — Pricing Trainer (I-067)

Ryan (2026-05-26): "Robert should be able to say 'this 100-acre job, here's how I'd bill
and why' and the AI stores it and uses it going forward. Just like training a new person
— build on it each time."

Accepts a structured pricing example from Robert or Mark and persists it to the
pricing_examples table. The pricing engine loads these examples as context when
estimating future jobs of the same service type / county.

Hard rules (I-069 governance):
  - Only 'robert' or 'mark' roles may submit pricing/logistics domain entries
  - Only 'jessica' may submit ar/refund domain entries
  - Cross-domain attempts → GovernanceError; never silently overwritten
  - Superusers (ryan, prateek) bypass domain checks

Input schema:
  {
    "entered_by": "Robert",             # required — role identity
    "job_description": "...",           # required — plain English job description
    "final_price": 700.00,              # required — actual price charged
    "service_type": "Boundary Survey",  # optional — canonical FTF service name
    "county": "Palm Beach",             # optional — Florida county
    "lot_size_acres": 0.5,              # optional
    "complexity_notes": "pool, 2 sheds, 30 corners",  # optional
    "pricing_rationale": "...",         # optional — why this price was set
    "domain": "pricing",                # optional — defaults to 'pricing'
  }
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from core.db import save_pricing_example, get_recent_pricing_examples, log_decision
from core.exceptions import AgentError
from core.governance import GovernanceError, check_permission
from core.logger import get_logger

AGENT_NAME = "agent_13_pricing_trainer"
log = get_logger(AGENT_NAME)


def submit_pricing_example(example: dict) -> dict:
    """Validate governance, persist example, return confirmation.

    Returns:
      {"saved": True, "id": <int>, "entered_by": str, "service_type": str}
    or raises GovernanceError if role is not permitted.
    """
    entered_by = (example.get("entered_by") or "").strip()
    if not entered_by:
        raise AgentError("submit_pricing_example: 'entered_by' is required")

    job_description = (example.get("job_description") or "").strip()
    if not job_description:
        raise AgentError("submit_pricing_example: 'job_description' is required")

    final_price = example.get("final_price")
    if final_price is None or float(final_price) <= 0:
        raise AgentError("submit_pricing_example: 'final_price' must be a positive number")

    domain = (example.get("domain") or "pricing").lower()

    # I-069: enforce role-domain permission before any DB write
    check_permission(entered_by, domain)

    row_id = save_pricing_example(
        job_description=job_description,
        final_price=float(final_price),
        service_type=example.get("service_type"),
        county=example.get("county"),
        lot_size_acres=example.get("lot_size_acres"),
        complexity_notes=example.get("complexity_notes"),
        pricing_rationale=example.get("pricing_rationale"),
        entered_by=entered_by,
        domain=domain,
    )

    log_decision(
        AGENT_NAME,
        "pricing_example_saved",
        reason=f"entered_by={entered_by} service_type={example.get('service_type')} "
               f"county={example.get('county')} price=${final_price}",
        input_summary=job_description[:200],
        output_summary=f"saved as pricing_examples id={row_id}",
    )

    log.info(
        "pricing example saved id=%d by=%s service=%s county=%s price=%.2f",
        row_id, entered_by,
        example.get("service_type", "—"),
        example.get("county", "—"),
        float(final_price),
    )

    return {
        "saved": True,
        "id": row_id,
        "entered_by": entered_by,
        "service_type": example.get("service_type"),
        "county": example.get("county"),
        "final_price": float(final_price),
    }


def get_training_summary(limit: int = 10) -> list[dict]:
    """Return the most recent pricing examples for review."""
    return get_recent_pricing_examples(limit=limit)


if __name__ == "__main__":
    import json
    examples = get_training_summary()
    print(f"Recent pricing examples ({len(examples)}):")
    for ex in examples:
        print(f"  [{ex['id']}] {ex.get('service_type', '—')} | {ex.get('county', '—')} | "
              f"${ex['final_price']:.2f} | by={ex['entered_by']}")
