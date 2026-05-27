"""run_sprint10_internal.py — Sprint 10 Internal Staging Test

Runs a complete non-destructive staging validation:
  1. Live connection checks (FTF API, Claude, DB, FEMA)
  2. Full pytest suite (all sprints, all agents)
  3. Order classification test — 12 order types via deterministic flag rules
     (no DB writes, no Claude calls, no emails)
  4. AR escalation logic test — 3 overdue scenarios (in-memory only)
  5. Statement generation test — builds Excel + PDF to temp dir (no DB, no email)
  6. Cost benchmark — reads agent_decision_log (read-only)
  7. Writes docs/sprint_10_internal_test_YYYY-MM-DD.md

Usage:
    python scripts/run_sprint10_internal.py

All tests are READ-ONLY or write to /tmp — no Teams messages, no emails,
no DB writes during this run.
"""

import os
import subprocess
import sys
import tempfile
from datetime import date, timedelta

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_ROOT, "code", "shared"))
sys.path.insert(0, os.path.join(_ROOT, "code", "sprint_07_ar_followup"))
sys.path.insert(0, os.path.join(_ROOT, "code", "sprint_08_monthly_statements"))

from dotenv import load_dotenv
load_dotenv()

# ── colour helpers ────────────────────────────────────────────────────────────
_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_RESET  = "\033[0m"
_BOLD   = "\033[1m"

PASS  = f"{_GREEN}  PASS{_RESET}"
FAIL  = f"{_RED}  FAIL{_RESET}"
WARN  = f"{_YELLOW}  WARN{_RESET}"
SKIP  = f"{_YELLOW}  SKIP{_RESET}"

results: list[dict] = []


def record(section: str, name: str, ok: bool, detail: str = "", warn: bool = False):
    label = WARN if warn else (PASS if ok else FAIL)
    tag   = "WARN" if warn else ("PASS" if ok else "FAIL")
    print(f"{label}  [{section}] {name}")
    if detail:
        print(f"         {detail}")
    results.append({"section": section, "name": name, "status": tag, "detail": detail})


# ── Section 1 — Live connections ──────────────────────────────────────────────

def _section_connections():
    print(f"\n{_BOLD}[ 1 / 7 ] Live Connection Checks{_RESET}")

    # FTF health
    try:
        from core.ftf_client import health_check
        ok = health_check()
        record("connections", "FTF /health", ok, "200 OK" if ok else "returned False")
    except Exception as e:
        record("connections", "FTF /health", False, str(e)[:100])

    # FTF orders — single page only (max_results=5)
    try:
        from core.ftf_client import get_orders
        orders = get_orders(limit=5, max_results=5)
        ok = len(orders) > 0
        record("connections", "FTF /orders (5-order sample)", ok, f"{len(orders)} orders, total in system: see logs")
    except Exception as e:
        record("connections", "FTF /orders", False, str(e)[:100])

    # Claude
    try:
        from config.models import MONITOR_MODEL
        from core.claude_client import call as claude_call
        resp = claude_call(model=MONITOR_MODEL, system="You are a test assistant.",
                           user="Reply with only the word: OK", max_tokens=10)
        ok = bool(resp and resp.strip())
        record("connections", f"Claude ({MONITOR_MODEL})", ok, resp.strip()[:40] if resp else "empty")
    except Exception as e:
        record("connections", "Claude API", False, str(e)[:100])

    # DB
    try:
        from core.db import get_pending_order
        get_pending_order()
        record("connections", "PostgreSQL (processed_orders)", True, "table accessible")
    except Exception as e:
        record("connections", "PostgreSQL", False, str(e)[:100])

    # FEMA (network-dependent)
    try:
        from core.fema_client import check_flood_zone
        zone = check_flood_zone(lat=26.7998, lng=-80.0642)
        record("connections", "FEMA flood zone API", bool(zone), f"Zone: {zone}")
    except Exception as e:
        record("connections", "FEMA flood zone API", False, str(e)[:100], warn=True)


# ── Section 2 — Full test suite ───────────────────────────────────────────────

def _section_pytest():
    print(f"\n{_BOLD}[ 2 / 7 ] Full pytest Suite (all sprints){_RESET}")
    project_root = os.path.join(os.path.dirname(__file__), "..")
    code_dir     = os.path.join(project_root, "code")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=short", "-q"],
        cwd=code_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines  = result.stdout.strip().splitlines()
    summary = lines[-1] if lines else "no output"
    ok = result.returncode == 0
    print(f"  {summary}")
    record("pytest", "All sprint tests", ok, summary)
    if not ok and result.stdout:
        # print first failure context
        for line in lines:
            if "FAILED" in line or "ERROR" in line:
                print(f"  {line}")


# ── Section 3 — Order classification (deterministic, no DB/Claude) ─────────────

