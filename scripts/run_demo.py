"""
FTF Agentic AI OS — Demo Script (Sprints 0–6)
Pre-recorded demo for Ryan, Robert, Mark, Wyatt.

3 Scenarios:
  1. Standard auto-quote   — clean FL order, full pipeline, estimate sent
  2. Flagged order          — ALTA + Monroe County, Human Gate, Teams alert, Robert approves
  3. Reviewer self-correct  — AI catches its own price error, fixes on attempt 2

Usage:
  python scripts/run_demo.py
  python scripts/run_demo.py --scenario 2   (run one scenario only)

Recording instructions:
  1. Open Windows Terminal (dark theme, font size 14, width >= 120 cols)
  2. Run:  set PYTHONUTF8=1 && python scripts/run_demo.py
  3. Record with OBS or Windows Game Bar (Win + G -> Start recording)
  4. Individual scenarios:  python scripts/run_demo.py --scenario 1|2|3

Timing: ~2 minutes full run. Delays are tunable via the constants at the top.
"""

import argparse
import io
import sys
import time

# Force UTF-8 output on Windows so emojis and Unicode render correctly in any terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console(width=110)

# ── Timing constants (seconds) — increase for slower narration pace ───────────
SPLASH_HOLD   = 2.0
SCAN_DELAY    = 1.0
STEP_DELAY    = 0.5
WRITE_DELAY   = 1.5
SCENE_HOLD    = 2.0


def _pause(t: float) -> None:
    time.sleep(t)


def _agent_header(num: int, name: str, role: str, color: str = "cyan") -> None:
    console.print()
    console.print(Rule(
        f"[{color} bold]Agent {num} — {name}[/{color} bold]  [dim]{role}[/dim]",
        style=color,
    ))
    _pause(0.3)


def _step(icon: str, msg: str, color: str = "white") -> None:
    console.print(f"  {icon}  [{color}]{msg}[/{color}]")
    _pause(0.25)


def _status(label: str) -> None:
    colors = {
        "pending":            ("yellow",       "black"),
        "classified":         ("green",        "black"),
        "priced":             ("green",        "black"),
        "flagged":            ("red",          "white"),
        "awaiting_approval":  ("dark_orange",  "white"),
        "approved":           ("green",        "black"),
        "written":            ("cyan",         "black"),
        "reviewed":           ("green",        "black"),
        "sent":               ("bright_green", "black"),
    }
    fg, bg = colors.get(label, ("white", "black"))
    t = Text(f" {label.upper()} ", style=f"bold {fg} on {bg}")
    console.print("  Status -> ", end="")
    console.print(t)
    _pause(0.2)


def _db_row(order_id: str, status: str, extras: dict | None = None) -> None:
    tbl = Table(show_header=True, header_style="dim", box=None, padding=(0, 2))
    tbl.add_column("order_id", style="dim")
    tbl.add_column("status",   style="bold")
    for k in (extras or {}):
        tbl.add_column(k, style="dim")
    row = [order_id, status, *list((extras or {}).values())]
    tbl.add_row(*row, style="green")
    console.print(tbl)
    _pause(0.2)


def _order_panel(order_id: str, fields: dict) -> None:
    tbl = Table(show_header=False, box=None, padding=(0, 1))
    tbl.add_column("field", style="dim")
    tbl.add_column("value", style="bold")
    for k, v in fields.items():
        tbl.add_row(k.replace("_", " ").title(), str(v))
    console.print(Panel(tbl, title=f"[dim]FTF Order — {order_id}[/dim]", border_style="dim"))
    _pause(0.3)


# ═══════════════════════════════════════════════════════════════════════════════
#  SPLASH
# ═══════════════════════════════════════════════════════════════════════════════

