"""Agent A7 — Feedback Learner

Reads recently completed approved orders (invoice_sent / invoice_finalized) from the
pipeline state DB, extracts per-service approved prices, and persists patterns to
data/learned_rules.json for A3 to use in future pricing prompts.

Learning threshold: a (service, county) combination is promoted to 'active' only after
2+ approvals at a consistent price (within ±5%). A single approval is stored as 'pending'
to guard against one-time outliers poisoning future pricing.

Status flow: reads invoice_sent / invoice_finalized orders only (read-only, no status change)
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from core.excel_db import get_orders_by_status
from core.logger import get_logger

AGENT_NAME = "agent_a7_feedback_learner"
log = get_logger(AGENT_NAME)

_RULES_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "learned_rules.json")
)
_PROMOTION_THRESHOLD = 2   # approvals needed before a rule becomes active
_PRICE_VARIANCE_PCT  = 0.05  # ±5% tolerance for "consistent price"


def _load_rules() -> dict:
    try:
        with open(_RULES_FILE) as f:
            return json.load(f)
    except Exception:
        return {"rules": [], "order_overrides": {}}


def _save_rules(data: dict) -> None:
    os.makedirs(os.path.dirname(_RULES_FILE), exist_ok=True)
    with open(_RULES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _prices_consistent(existing_price: float, new_price: float) -> bool:
    """Return True if prices are within ±5% of each other."""
    if existing_price == 0:
        return False
    return abs(existing_price - new_price) / existing_price <= _PRICE_VARIANCE_PCT


def run() -> dict:
    """Scan completed orders and update learned_rules.json with per-service price patterns."""
    completed = (
        get_orders_by_status("invoice_sent")
        + get_orders_by_status("invoice_finalized")
    )
    if not completed:
        log.info("a7_feedback_learner: no completed orders to learn from")
        return {"learned": 0, "promoted": 0}

    data = _load_rules()
    data.setdefault("rules", [])

    # Build lookup: key=(service_type, county) → existing rule index in data["rules"]
    rule_index: dict = {}
    for i, r in enumerate(data["rules"]):
        if r.get("type") == "approved_service_price":
            key = (r.get("service_type", "").lower(), r.get("county", "").lower())
            rule_index[key] = i

    learned = 0
    promoted = 0

    for db_row in completed:
        order_id  = db_row.get("order_id", "")
        approved_by = db_row.get("approved_by", "")
        if not approved_by:
            continue  # skip — no human approval on record

        raw_draft = db_row.get("invoice_draft")
        if not raw_draft:
            continue
        draft = json.loads(raw_draft) if isinstance(raw_draft, str) else raw_draft

        services = draft.get("services", [])
        if not services:
            continue

        raw_sources = db_row.get("data_sources")
        ds = json.loads(raw_sources) if isinstance(raw_sources, str) else (raw_sources or {})
        county = (ds.get("packet") or {}).get("property_county", {}).get("value", "") or ""
        county = county.strip()

        for svc in services:
            svc_name = (svc.get("name") or db_row.get("service_type", "") or "").strip()
            amount   = float(svc.get("amount", 0) or 0)
            if not svc_name or amount <= 0:
                continue

            key = (svc_name.lower(), county.lower())

            if key in rule_index:
                # Update existing rule
                rule = data["rules"][rule_index[key]]
                existing_price = float(rule.get("price", 0))
                count          = int(rule.get("approved_count", 1))

                if _prices_consistent(existing_price, amount):
                    rule["approved_count"] = count + 1
                    rule["last_order"]     = order_id
                    rule["last_seen"]      = datetime.utcnow().strftime("%Y-%m-%d")
                    # Promote to active once threshold reached
                    if rule["approved_count"] >= _PROMOTION_THRESHOLD and rule.get("status") == "pending":
                        rule["status"]      = "active"
                        rule["description"] = (
                            f"{svc_name} in {county or 'any county'} approved at "
                            f"${amount:.2f} ({rule['approved_count']} approvals, "
                            f"last: order {order_id})"
                        )
                        promoted += 1
                        log.info(
                            "a7: PROMOTED rule — %s / %s = $%.2f (%d approvals)",
                            svc_name, county, amount, rule["approved_count"],
                        )
                    learned += 1
                else:
                    # Price changed significantly — reset to pending with new price
                    rule["price"]          = amount
                    rule["approved_count"] = 1
                    rule["status"]         = "pending"
                    rule["last_order"]     = order_id
                    rule["last_seen"]      = datetime.utcnow().strftime("%Y-%m-%d")
                    rule["description"]    = (
                        f"{svc_name} in {county or 'any county'} — price changed to "
                        f"${amount:.2f} (reset to pending, order {order_id})"
                    )
                    learned += 1
            else:
                # New service+county combination — add as pending
                new_rule = {
                    "type":           "approved_service_price",
                    "status":         "pending",
                    "service_type":   svc_name,
                    "county":         county,
                    "price":          amount,
                    "approved_count": 1,
                    "description":    (
                        f"{svc_name} in {county or 'any county'} approved at "
                        f"${amount:.2f} (1 approval, order {order_id})"
                    ),
                    "last_order":     order_id,
                    "last_seen":      datetime.utcnow().strftime("%Y-%m-%d"),
                }
                data["rules"].append(new_rule)
                rule_index[key] = len(data["rules"]) - 1
                learned += 1
                log.info(
                    "a7: new pending rule — %s / %s = $%.2f (order %s)",
                    svc_name, county, amount, order_id,
                )

    _save_rules(data)
    log.info("a7_feedback_learner: learned=%d promoted=%d", learned, promoted)
    return {"learned": learned, "promoted": promoted}


def main(argv=None) -> None:
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