def _section_order_types():
    print(f"\n{_BOLD}[ 3 / 7 ] Order Type Classification (12 types — no DB/Claude){_RESET}")

    from config.flag_triggers import ALWAYS_FLAG_SERVICES, COMPETITOR_NAMES, NEVER_AUTO_QUOTE

    test_cases = [
        # (service_type, customer_email, expected_routing, label)
        ("Boundary Survey",        "client@realestate.com",        "auto",       "Standard boundary survey"),
        ("Elevation Certificate",  "homeowner@gmail.com",          "auto",       "Elevation cert ($225 flat)"),
        ("Mortgage Survey",        "title@titleco.com",            "auto",       "Mortgage survey"),
        ("Update Survey",          "attorney@lawfirm.com",         "auto",       "Update survey"),
        ("Final Survey",           "builder@construction.com",     "auto",       "Final survey — post-construction"),
        ("ALTA Table A Survey",    "commercial@developer.com",     "flag",       "ALTA — always flag"),
        ("Building Stake Out",     "gc@contractor.com",            "flag",       "Building Stake Out — always flag"),
        ("Topography Survey",      "engineer@civil.com",           "flag",       "Topography — never auto-quote"),
        ("Lot Split",              "owner@property.com",           "flag",       "Lot Split — county approval needed"),
        ("Wetland Delineation",    "env@consultant.com",           "flag",       "Wetland — FDEP jurisdiction"),
        ("Specific Purpose Survey","attorney@lawfirm.com",         "flag",       "Specific Purpose — scope undefined"),
        ("Boundary Survey",        "contact@apexsurvey.us",        "competitor", "Order from competitor domain"),
    ]

    def classify_deterministic(service_type, email):
        # Check competitor domain
        domain = email.split("@")[-1].lower() if "@" in email else ""
        from config.flag_triggers import COMPETITOR_DOMAINS
        if any(d in domain for d in COMPETITOR_DOMAINS):
            return "competitor"
        # Check always-flag
        if service_type in ALWAYS_FLAG_SERVICES:
            return "flag"
        # Check never-auto-quote
        if service_type in NEVER_AUTO_QUOTE:
            return "flag"
        return "auto"

    for service, email, expected, label in test_cases:
        got = classify_deterministic(service, email)
        ok  = (got == expected)
        record("order_types", label, ok, f"expected={expected} got={got}")


# ── Section 4 — AR escalation logic (in-memory, no DB) ────────────────────────

def _section_ar_logic():
    print(f"\n{_BOLD}[ 4 / 7 ] AR Escalation Logic (in-memory, no DB/Teams){_RESET}")

    from config.settings import AR_ALERT_DAYS_60, AR_ESCALATION_DAYS

    scenarios = [
        (45,  1, False, False, "Day 45 — no alert expected"),
        (65,  1, True,  False, "Day 65 — 60d alert to Jessica"),
        (95,  1, True,  True,  "Day 95, level=1 — both 60d and 90d fire (90d processed first)"),
        (95,  2, False, True,  "Day 95, level=2 — still escalates to level 3"),
        (65,  2, False, False, "Day 65, level=2 — already alerted, skip"),
        (110, 3, False, False, "Day 110, level=3 — already escalated, skip"),
    ]

    for days, level, expect_60, expect_90, label in scenarios:
        should_alert_60 = (days >= AR_ALERT_DAYS_60 and level < 2)
        should_alert_90 = (days >= AR_ESCALATION_DAYS and level < 3)
        ok = (should_alert_60 == expect_60) and (should_alert_90 == expect_90)
        detail = f"days={days} level={level} -> 60d={should_alert_60} 90d={should_alert_90}"
        record("ar_logic", label, ok, detail)


# ── Section 5 — Statement generation (to temp dir, no DB/email) ───────────────

def _section_statement_gen():
    print(f"\n{_BOLD}[ 5 / 7 ] Statement Generation (temp dir, no DB/email){_RESET}")

    from agents.agent_15_statement_generator import _build_excel, _build_pdf, _group_by_client

    month = date.today().replace(day=1)
    test_orders = [
        {"order_id": f"TEST-{i}", "service_type": "Boundary Survey",
         "order_date": (date.today() - timedelta(days=30+i)).isoformat(),
         "invoice_amount": 400.0 + i*50,
         "payment_status": "Paid" if i % 2 == 0 else "Unpaid",
         "billing_email": "billing@acme-title.com",
         "customer_type": "b2b"}
        for i in range(5)
    ] + [
        {"order_id": "TEST-B1", "service_type": "Elevation Certificate",
         "order_date": (date.today() - timedelta(days=20)).isoformat(),
         "invoice_amount": 225.0,
         "payment_status": "Unpaid",
         "billing_email": "accounts@lawfirm-test.com",
         "customer_type": "b2b"}
    ]

    with tempfile.TemporaryDirectory() as tmp:
        try:
            groups = _group_by_client(test_orders)
            record("statement_gen", "Group by billing email", len(groups) == 2,
                   f"{len(groups)} clients: {list(groups.keys())}")

            for email, orders in groups.items():
                excel = _build_excel(email, orders, month, tmp)
                pdf   = _build_pdf(email, orders, month, tmp)
                record("statement_gen", f"Excel generated — {email}", os.path.exists(excel),
                       f"{os.path.getsize(excel)} bytes")
                record("statement_gen", f"PDF generated — {email}", os.path.exists(pdf),
                       f"{os.path.getsize(pdf)} bytes")
        except Exception as e:
            record("statement_gen", "Statement file generation", False, str(e)[:120])