def splash() -> None:
    console.clear()
    console.print()
    console.print(Panel.fit(
        Align.center(
            "[bold bright_white]FTF Agentic AI Operating System[/bold bright_white]\n"
            "[dim]Automated Estimate Generation Pipeline · Sprints 0 – 6[/dim]\n\n"
            "[cyan]9 Agents  ·  151 Unit Tests  ·  0 Failures[/cyan]\n"
            "[dim]NexGen Land Surveying · Florida[/dim]"
        ),
        border_style="bright_blue",
        padding=(1, 6),
    ))
    _pause(SPLASH_HOLD)

    console.print()
    console.print("[bold]What this system does — every 60 minutes, automatically:[/bold]")
    items = [
        ("1", "Scans FTF CRM for new Quote-stage orders"),
        ("2", "Classifies each order — service type, flood zone, 9 flag triggers"),
        ("3", "Prices the estimate via FTF Pricing API"),
        ("4", "Routes flagged orders to Robert / Mark for approval in MS Teams"),
        ("5", "Writes a personalized estimate email via Claude AI"),
        ("6", "Reviews the email — 4 accuracy checks, self-corrects if needed"),
        ("7", "Sends the estimate with a human-like 6 – 13 min delay"),
        ("8", "Posts a daily summary to MS Teams"),
    ]
    for num, text in items:
        console.print(f"  [cyan]{num}.[/cyan] {text}")
        _pause(0.25)

    _pause(0.8)
    console.print()
    console.print("[bold]Today's demo — 3 real scenarios:[/bold]")
    console.print("  [green]Scenario 1[/green] — Standard order: Boundary Survey, auto-quoted end-to-end")
    console.print("  [yellow]Scenario 2[/yellow] — Flagged order: ALTA Survey + Monroe County -> Teams alert -> Robert approves")
    console.print("  [cyan]Scenario 3[/cyan]  — Reviewer self-correction: AI catches wrong price, fixes on attempt 2")
    _pause(SCENE_HOLD)


# ═══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 1 — STANDARD AUTO-QUOTE
# ═══════════════════════════════════════════════════════════════════════════════

