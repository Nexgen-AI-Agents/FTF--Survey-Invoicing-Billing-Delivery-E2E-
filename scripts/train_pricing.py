#!/usr/bin/env python3
"""
Pricing Trainer CLI — FTF Agentic AI (I-067)
Robert describes a job and the AI stores the pricing rationale permanently.

Usage:
  python scripts/train_pricing.py                  # interactive mode
  python scripts/train_pricing.py --list           # show recent examples
  python scripts/train_pricing.py --json '{"entered_by":"Robert","job_description":"...","final_price":700}'

Role governance (I-069):
  Only 'robert' may enter pricing/logistics domain entries.
  Only 'jessica' may enter ar/refund domain entries.
  Cross-domain attempts are blocked and Prateek is notified.

Examples:
  python scripts/train_pricing.py
  > Who is entering this? (robert/jessica/ryan/prateek): robert
  > Describe the job: Half-acre residential in Palm Beach, pool + 2 sheds, 30 corners
  > Service type (or Enter to skip): Boundary Survey
  > County (or Enter to skip): Palm Beach
  > Lot size in acres (or Enter to skip): 0.5
  > What complexity factors apply? pool, 2 sheds, 30 wall corners, irregular lot
  > What was the final price charged? $: 700
  > Why was it priced at $700? Pool adds $150, sheds $100 each, 30 corners vs 4 = extra $150 fieldwork

  Saved! Example #42 stored. AI will reference this for future Palm Beach Boundary Surveys.
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "sprint_09_memory_loop", "agents"))

from dotenv import load_dotenv
load_dotenv()

from agent_13_pricing_trainer import submit_pricing_example, get_training_summary
from core.governance import GovernanceError, get_role_domains

_DIVIDER = "=" * 60


def _prompt(label: str, required: bool = False) -> str:
    while True:
        val = input(f"  {label}: ").strip()
        if val or not required:
            return val
        print("  (required — please enter a value)")


def _prompt_float(label: str, required: bool = False) -> float | None:
    while True:
        raw = input(f"  {label} $: ").strip().replace("$", "").replace(",", "")
        if not raw and not required:
            return None
        try:
            val = float(raw)
            if val > 0:
                return val
            print("  (must be a positive number)")
        except ValueError:
            print("  (please enter a number, e.g. 700 or 350.50)")


def interactive_mode():
    print()
    print(_DIVIDER)
    print("  FTF Pricing Trainer — AI Learning Interface")
    print("  Describe a job you billed. AI will remember it.")
    print(_DIVIDER)
    print()

    entered_by = ""
    while entered_by.lower() not in ("robert", "jessica", "ryan", "prateek"):
        entered_by = input("  Who is entering this? (robert / jessica / ryan / prateek): ").strip()
        if entered_by.lower() not in ("robert", "jessica", "ryan", "prateek"):
            print("  (enter a valid role name)")

    domains = get_role_domains(entered_by)
    print(f"  Role: {entered_by} | Permitted domains: {', '.join(sorted(domains))}")
    print()

    domain = _prompt("Domain (pricing / logistics / ar / refund) [default: pricing]") or "pricing"

    print()
    print("  Job Details")
    print("  " + "-" * 40)
    job_description = _prompt("Describe the job", required=True)
    service_type    = _prompt("Service type (or Enter to skip)")
    county          = _prompt("County (or Enter to skip)")

    lot_raw = input("  Lot size in acres (or Enter to skip): ").strip()
    lot_size_acres = float(lot_raw) if lot_raw else None

    complexity_notes = _prompt("Complexity factors (pool, sheds, corners, etc.)")

    print()
    final_price = _prompt_float("Final price charged", required=True)
    pricing_rationale = _prompt("Why was it priced at this amount?")

    print()
    print("  " + "-" * 40)
    print(f"  Service type  : {service_type or '—'}")
    print(f"  County        : {county or '—'}")
    print(f"  Lot size      : {lot_size_acres or '—'} acres")
    print(f"  Complexity    : {complexity_notes or '—'}")
    print(f"  Final price   : ${final_price:,.2f}")
    print(f"  Rationale     : {pricing_rationale or '—'}")
    print()

    confirm = input("  Save this example? (yes/no): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("  Cancelled — nothing saved.")
        return

    example = {
        "entered_by": entered_by,
        "domain": domain,
        "job_description": job_description,
        "service_type": service_type or None,
        "county": county or None,
        "lot_size_acres": lot_size_acres,
        "complexity_notes": complexity_notes or None,
        "final_price": final_price,
        "pricing_rationale": pricing_rationale or None,
    }

    try:
        result = submit_pricing_example(example)
        print()
        print(f"  Saved! Example #{result['id']} stored.")
        print(f"  AI will reference this for future {result.get('service_type') or 'similar'} "
              f"jobs{' in ' + result['county'] if result.get('county') else ''}.")
    except GovernanceError as exc:
        print()
        print(f"  BLOCKED: {exc}")
        print(f"  Cross-domain change request sent to Prateek for review.")
    print()


def list_mode(limit: int = 15):
    examples = get_training_summary(limit=limit)
    print()
    print(_DIVIDER)
    print(f"  Recent Pricing Examples ({len(examples)} shown)")
    print(_DIVIDER)
    if not examples:
        print("  No examples stored yet.")
    for ex in examples:
        print(
            f"  [{ex['id']:>4}] {(ex.get('service_type') or '—'):<28} "
            f"{(ex.get('county') or '—'):<16} "
            f"${float(ex['final_price']):>8,.2f}  by={ex['entered_by']}"
        )
        if ex.get("complexity_notes"):
            print(f"         Complexity: {ex['complexity_notes']}")
        if ex.get("pricing_rationale"):
            print(f"         Rationale : {ex['pricing_rationale'][:120]}")
        print()


def json_mode(raw_json: str):
    try:
        example = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON — {exc}")
        sys.exit(1)

    try:
        result = submit_pricing_example(example)
        print(json.dumps(result, indent=2))
    except GovernanceError as exc:
        print(f"GOVERNANCE_ERROR: {exc}")
        sys.exit(2)
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="FTF Pricing Trainer CLI")
    parser.add_argument("--list",  action="store_true", help="Show recent pricing examples")
    parser.add_argument("--json",  type=str, metavar="JSON", help="Submit example as JSON string (non-interactive)")
    parser.add_argument("--limit", type=int, default=15, help="Number of examples to show with --list")
    args = parser.parse_args()

    if args.list:
        list_mode(args.limit)
    elif args.json:
        json_mode(args.json)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