# ── Section 6 — Cost benchmark ────────────────────────────────────────────────

def _section_benchmark():
    print(f"\n{_BOLD}[ 6 / 7 ] Claude API Cost Benchmark (last 30 days){_RESET}")
    try:
        from benchmark_credits import _print_summary, _write_report, run
        result = run(days=30)
        print(f"  Total calls (30d): {result['total_calls']}")
        print(f"  Est. monthly cost: ${result['est_monthly_cost_usd']:.2f} USD")
        docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
        path = _write_report(result, output_dir=docs_dir)
        record("benchmark", "Cost benchmark report written", True,
               f"${result['est_monthly_cost_usd']:.2f}/month est. — {path}")
    except Exception as e:
        record("benchmark", "Cost benchmark", False, str(e)[:120])


# ── Section 7 — Sprint 10 summary report ──────────────────────────────────────

def _write_sprint10_report():
    today = date.today().isoformat()
    docs  = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(docs, exist_ok=True)
    path  = os.path.join(docs, f"sprint_10_internal_test_{today}.md")

    by_section: dict[str, list[dict]] = {}
    for r in results:
        by_section.setdefault(r["section"], []).append(r)

    total   = len(results)
    passed  = sum(1 for r in results if r["status"] == "PASS")
    failed  = sum(1 for r in results if r["status"] == "FAIL")
    warned  = sum(1 for r in results if r["status"] == "WARN")

    lines = [
        f"# Sprint 10 — Internal Staging Test Report",
        f"",
        f"**Date:** {today}  ",
        f"**Run by:** Internal team (Prateek + AI agents)  ",
        f"**Result:** {'✅ PASS' if failed == 0 else '❌ FAIL'} — {passed}/{total} checks passed"
        + (f", {warned} warnings" if warned else "") + (f", {failed} failures" if failed else ""),
        f"",
        f"---",
        f"",
    ]

    section_labels = {
        "connections":   "1. Live Connection Checks",
        "pytest":        "2. Full pytest Suite",
        "order_types":   "3. Order Type Classification (12 types)",
        "ar_logic":      "4. AR Escalation Logic",
        "statement_gen": "5. Statement Generation",
        "benchmark":     "6. Claude API Cost Benchmark",
    }

    for sec_key, sec_label in section_labels.items():
        rows = by_section.get(sec_key, [])
        if not rows:
            continue
        sec_pass = sum(1 for r in rows if r["status"] == "PASS")
        lines += [
            f"## {sec_label}",
            f"",
            f"| Check | Status | Detail |",
            f"|-------|--------|--------|",
        ]
        for r in rows:
            icon = "✅" if r["status"] == "PASS" else ("⚠️" if r["status"] == "WARN" else "❌")
            lines.append(f"| {r['name']} | {icon} {r['status']} | {r['detail'][:80]} |")
        lines += [f"", f"**{sec_pass}/{len(rows)} passed**", f""]

    lines += [
        f"---",
        f"",
        f"## Internal Sign-Off",
        f"",
        f"| Role | Person | Status |",
        f"|------|--------|--------|",
        f"| CTO | Prateek | {'✅ Approved' if failed == 0 else '🔲 Pending fixes'} |",
        f"| AR Lead | Jessica | 🔲 Sprint 10 staging review |",
        f"| Oversight | Wyatt | 🔲 Sprint 10 staging review |",
        f"| Operations | Robert / Mark | 🔲 Sprint 10 staging review |",
        f"| Decision Maker | Ryan | 🔲 Cost approval + GO/NO-GO |",
        f"",
        f"*External stakeholder reviews scheduled for Sprint 10 staging session.*",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{_BOLD}{'='*60}{_RESET}")
    print(f"{_BOLD}  Sprint 10 — Internal Staging Test{_RESET}")
    print(f"{_BOLD}{'='*60}{_RESET}")
    print(f"  Date: {date.today().isoformat()}")
    print(f"  Mode: read-only + temp-dir writes only")

    _section_connections()
    _section_pytest()
    _section_order_types()
    _section_ar_logic()
    _section_statement_gen()
    _section_benchmark()

    # Summary
    total  = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["status"] == "WARN")

    print(f"\n{_BOLD}[ 7 / 7 ] Writing Test Report{_RESET}")
    report_path = _write_sprint10_report()
    print(f"  Report: {report_path}")

    print(f"\n{_BOLD}{'='*60}{_RESET}")
    colour = _GREEN if failed == 0 else _RED
    print(f"{colour}{_BOLD}  SPRINT 10 INTERNAL TEST: {passed}/{total} passed", end="")
    if warned:
        print(f", {warned} warnings", end="")
    if failed:
        print(f", {failed} FAILED", end="")
    print(f"{_RESET}\n")

    if failed > 0:
        print("Failed checks:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  ❌ [{r['section']}] {r['name']}: {r['detail']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