def scenario_1() -> None:
    ORDER = "ORD-2026-1001"
    console.print()
    console.print(Rule("[bold green]SCENARIO 1 — Standard Auto-Quote[/bold green]", style="green"))
    console.print("[dim]  Boundary Survey · John Smith · Boca Raton FL · Broward County · Zone X[/dim]")
    _pause(1.0)

    # ── Agent 2: Monitor ──────────────────────────────────────────────────────
    _agent_header(2, "CRM Monitor", "Polls FTF API every 60 min for new Quote-stage orders", "bright_cyan")
    _pause(SCAN_DELAY)
    _step("🔍", "Connecting to FTF CRM  ->  stage.fieldtofinish.jobs")
    _pause(SCAN_DELAY)
    _step("📊", "GET /orders?status=Quote&limit=500  ->  275,705 total orders, [bold]12 new[/bold] since last poll")
    _pause(0.5)
    _step("✅", f"New order detected: [bold]{ORDER}[/bold]")
    _order_panel(ORDER, {
        "order_id":       ORDER,
        "customer_name":  "John Smith",
        "customer_email": "j.smith@gmail.com",
        "customer_type":  "individual",
        "service_type":   "Boundary Survey",
        "address":        "1234 Palm Avenue, Boca Raton FL 33432",
        "property_county":"Broward",
        "property_state": "FL",
        "flood_zone":     "X",
        "special_pricing":"False",
    })
    _step("💾", f"Saved to processed_orders")
    _status("pending")
    _db_row(ORDER, "pending")

    # ── Agent 3: Classifier ───────────────────────────────────────────────────
    _agent_header(3, "Classifier", "Service type · pricing tier · flood zone · 9 flag triggers", "bright_yellow")
    _pause(STEP_DELAY)
    _step("🔎", '"Boundary Survey" -> canonical FTF service name  ✓')
    _step("🔎", "customer_type = individual  ->  pricing_tier = individual  ✓")
    _step("🔎", "property_state = FL  ->  in-state  ✓")
    _step("🔎", "property_county = Broward  ->  no Monroe County flag  ✓")
    _step("🔎", "flood_zone = X  ->  no elevation certificate required  ✓")
    _step("🔎", "competitor check: gmail.com not in competitor domain list  ✓")
    _step("🔎", "ALWAYS_FLAG_SERVICES: Boundary Survey not listed  ✓")
    _step("🔎", "NEVER_AUTO_QUOTE: Boundary Survey not listed  ✓")
    console.print()
    console.print("  [bold green]No flags. All 9 triggers clear. Proceeding to pricing.[/bold green]")
    _status("classified")
    _db_row(ORDER, "classified", {"service_type": "Boundary Survey", "tier": "individual", "elev_cert": "No"})

    # ── Agent 5: Pricing Engine ───────────────────────────────────────────────
    _agent_header(5, "Pricing Engine", "FTF API pricing · override check · elevation cert add-on", "magenta")
    _pause(STEP_DELAY)
    _step("💲", "GET /pricing?service=Boundary+Survey&tier=individual  ->  $350.00")
    _step("💲", "special_pricing = False  ->  no override lookup needed")
    _step("💲", "elevation_cert_required = False  ->  $0 add-on")

    pt = Table(show_header=False, box=None, padding=(0, 2))
    pt.add_column("", style="dim");  pt.add_column("", style="bold")
    pt.add_row("Base amount",            "$350.00")
    pt.add_row("Elevation cert add-on",  "$0.00")
    pt.add_row("──────────────────────", "──────────")
    pt.add_row("TOTAL ESTIMATE",         "[bold green]$350.00[/bold green]")
    console.print(Panel(pt, title="[dim]Pricing Result[/dim]", border_style="dim"))
    _status("priced")
    _db_row(ORDER, "priced", {"estimate_amount": "$350.00"})

    # ── Agent 6: Writer ───────────────────────────────────────────────────────
    _agent_header(6, "Estimate Writer", "Claude AI · warm/friendly tone for individuals · change order clause appended", "bright_green")
    _pause(STEP_DELAY)
    _step("✍️ ", "Sending to Claude (claude-sonnet-4-6) — individual tone prompt...")
    _pause(WRITE_DELAY)

    email = (
        "[dim]Subject:[/dim] [bold]Your NexGen Land Surveying Estimate — Boundary Survey[/bold]\n\n"
        "Dear John,\n\n"
        "Thank you for reaching out to NexGen Land Surveying! We'd be delighted to\n"
        "assist you with a Boundary Survey at 1234 Palm Avenue, Boca Raton.\n\n"
        "  [bold]Service:[/bold]   Boundary Survey\n"
        "  [bold]Property:[/bold]  1234 Palm Avenue, Boca Raton FL 33432\n"
        "  [bold]Total:[/bold]     [green bold]$350.00[/green bold]\n\n"
        "Once you're ready to proceed, please reply to this email or use the payment\n"
        "link to secure your appointment. We look forward to serving you!\n\n"
        "Warm regards,\nNexGen Land Surveying  ·  (561) 508-6272\n\n"
        "[dim]──────────────────────────────────────────────────────────────────────\n"
        "CHANGE ORDER CLAUSE: Any changes to the agreed scope of work requested\n"
        "after this estimate is accepted may result in additional charges. NexGen\n"
        "Land Surveying will contact you for written approval before proceeding\n"
        "with any scope changes.\n"
        "──────────────────────────────────────────────────────────────────────[/dim]"
    )
    console.print(Panel(email, title="[dim]Draft Estimate Email — Attempt 1[/dim]", border_style="green"))
    _status("written")
    _db_row(ORDER, "written")

    # ── Agent 7: Reviewer ─────────────────────────────────────────────────────
    _agent_header(7, "Estimate Reviewer", "4 deterministic checks · self-correction up to 3 attempts", "yellow")
    _pause(STEP_DELAY)

    ct = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
    ct.add_column("Check");  ct.add_column("Expected", style="cyan")
    ct.add_column("Found in email", style="cyan");  ct.add_column("Result", justify="center")
    ct.add_row("Total price",          "$350.00", "$350.00",                              "[bold green]✓  PASS[/bold green]")
    ct.add_row("Customer name",        "John Smith", "John",                              "[bold green]✓  PASS[/bold green]")
    ct.add_row("Property address",     "1234 Palm Ave, Boca Raton FL", "1234 Palm Avenue, Boca Raton FL",  "[bold green]✓  PASS[/bold green]")
    ct.add_row("Change order clause",  "Required",  "Present",                            "[bold green]✓  PASS[/bold green]")
    console.print(Panel(ct, title="[dim]Reviewer — 4 Accuracy Checks[/dim]", border_style="yellow"))
    console.print("  [bold green]All 4 checks PASSED. No correction needed.[/bold green]")
    _status("reviewed")
    _db_row(ORDER, "reviewed")

    # ── Agent 8: Sender ───────────────────────────────────────────────────────
    _agent_header(8, "Sender", "8 AM–6 PM ET send window · 6–13 min human-like delay · 3 retry max", "bright_blue")
    _pause(STEP_DELAY)
    _step("🕑", "Send window check: 10:32 AM ET  ->  within window  ✓")
    _step("⏱ ", "Human-like delay applied: 9 minutes  [dim](skipped in demo)[/dim]")
    _pause(0.6)
    _step("📋", "POST /invoices  ->  FTF invoice created: INV-2026-1001")
    _step("📧", "Estimate email sent to j.smith@gmail.com  ✓")
    _status("sent")

    console.print()
    console.print(Panel(
        "[bold green]✓  Estimate delivered automatically — zero human touches needed.[/bold green]\n\n"
        f"  Order {ORDER}  ·  $350.00  ·  John Smith  ·  Broward County\n"
        "  Full audit trail written to agent_decision_log for every agent step.",
        border_style="green",
        title="[dim]Scenario 1 Complete[/dim]",
    ))
    _pause(SCENE_HOLD)


