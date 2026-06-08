"""Agent A4 — Human Gate v2 (Invoice Pipeline)

Processes approval decisions coming from the OneDrive Excel spreadsheet
via GitHub Actions workflow_dispatch (triggered by Power Automate).

Flow:
  User changes Status in FTF-Invoicing Agent.xlsx (Pending → Approve/Reject/Hold)
  → Power Automate detects change
  → calls GitHub Actions workflow_dispatch with {order_id, action, notes}
  → this agent reads INPUT_ORDER_ID / INPUT_ACTION / INPUT_NOTES env vars
  → updates pipeline state accordingly
  → marks the Excel row as Processed

Status transitions:
  invoice_draft_posted → invoice_approved  (approve)
  invoice_draft_posted → invoice_rejected  (reject)
  invoice_draft_posted → on_hold           (hold)
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
    APPROVED_SENDERS, APPROVED_SENDER_EMAILS, APPROVED_SENDER_EMAIL_MAP,
    FTF_ORDER_URL, MAX_INVOICE_MODIFICATIONS,
)
from core.claude_client import call as llm_call
from core.excel_db import (
    get_orders_awaiting_invoice_approval, get_order_by_id,
    get_orders_by_status,
    get_processed_reply_ids, increment_modification_count,
    mark_reply_processed, save_invoice_learning,
    save_order_state, log_decision,
)
from core.exceptions import AgentError
from core.logger import get_logger

AGENT_NAME = "agent_a4_human_gate_v2"
log = get_logger(AGENT_NAME)

_RULES_FILE    = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "learned_rules.json")
_PRICE_RE      = re.compile(r'\$?\s*(\d+(?:\.\d{1,2})?)', re.IGNORECASE)
# Parses "Boundary Survey: $475.00 | Elevation Cert: $150.00" → list of {name, amount}
_BREAKDOWN_RE  = re.compile(r'([^|$:]+?):\s*\$\s*([\d,]+(?:\.\d{1,2})?)\s*(?:\||$)')


def _is_approved_sender(sender_name: str, sender_email: str = "") -> bool:
    first = sender_name.strip().lower().split()[0] if sender_name.strip() else ""
    email_local = sender_email.split("@")[0].lower() if "@" in sender_email else ""
    name_match = first in APPROVED_SENDERS or email_local in APPROVED_SENDERS
    if not name_match:
        return False
    if APPROVED_SENDER_EMAILS and sender_email:
        if sender_email.lower() in APPROVED_SENDER_EMAILS:
            return True
        if email_local in APPROVED_SENDERS:
            log.warning("sender=%s email=%s — accepting on local-part match (UPN drift)",
                        sender_name, sender_email)
            return True
        log.warning(
            "sender=%s email=%s — display name matches but email not in approved list; "
            "accepting (check APPROVED_SENDERS secret has correct UPN for this user)",
            sender_name, sender_email,
        )
        return True
    return True


def _ai_parse_instruction(reply_text: str, current_draft: dict, order_id: str) -> dict:
    """Use Claude to interpret a natural language approval instruction."""
    prompt = f"""You work for NexGen Surveying. A team member replied to an invoice draft.

Reply text: "{reply_text}"

Current invoice draft:
{json.dumps(current_draft, indent=2, default=str)[:1500]}

Determine what the team member wants to do. Return ONLY valid JSON:
{{
  "action": "approve | reject | hold | modify | question | ignore",
  "email_override": "sender | null",
  "modification": {{
    "type": "change_price | add_service | remove_service | change_field | other",
    "description": "what specifically to change",
    "new_value": null,
    "service_name": null
  }},
  "reject_reason": null,
  "question_text": null,
  "confidence": "HIGH | MEDIUM | LOW",
  "status_message": "one natural sentence describing exactly what you understood",
  "learned_rule": "short sentence about what we learned from this"
}}