# ═══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 2 — FLAGGED ORDER + HUMAN GATE
# ═══════════════════════════════════════════════════════════════════════════════

def scenario_2() -> None:
    ORDER = "ORD-2026-1002"
    console.print()
    console.print(Rule("[bold yellow]SCENARIO 2 — Flagged Order + Human Gate[/bold yellow]", style="yellow"))
    console.print("[dim]  ALTA Table A Survey · Coastal Builders LLC (B2B) · Monroe County FL · Zone AE[/dim]")
    _pause(1.0)

    # ── Agent 2 ───────────────────────────────────────────────────────────────
    _agent_header(2, "CRM Monitor", "Polls FTF API every 60 min", "bright_cyan")
    _step("✅", f"New order: [bold]{ORDER}[/bold]")
    _order_panel(ORDER, {
        "order_id":       ORDER,
        "customer_name":  "Coastal Builders LLC",
        "customer_email": "projects@coastalbuilders.com",
        "customer_type":  "b2b",
        "service_type":   "ALTA Table A Survey",
        "address":        "77 Ocean Drive, Key West FL 33040",
        "property_county":"Monroe",
        "property_state": "FL",
        "flood_zone":     "AE",
        "special_pricing":"False",
    })
    _status("pending")
    _db_row(ORDER, "pending")

    # ── Agent 3 ───────────────────────────────────────────────────────────────
    _agent_header(3, "Classifier", "9 flag triggers evaluated", "bright_yellow")
    _pause(STEP_DELAY)
    _step("🔎", 'Service type: "ALTA Table A Survey"')
    _pause(0.2)
    _step("🚩", "[bold red]TRIGGER 1 — ALWAYS_FLAG_SERVICES: ALTA Table A Survey (complex, high-value, mandatory review)[/bold red]")
    _pause(0.4)
    _step("🚩", "[bold red]TRIGGER 10 — Monroe County (Florida Keys): non-standard pricing, limited crew availability[/bold red]")
    _pause(0.4)
    _step("🌊", "flood_zone = AE  ->  elevation_cert_required = True (+$225)")
    _pause(0.3)
    console.print()
    console.print("  [bold]2 flags accumulated:[/bold]")
    console.print("    [red]•[/red] ALTA Table A Survey — always requires human review")
    console.print("    [red]•[/red] Monroe County — non-standard pricing, human review required")
    console.print()
    console.print("  [bold yellow]Routing to Human Gate — pricing deferred until approval.[/bold yellow]")
    _status("flagged")
    _db_row(ORDER, "flagged", {"flag_reason": "ALWAYS_FLAG + Monroe County", "elev_cert": "Yes"})

    # ── Agent 4: Human Gate ───────────────────────────────────────────────────
    _agent_header(4, "Human Gate", "Teams notification · awaiting_approval · escalation after timeout", "red")
    _pause(STEP_DELAY)
    _step("📡", "Retrieving order details from DB...")
    _step("📋", "Building Teams MessageCard payload...")
    _step("🚀", "POST to TEAMS_WEBHOOK_URL  ->  HTTP 200 OK  ✓")
    _pause(0.5)

    teams_msg = (
        "[bold bright_white]FTF Estimate — Human Review Required[/bold bright_white]\n"
        "[dim]─────────────────────────────────────────────────[/dim]\n"
        "  [bold]Order ID           [/bold]  ORD-2026-1002\n"
        "  [bold]Service            [/bold]  ALTA Table A Survey\n"
        "  [bold]County             [/bold]  Monroe\n"
        "  [bold]State              [/bold]  FL\n"
        "  [bold]Flag Reason        [/bold]  ALWAYS_FLAG; Monroe County — non-standard pricing\n"
        "  [bold]Elevation Cert     [/bold]  Required (Zone AE)\n"
        "  [bold]Estimate Amount    [/bold]  TBD (priced after approval)\n"
        "  [bold]Flagged At         [/bold]  2026-05-26 10:47 UTC\n"
        "[dim]─────────────────────────────────────────────────[/dim]\n\n"
        '[italic dim]Reply "approve" or "reject" to process this order.[/italic dim]'
    )
    console.print(Panel(
        teams_msg,
        title="[dim]MS Teams — FTF Invoicing Channel[/dim]",
        border_style="red",
        padding=(0, 2),
    ))
    _status("awaiting_approval")
    _db_row(ORDER, "awaiting_approval")

    _pause(1.2)
    console.print()
    console.print("  [dim]Robert opens the FTF order in CRM, checks the property on GIS...[/dim]")
    _pause(WRITE_DELAY)
    console.print()
    console.print("  [dim bold]Robert (Teams):[/dim bold] [bold green]approve[/bold green]")
    _pause(0.8)
    _step("✅", "[green]process_approval_reply('ORD-2026-1002', 'approve')  ->  status = approved[/green]")
    _status("approved")
    _db_row(ORDER, "approved")

    _pause(0.6)
    console.print()
    console.print("  [dim]Pipeline resumes automatically after approval:[/dim]")
    console.print("  [dim]  Agent 5 -> $1,500 base + $225 elevation cert = $1,725 total[/dim]")
    console.print("  [dim]  Agent 6 -> B2B estimate (concise, professional tone)[/dim]")
    console.print("  [dim]  Agent 7 -> 4 checks PASSED[/dim]")
    console.print("  [dim]  Agent 8 -> sent to projects@coastalbuilders.com[/dim]")
    _pause(0.8)

    console.print()
    console.print(Panel(
        "[bold green]✓  Flagged order handled correctly.[/bold green]\n\n"
        f"  Order {ORDER}  ·  $1,725.00  ·  Coastal Builders LLC  ·  Monroe County\n"
        "  Robert approved in Teams · audit trail complete · no order bypassed review.",
        border_style="yellow",
        title="[dim]Scenario 2 Complete[/dim]",
    ))
    _pause(SCENE_HOLD)


# ═══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 3 — REVIEWER SELF-CORRECTION
# ═══════════════════════════════════════════════════════════════════════════════

def scenario_3() -> None:
    ORDER = "ORD-2026-1003"
    console.print()
    console.print(Rule("[bold cyan]SCENARIO 3 — Reviewer Self-Correction Loop[/bold cyan]", style="cyan"))
    console.print("[dim]  Elevation Certificate · Maria Santos · Miami Beach FL · Zone AE[/dim]")
    _pause(1.0)

    # ── Agents 2 + 3 + 5 (summarised) ────────────────────────────────────────
    _agent_header(2, "CRM Monitor", "New Quote order detected", "bright_cyan")
    _step("✅", f"New order: [bold]{ORDER}[/bold] — Maria Santos, Elevation Certificate, Miami Beach FL")
    _status("pending")
    _db_row(ORDER, "pending")

    _agent_header(3, "Classifier", "Flood zone check", "bright_yellow")
    _pause(STEP_DELAY)
    _step("🔎", 'Service type: "Elevation Certificate"  ->  canonical ✓')
    _step("🔎", "FL · Miami-Dade County · no competitor flags ✓")
    _step("🌊", "[cyan]flood_zone = AE  ->  FEMA flood zone confirmed  ->  elevation_cert_required = True[/cyan]")
    _status("classified")
    _db_row(ORDER, "classified", {"elev_cert_required": "True"})

    _agent_header(5, "Pricing Engine", "Base + elevation cert add-on", "magenta")
    _pause(STEP_DELAY)
    _step("💲", "GET /pricing?service=Elevation+Certificate&tier=individual  ->  $225.00 base")
    _step("💲", "[cyan]elevation_cert_required = True  ->  +$225.00 (FEMA add-on)[/cyan]")

    pt = Table(show_header=False, box=None, padding=(0, 2))
    pt.add_column("", style="dim");  pt.add_column("", style="bold")
    pt.add_row("Base amount",           "$225.00")
    pt.add_row("Elevation cert add-on", "[cyan]$225.00[/cyan]")
    pt.add_row("─────────────────────", "──────────")
    pt.add_row("TOTAL ESTIMATE",        "[bold green]$450.00[/bold green]")
    console.print(Panel(pt, title="[dim]Pricing Result[/dim]", border_style="dim"))
    _status("priced")
    _db_row(ORDER, "priced", {"estimate_amount": "$450.00"})

    # ── Agent 6: First draft (WRONG) ──────────────────────────────────────────
    _agent_header(6, "Estimate Writer", "Attempt 1 of 3", "bright_green")
    _pause(STEP_DELAY)
    _step("✍️ ", "Generating estimate email (claude-sonnet-4-6)...")
    _pause(WRITE_DELAY)

    bad_email = (
        "Dear Maria,\n\n"
        "Thank you for contacting NexGen Land Surveying. We're happy to assist with\n"
        "your Elevation Certificate at 456 Ocean Drive, Miami Beach.\n\n"
        "  [bold]Service:[/bold]   Elevation Certificate\n"
        "  [bold]Property:[/bold]  456 Ocean Drive, Miami Beach FL 33139\n"
        "  [bold]Total:[/bold]     [bold red]$350.00[/bold red]     "
        "[dim]←  AI wrote wrong price (base only, forgot add-on)[/dim]\n\n"
        "Please reply when you're ready to schedule.\n\n"
        "Warm regards,\nNexGen Land Surveying\n\n"
        "[dim]CHANGE ORDER CLAUSE: [...][/dim]"
    )
    console.print(Panel(bad_email, title="[dim]Draft Estimate — Attempt 1[/dim]", border_style="red"))

    # ── Agent 7: Fail ─────────────────────────────────────────────────────────
    _agent_header(7, "Estimate Reviewer", "Checking attempt 1", "yellow")
    _pause(STEP_DELAY)

    t1 = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
    t1.add_column("Check"); t1.add_column("Expected", style="cyan")
    t1.add_column("Found in email", style="cyan"); t1.add_column("Result", justify="center")
    t1.add_row("Total price",         "$450.00", "$350.00",                                   "[bold red]✗  FAIL[/bold red]")
    t1.add_row("Customer name",       "Maria Santos", "Maria",                                "[bold green]✓  PASS[/bold green]")
    t1.add_row("Property address",    "456 Ocean Drive, Miami Beach FL", "456 Ocean Drive, Miami Beach FL", "[bold green]✓  PASS[/bold green]")
    t1.add_row("Change order clause", "Required", "Present",                                  "[bold green]✓  PASS[/bold green]")
    console.print(Panel(t1, title="[dim]Reviewer — Attempt 1[/dim]", border_style="red"))
    console.print("  [bold red]✗  FAIL — Price mismatch. Sending correction note back to Writer...[/bold red]")
    _pause(0.4)
    console.print('  [dim]correction_note: "Total price in email ($350.00) does not match estimate total ($450.00). '
                  'Price must be $450.00 = $225 base + $225 elevation certificate add-on."[/dim]')
    _pause(1.2)

    # ── Agent 6: Second draft (CORRECT) ──────────────────────────────────────
    _agent_header(6, "Estimate Writer", "Attempt 2 of 3 — rewriting with correction note", "bright_green")
    _pause(STEP_DELAY)
    _step("✍️ ", 'Rewriting with correction note applied...')
    _pause(WRITE_DELAY)

    good_email = (
        "Dear Maria,\n\n"
        "Thank you for contacting NexGen Land Surveying! We're pleased to assist with\n"
        "your Elevation Certificate at 456 Ocean Drive, Miami Beach.\n\n"
        "As your property is located in a FEMA AE flood zone, your survey includes\n"
        "a full Elevation Certificate as required by your lender / municipality.\n\n"
        "  [bold]Service:[/bold]    Elevation Certificate (incl. FEMA AE zone cert)\n"
        "  [bold]Property:[/bold]   456 Ocean Drive, Miami Beach FL 33139\n"
        "  [bold]Flood Zone:[/bold] AE — elevation certificate required\n"
        "  [bold]Base:[/bold]       $225.00  |  [bold]Elev. Cert:[/bold] $225.00\n"
        "  [bold]TOTAL:[/bold]      [bold green]$450.00[/bold green]\n\n"
        "Please don't hesitate to reach out with any questions!\n\n"
        "Warm regards,\nNexGen Land Surveying  ·  (561) 508-6272\n\n"
        "[dim]CHANGE ORDER CLAUSE: [...][/dim]"
    )
    console.print(Panel(good_email, title="[dim]Draft Estimate — Attempt 2[/dim]", border_style="green"))

    # ── Agent 7: Pass ─────────────────────────────────────────────────────────
    _agent_header(7, "Estimate Reviewer", "Checking attempt 2", "yellow")
    _pause(STEP_DELAY)

    t2 = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
    t2.add_column("Check"); t2.add_column("Expected", style="cyan")
    t2.add_column("Found in email", style="cyan"); t2.add_column("Result", justify="center")
    t2.add_row("Total price",         "$450.00", "$450.00",                                   "[bold green]✓  PASS[/bold green]")
    t2.add_row("Customer name",       "Maria Santos", "Maria",                                "[bold green]✓  PASS[/bold green]")
    t2.add_row("Property address",    "456 Ocean Drive, Miami Beach FL", "456 Ocean Drive, Miami Beach FL", "[bold green]✓  PASS[/bold green]")
    t2.add_row("Change order clause", "Required", "Present",                                  "[bold green]✓  PASS[/bold green]")
    console.print(Panel(t2, title="[dim]Reviewer — Attempt 2[/dim]", border_style="green"))
    console.print("  [bold green]✓  All 4 checks PASSED on attempt 2. No further correction needed.[/bold green]")
    _status("reviewed")
    _db_row(ORDER, "reviewed")

    _agent_header(8, "Sender", "Sending reviewed estimate", "bright_blue")
    _pause(STEP_DELAY)
    _step("📧", "Estimate sent to m.santos@gmail.com  ✓  (9-min delay simulated)")
    _status("sent")

    console.print()
    console.print(Panel(
        "[bold green]✓  AI caught its own error and corrected it — no human intervention needed.[/bold green]\n\n"
        f"  Order {ORDER}  ·  $450.00  ·  Maria Santos  ·  Miami Beach\n"
        "  Error detected on check 1/4  ·  Corrected on attempt 2 of 3  ·  Sent successfully.",
        border_style="cyan",
        title="[dim]Scenario 3 Complete[/dim]",
    ))
    _pause(SCENE_HOLD)