Rules:
- action=approve: they want to send the invoice
- action=reject: they want to cancel permanently
- action=hold: they want to pause without rejecting
- action=modify: they want to change something (price, service, add/remove)
- action=question: you are genuinely unsure
- action=ignore: random chat not related to this invoice
- confidence=LOW → always set action=question
"""
    try:
        result_str = llm_call(
            model=HUMAN_GATE_MODEL,
            system="You are an invoice approval assistant. Return only valid JSON.",
            user=prompt,
            max_tokens=300,
        ).strip()
        if result_str.startswith("```"):
            result_str = re.sub(r"^```[a-z]*\n?", "", result_str).rstrip("`").strip()
        return json.loads(result_str)
    except Exception as exc:
        log.warning("AI instruction parse failed: %s", exc)
        return {
            "action": "question",
            "modification": {},
            "reject_reason": None,
            "question_text": "I had trouble understanding your message. Could you reply with APPROVE, REJECT, or describe the change you'd like?",
            "confidence": "LOW",
            "learned_rule": "",
        }


def _apply_modification(draft: dict, modification: dict) -> dict:
    """Apply a modification instruction to the current draft dict."""
    mod_type     = modification.get("type", "other")
    description  = modification.get("description", "")
    new_value    = modification.get("new_value")
    service_name = modification.get("service_name", "")

    draft = json.loads(json.dumps(draft))  # deep copy

    if mod_type == "change_price":
        try:
            new_total = float(new_value)
            if len(draft.get("services", [])) == 1:
                draft["services"][0]["amount"] = new_total
            else:
                draft["invoice_notes"] = (
                    f"{draft.get('invoice_notes', '')} [Price adjusted to ${new_total:,.2f} by approver]"
                ).strip()
            draft["total_amount"] = new_total
        except (TypeError, ValueError):
            draft["invoice_notes"] = f"{draft.get('invoice_notes', '')} [Approver requested: {description}]".strip()

    elif mod_type == "add_service":
        from config.settings import ELEVATION_CERT_PRICE
        new_svc = {
            "name":        service_name or description,
            "description": service_name or description,
            "amount":      ELEVATION_CERT_PRICE if "elevation" in (service_name or "").lower() else 0.0,
        }
        draft.setdefault("services", []).append(new_svc)
        draft["total_amount"] = sum(s.get("amount", 0) for s in draft["services"])
        if new_svc["amount"] == 0.0:
            draft.setdefault("questions_for_approver", []).append(
                f"What price should I use for {service_name}?"
            )

    elif mod_type == "remove_service":
        before = len(draft.get("services", []))
        draft["services"] = [
            s for s in draft.get("services", [])
            if service_name.lower() not in s.get("name", "").lower()
        ]
        if len(draft.get("services", [])) == before:
            draft["invoice_notes"] = f"{draft.get('invoice_notes', '')} [Note: '{service_name}' not found in current services to remove]".strip()
        draft["total_amount"] = sum(s.get("amount", 0) for s in draft["services"])

    else:
        draft["invoice_notes"] = f"{draft.get('invoice_notes', '')} [Requested change: {description}]".strip()

    return draft


def _store_learning(
    order_id: str,
    original_draft: dict,
    human_reply: str,
    learned_rule: str,
    data_sources: dict,
    entered_by: str,
) -> None:
    try:
        packet   = data_sources.get("packet", {})
        svc_type = ""
        svcs     = packet.get("services_requested", {}).get("value", [])
        if svcs:
            svc_type = svcs[0] if isinstance(svcs, list) else str(svcs)
        county = packet.get("property_county", {}).get("value", "")
        save_invoice_learning(
            order_id=order_id,
            original_draft=json.dumps(original_draft, default=str)[:2000],
            human_correction=human_reply[:500],
            learned_rule=learned_rule,
            service_type=svc_type,
            county=county,
            entered_by=entered_by,
        )
        log.info("learning saved order=%s", order_id)
    except Exception as exc:
        log.warning("failed to save learning order=%s: %s", order_id, exc)


def _save_learned_price(service_type: str, county: str, amount: float, learned_from: str, order_id: str) -> None:
    """Persist a user-provided price to learned_rules.json for A3 to reuse."""
    try:
        try:
            with open(_RULES_FILE) as f:
                data = json.load(f)
        except Exception:
            data = {"rules": [], "order_overrides": {}}
        data.setdefault("rules", [])
        data["rules"].append({
            "type":         "user_price_override",
            "status":       "active",
            "service_type": service_type,
            "county":       county,
            "price":        amount,
            "description":  (
                f"User-taught price: {service_type} in {county or 'any county'} = ${amount:.2f}"
                f" (taught by {learned_from}, order {order_id})"
            ),
        })
        with open(_RULES_FILE, "w") as f:
            json.dump(data, f, indent=2)
        log.info("learned price saved: %s / %s = $%.2f (from %s)", service_type, county, amount, learned_from)
    except Exception as exc:
        log.warning("failed to save learned price: %s", exc)


def _parse_breakdown_str(s: str) -> list:
    """Parse 'Boundary Survey: $475.00 | Elevation Cert: $150.00' into [{name, amount}, ...].

    Returns empty list if string is not in breakdown format (e.g. legacy bare-name rows).
    """
    return [
        {"name": m.group(1).strip(), "amount": float(m.group(2).replace(",", ""))}
        for m in _BREAKDOWN_RE.finditer(s)
    ]


def _apply_total_override(draft: dict, new_total: float) -> dict:
    """User changed Amount ($) only. Distribute new total proportionally across all services."""
    draft    = json.loads(json.dumps(draft))  # deep copy
    services = draft.get("services", [])
    orig_total = float(draft.get("total_amount", 0) or 0)

    if not services:
        draft["total_amount"] = new_total
        return draft

    if orig_total == 0:
        # No original total to distribute from — split evenly
        share = round(new_total / len(services), 2)
        for svc in services:
            svc["amount"] = share
        services[0]["amount"] = round(new_total - share * (len(services) - 1), 2)
    else:
        ratio = new_total / orig_total
        for svc in services:
            svc["amount"] = round(float(svc.get("amount", 0)) * ratio, 2)
        # Correct rounding penny on first service
        computed = sum(s["amount"] for s in services)
        if abs(computed - new_total) > 0.005:
            services[0]["amount"] = round(services[0]["amount"] + (new_total - computed), 2)

    draft["total_amount"] = new_total
    draft["services"]     = services
    return draft


def _apply_breakdown_override(draft: dict, parsed_breakdown: list) -> dict:
    """User edited individual service amounts in the breakdown cell. Apply per-service amounts."""
    draft    = json.loads(json.dumps(draft))  # deep copy
    services = draft.get("services", [])

    # Build name→amount from what the user typed
    user_prices = {item["name"].lower(): item["amount"] for item in parsed_breakdown}

    for svc in services:
        key = (svc.get("name") or "").lower()
        if key in user_prices:
            svc["amount"] = user_prices[key]
        else:
            # Substring match — e.g. "boundary" matches "Boundary Survey"
            for k, v in user_prices.items():
                if k in key or key in k:
                    svc["amount"] = v
                    break

    draft["total_amount"] = round(sum(s.get("amount", 0) for s in services), 2)
    draft["services"]     = services
    return draft


def _build_breakdown_str_from_draft(services: list) -> str:
    """Rebuild the Excel breakdown string from invoice_draft services list."""
    parts = []
    for svc in services:
        name = (svc.get("name") or "").strip()
        amt  = svc.get("amount", 0.0)
        if name and amt:
            parts.append(f"{name}: ${float(amt):.2f}")
        elif name:
            parts.append(name)
    return " | ".join(p for p in parts if p)


def process_dispatch_input() -> dict:
    """Handle a single order from GitHub Actions workflow_dispatch inputs.

    Power Automate watches FTF-Invoicing Agent.xlsx and calls workflow_dispatch
    when the user changes Status column from Pending → Approve / Reject / Hold.
    """
    order_id       = os.getenv("INPUT_ORDER_ID",  "").strip()
    action         = os.getenv("INPUT_ACTION",    "").strip().lower()
    notes          = os.getenv("INPUT_NOTES",     "").strip()
    excel_amount   = os.getenv("INPUT_AMOUNT",    "").strip()
    excel_breakdown= os.getenv("INPUT_BREAKDOWN", "").strip()

    if not order_id or not action:
        log.warning("workflow_dispatch: INPUT_ORDER_ID or INPUT_ACTION not set")
        return {"ok": False, "reason": "missing inputs"}

    db_row = get_order_by_id(order_id)
    if not db_row:
        log.error("workflow_dispatch: order %s not found in pipeline state", order_id)
        return {"ok": False, "reason": "order not found"}

    # Guard: skip if order already past approval stage (prevents duplicate invoices from stale Excel rows)
    current_status = db_row.get("status", "")
    _TERMINAL = {"invoice_finalized", "invoice_sent", "invoice_approved"}
    if action == "approve" and current_status in _TERMINAL:
        log.warning("dispatch: order %s already in %s — skipping re-approval (stale Excel row)",
                    order_id, current_status)
        try:
            from core.onedrive_excel_client import mark_row_processed
            mark_row_processed(order_id)
        except Exception:
            pass
        return {"ok": True, "order_id": order_id, "action": "skipped", "reason": f"already {current_status}"}

    # Guard: block approval of orders that require manual intervention — cannot be auto-processed
    _BLOCKED = {"condo_rejected"}
    if action == "approve" and current_status in _BLOCKED:
        log.warning(
            "dispatch: order %s is %s — approval blocked; manual intervention required",
            order_id, current_status,
        )
        return {
            "ok": False,
            "order_id": order_id,
            "action": "blocked",
            "reason": (
                f"Order is '{current_status}' and cannot be approved through the pipeline. "
                "Manual intervention required — contact client and handle outside the system."
            ),
        }

    if action == "approve":
        # ── Amount reconciliation: pick up any user edits to col E (breakdown) or col F (total) ──
        raw_draft = db_row.get("invoice_draft")
        draft = json.loads(raw_draft) if isinstance(raw_draft, str) else (raw_draft or {})
        orig_total = float(draft.get("total_amount", 0) or 0)

        parsed_breakdown = _parse_breakdown_str(excel_breakdown)
        orig_service_amounts = {
            (s.get("name") or "").lower(): float(s.get("amount", 0))
            for s in draft.get("services", [])
        }
        # Detect whether the user changed per-service amounts in the breakdown cell
        amounts_changed = parsed_breakdown and any(
            abs(item["amount"] - orig_service_amounts.get(item["name"].lower(), -1)) > 0.01
            for item in parsed_breakdown
        )

        try:
            excel_total = float(excel_amount.replace(",", "").replace("$", ""))
        except (ValueError, TypeError):
            excel_total = orig_total

        total_changed = abs(excel_total - orig_total) > 0.01

        if amounts_changed:
            # User edited individual service amounts — use breakdown values, recalculate total
            draft = _apply_breakdown_override(draft, parsed_breakdown)
            log.info(
                "dispatch: order=%s breakdown-level price edit applied, new total=%.2f",
                order_id, draft["total_amount"],
            )
        elif total_changed:
            # User edited total only — distribute proportionally
            draft = _apply_total_override(draft, excel_total)
            log.info(
                "dispatch: order=%s total-only price edit applied %.2f→%.2f",
                order_id, orig_total, excel_total,
            )

        # Write reconciled values back to Excel so both columns stay in sync
        if amounts_changed or total_changed:
            new_breakdown = _build_breakdown_str_from_draft(draft.get("services", []))
            try:
                from core.onedrive_excel_client import sync_approval_amounts
                sync_approval_amounts(order_id, draft["total_amount"], new_breakdown)
            except Exception as exc:
                log.warning("sync_approval_amounts failed order=%s (non-fatal): %s", order_id, exc)
            # Persist the updated draft
            save_order_state(order_id, invoice_draft=json.dumps(draft, default=str))
            # Save a learned price rule when user explicitly changed the amount
            service_type = db_row.get("service_type", "")
            raw_sources = db_row.get("data_sources")
            ds = json.loads(raw_sources) if isinstance(raw_sources, str) else (raw_sources or {})
            county = (ds.get("packet") or {}).get("property_county", {}).get("value", "")
            _save_learned_price(
                service_type=service_type,
                county=county,
                amount=draft["total_amount"],
                learned_from="excel_edit",
                order_id=order_id,
            )

        save_order_state(order_id, status="invoice_approved", approved_by="prateek")
        log_decision(AGENT_NAME, "invoice_approved", order_id=order_id,
                     reason="Approved via OneDrive Excel / Power Automate",
                     input_summary=f"notes={notes} amounts_changed={amounts_changed} total_changed={total_changed}",
                     output_summary="status → invoice_approved")
        log.info("dispatch: approved order=%s", order_id)

    elif action == "reject":
        save_order_state(order_id, status="invoice_rejected")
        log_decision(AGENT_NAME, "invoice_rejected", order_id=order_id,
                     reason=f"Rejected via OneDrive Excel: {notes}",
                     input_summary=f"notes={notes}", output_summary="status → invoice_rejected")
        log.info("dispatch: rejected order=%s notes=%s", order_id, notes)

    elif action == "hold":
        save_order_state(order_id, status="on_hold")
        log_decision(AGENT_NAME, "invoice_on_hold", order_id=order_id,
                     reason=f"Held via OneDrive Excel: {notes}",
                     input_summary=f"notes={notes}", output_summary="status → on_hold")
        log.info("dispatch: held order=%s", order_id)

    else:
        log.warning("dispatch: unknown action=%s for order=%s", action, order_id)
        return {"ok": False, "reason": f"unknown action: {action}"}

    try:
        from core.onedrive_excel_client import mark_row_processed
        mark_row_processed(order_id)
    except Exception as exc:
        log.warning("mark_row_processed failed order=%s: %s", order_id, exc)

    return {"ok": True, "order_id": order_id, "action": action}


def run() -> dict:
    """No-op — approval processing now happens via process_dispatch_input() only."""
    log.info("a4_human_gate: Teams-based polling retired; using workflow_dispatch path")
    return {"skipped": True, "reason": "Teams retired; use process_dispatch_input() via workflow_dispatch"}


def main(argv=None) -> None:
    if os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch" and os.getenv("INPUT_ORDER_ID"):
        result = process_dispatch_input()
        print(result)
        return

    import argparse
    parser = argparse.ArgumentParser(description="A4 Human Gate v2 — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--order-id", help="Process a specific order via dispatch inputs")
    args = parser.parse_args(argv)

    if args.order_id:
        os.environ.setdefault("INPUT_ORDER_ID", args.order_id)
        print(process_dispatch_input())
    elif args.run_now:
        print(run())


if __name__ == "__main__":
    main()