# ═══════════════════════════════════════════════════════════════════════════════
#  AGENT 9 — DAILY REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def daily_report() -> None:
    console.print()
    console.print(Rule("[bold bright_blue]Agent 9 — Daily Report posted to MS Teams[/bold bright_blue]", style="bright_blue"))
    _pause(STEP_DELAY)
    _step("📊", "Querying processed_orders for today's stats...")
    _pause(SCAN_DELAY)

    report = (
        "[bold bright_white]FTF AI — Daily Estimate Report[/bold bright_white]\n"
        "[dim]NexGen Land Surveying  ·  2026-05-26[/dim]\n\n"
        "[dim]─────────────────────────────────────────[/dim]\n"
        "  [bold]Estimates Sent Today      [/bold]  [green bold]8[/green bold]\n"
        "  [bold]Flagged (Needs Review)    [/bold]  [yellow bold]2[/yellow bold]\n"
        "  [bold]Awaiting Human Approval   [/bold]  [yellow bold]1[/yellow bold]\n"
        "  [bold]Ready to Send             [/bold]  [cyan bold]3[/cyan bold]\n"
        "  [bold]Active Pipeline (total)   [/bold]  [white bold]14[/white bold]\n"
        "[dim]─────────────────────────────────────────[/dim]"
    )
    console.print(Panel(
        report,
        title="[dim]MS Teams — FTF Invoicing Channel[/dim]",
        border_style="bright_blue",
        padding=(0, 2),
    ))
    _pause(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
#  FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

def footer() -> None:
    console.print()
    console.print(Rule(style="dim"))
    console.print()
    console.print(Panel(
        "[bold bright_white]Sprint 0–6 Complete[/bold bright_white]\n\n"
        "  [cyan]9 agents[/cyan] built and tested  "
        " ·  [cyan]151 unit tests[/cyan], 0 failures  "
        " ·  [cyan]6 sprints[/cyan] delivered\n\n"
        "  [green]Estimate generation loop is functionally complete[/green]\n"
        "  [dim](staging validation and production go-live in Sprints 10 – 11)[/dim]\n\n"
        "[bold]What's next:[/bold]\n"
        "  [yellow]Sprint 7[/yellow]  — AR Follow-Up Loop     [dim](needs: Jessica recording)[/dim]\n"
        "  [yellow]Sprint 8[/yellow]  — Monthly Statements    [dim](needs: Wyatt recording)[/dim]\n"
        "  [cyan]Sprint 9[/cyan]  — Orchestrator (24/7 autonomous, every 60 min)\n"
        "  [cyan]Sprint 10[/cyan] — Staging test with live FTF data\n"
        "  [green]Sprint 11[/green] — Limited production go-live",
        title="[dim]FTF Agentic AI OS — Demo Summary[/dim]",
        border_style="bright_blue",
        padding=(1, 2),
    ))
    console.print()


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="FTF Agentic AI OS — Demo Script")
    parser.add_argument(
        "--scenario", type=int, choices=[1, 2, 3],
        help="Run a single scenario (1=auto-quote, 2=flagged, 3=self-correction)",
    )
    parser.add_argument(
        "--save-html", metavar="OUTPUT_PATH",
        help="Export demo as a styled HTML file (no delays, for sharing/recording)",
    )
    args = parser.parse_args()

    if args.save_html:
        _run_html_export(args.save_html)
        return

    if args.scenario == 1:
        scenario_1()
    elif args.scenario == 2:
        scenario_2()
    elif args.scenario == 3:
        scenario_3()
    else:
        splash()
        scenario_1()
        scenario_2()
        scenario_3()
        daily_report()
        footer()


def _run_html_export(output_path: str) -> None:
    """Re-run the full demo with zero delays into a recording console, export as HTML."""
    global console, SPLASH_HOLD, SCAN_DELAY, STEP_DELAY, WRITE_DELAY, SCENE_HOLD

    # Zero out all delays for the export run
    SPLASH_HOLD = SCAN_DELAY = STEP_DELAY = WRITE_DELAY = SCENE_HOLD = 0.0

    # Replace the global console with a recording one (force_terminal=True renders markup)
    console = Console(
        width=110,
        record=True,
        force_terminal=True,
        highlight=False,
    )

    splash()
    scenario_1()
    scenario_2()
    scenario_3()
    daily_report()
    footer()

    console.save_html(output_path, theme=None, clear=False)
    # Print confirmation to the real stdout
    import builtins
    builtins.print(f"Demo HTML saved to: {output_path}")


if __name__ == "__main__":
    main()
