"""
generate_demo_audio.py — Generate OpenAI TTS audio for live interactive demo.

Produces docs/demo_audio/scene_XX.mp3 for each scene.
Uses OpenAI tts-1-hd (nova voice) — noticeably better quality than edge-tts.

Usage:
    set PYTHONUTF8=1 && python scripts/generate_demo_audio.py

Output: docs/demo_audio/scene_00.mp3 ... scene_22.mp3
"""

import asyncio
import os
import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code" / "shared"))

from dotenv import load_dotenv
load_dotenv()

from core.openai_client import atts_to_file

OUTPUT_DIR = Path("docs") / "demo_audio"

SCENES = [
    (0,  "intro",
     "Welcome to the NexGen FTF Agentic AI demo. "
     "Over the past 6 sprints, we've built a fully automated estimate generation pipeline for NexGen Land Surveying in Florida. "
     "This system detects new survey orders, classifies them, prices them, writes personalized estimate emails using Claude AI, "
     "reviews them for accuracy, and sends them — automatically, every 60 minutes, around the clock. "
     "Let's see it in action."),

    (1,  "pipeline_overview",
     "The pipeline has 8 agents working in sequence. "
     "Agent 2 scans the FTF CRM for new orders. Agent 3 classifies the service type and checks 9 flag triggers. "
     "Agent 4 handles orders that need human review from Robert. "
     "Agent 5 prices the estimate using the FTF API. Agent 6 writes the email using Claude AI. "
     "Agent 7 reviews it for accuracy and self-corrects if needed. "
     "Agent 8 sends the estimate between 8 AM and 6 PM Eastern time. "
     "And Agent 9 posts a daily summary to MS Teams."),

    (2,  "s1_intro",
     "Scenario 1: A standard Boundary Survey order from John Smith in Boca Raton, Florida. "
     "Individual client, Broward County, flood zone X. "
     "This is the most common order type — no flags expected. Watch the pipeline handle it automatically."),

    (3,  "s1_agent2",
     "Agent 2, the CRM Monitor, connects to the FTF staging API and polls for Quote-stage orders. "
     "Out of 275 thousand total orders, 12 new ones are detected since the last run. "
     "John's Boundary Survey is one of them. It's saved to the pipeline database with status: pending."),

    (4,  "s1_agent3",
     "Agent 3, the Classifier, runs 9 flag triggers against the order. "
     "Boundary Survey is a standard service — not on the always-flag list, not a competitor inquiry, not Monroe County. "
     "John is in Florida, in-state, individual tier. Flood zone X — no elevation certificate needed. "
     "All 9 triggers clear. Status updated to: classified."),

    (5,  "s1_agent5",
     "Agent 5, the Pricing Engine, queries the FTF API for the Boundary Survey price at the individual tier. "
     "That returns $350. "
     "No elevation certificate surcharge for Zone X. "
     "Total estimate: $350. Status updated to: priced."),

    (6,  "s1_agent6",
     "Agent 6, the Estimate Writer, sends the order details to Claude AI with a warm, friendly tone for individual clients. "
     "Claude generates a personalized estimate email in seconds. "
     "The service name, property address, and total price are all included. "
     "Critically, the change order clause is automatically appended — this is new legal language that NexGen didn't include in estimates before this system."),

    (7,  "s1_agent7",
     "Agent 7, the Estimate Reviewer, runs 4 deterministic accuracy checks. "
     "Is the total price $350? Check. Is John's name in the email? Check. Is the property address correct? Check. Is the change order clause included? Check. "
     "All 4 pass on the first attempt. No correction loop needed. Status: reviewed."),

    (8,  "s1_agent8",
     "Agent 8, the Sender, checks the send window — estimates only go out between 8 AM and 6 PM Eastern time. "
     "It's 10:32 AM, window is open. "
     "The FTF invoice is created via API. Then a human-like delay of 9 minutes is applied — the email won't appear robotic. "
     "Estimate sent to John Smith. Status: sent."),

    (9,  "s1_complete",
     "Scenario 1 complete. John's $350 Boundary Survey estimate was processed and sent with zero human involvement. "
     "Every step is logged to the audit database. "
     "Total compute time: under 2 minutes, plus the human-like send delay. "
     "Now let's see how the system handles an order that needs Robert's judgment."),

    (10, "s2_intro",
     "Scenario 2: Coastal Builders, a B2B client, has requested an ALTA Table A Survey in Monroe County — the Florida Keys. "
     "This order will trigger multiple flags. The Human Gate will activate, and Robert will need to approve before the estimate is sent."),

    (11, "s2_agent3",
     "The Classifier fires two flags immediately. "
     "First: ALTA Table A Survey is on the always-flag list — it's a complex, high-value survey that Robert requires human review for every time. "
     "Second: Monroe County triggers a separate flag — non-standard pricing and limited crew availability in the Keys. "
     "Additionally, the property is in FEMA flood zone AE, so an elevation certificate will be required. "
     "Order flagged. Pricing deferred until Robert approves."),

    (12, "s2_agent4_notify",
     "Agent 4, the Human Gate, sends a detailed notification card to Robert in MS Teams. "
     "The card shows the order ID, service type, Monroe County flag, both flag reasons, and that an elevation certificate will be needed. "
     "Robert can check the property in the FTF CRM and on GIS before making his decision. "
     "Status: awaiting approval."),

    (13, "s2_agent4_approve",
     "Robert reviews the order and types 'approve' in Teams. "
     "The system immediately picks up the reply. "
     "Agent 5 prices the ALTA at $1,500 plus the $225 elevation certificate add-on — total: $1,725. "
     "Agent 6 writes a B2B estimate in concise, professional tone. The Reviewer passes. The Sender delivers it."),

    (14, "s2_complete",
     "Scenario 2 complete. $1,725 estimate for Coastal Builders, Monroe County. "
     "Every order that needs Robert's judgment gets it — nothing bypasses him on flagged orders. "
     "Once he approves, the AI handles everything else. "
     "Now let's watch the AI catch and correct its own mistake."),

    (15, "s3_intro",
     "Scenario 3: Maria Santos needs an Elevation Certificate for a property in Miami Beach. "
     "FEMA flood zone AE — elevation certificate required, adds $225 to the estimate. "
     "Watch how the AI catches and corrects a pricing error without any human intervention."),

    (16, "s3_agent5",
     "The Classifier detects zone AE and sets elevation certificate required. "
     "The Pricing Engine adds the $225 surcharge to the $225 base price. "
     "Correct total: $450. Status: priced."),

    (17, "s3_agent6_bad",
     "The Writer generates the first draft — but makes an error. "
     "It writes $350 in the email body — only the base price. It forgot the elevation certificate add-on. "
     "This is exactly the kind of mistake that can happen with AI. "
     "But the Reviewer is about to catch it."),

    (18, "s3_agent7_fail",
     "The Reviewer immediately catches the price mismatch. "
     "The email says $350 but the estimate total is $450. "
     "That's a $100 error that would confuse Maria and require a manual correction. "
     "The Reviewer generates a specific correction note and sends it back to the Writer for attempt 2."),

    (19, "s3_agent6_fixed",
     "The Writer rewrites the email with the correction applied. "
     "This time it shows $450, with a clear breakdown of the $225 base fee and the $225 FEMA flood zone AE elevation certificate add-on. "
     "The context helps Maria understand why the extra charge is needed."),

    (20, "s3_agent7_pass",
     "The Reviewer checks the corrected draft. All 4 accuracy checks pass on the second attempt. "
     "The estimate is sent to Maria. "
     "If the AI had failed 3 times in a row, the order would automatically escalate to the Human Gate — nothing slips through unchecked."),

    (21, "agent9_report",
     "At the end of each business day, Agent 9 posts a digest to the FTF Invoicing channel in MS Teams. "
     "Today: 8 estimates sent, 2 orders flagged for review, 1 awaiting Robert's approval, and 14 orders total in the pipeline. "
     "Ryan, Robert, Mark, and the team receive this every day automatically — no manual reporting needed."),

    (22, "outro",
     "That's the complete Sprint 0 through 6 demo. "
     "The estimate generation loop is built and tested with 186 passing unit tests across 6 sprints. "
     "To unlock the AR follow-up reminders, we need the Jessica recording — Sprint 7. "
     "Monthly B2B statements need the Wyatt recording — Sprint 8. "
     "Sprint 9 adds the full orchestrator that runs all three loops 24 hours a day. "
     "Thank you."),
]


async def generate_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating {len(SCENES)} audio files using OpenAI tts-1-hd (nova voice)...")
    print()

    tasks = []
    for idx, slug, text in SCENES:
        out_path = OUTPUT_DIR / f"scene_{idx:02d}_{slug}.mp3"
        tasks.append((idx, slug, out_path, text))

    for idx, slug, out_path, text in tasks:
        if out_path.exists():
            print(f"  [{idx:02d}] {slug:<25} SKIP (exists)")
            continue
        print(f"  [{idx:02d}] {slug:<25} generating...", end="", flush=True)
        await atts_to_file(text, out_path)
        size_kb = out_path.stat().st_size / 1024
        print(f" {size_kb:.0f} KB")

    print()
    total = sum((OUTPUT_DIR / f"scene_{i:02d}_{s}.mp3").stat().st_size
                for i, s, _ in SCENES
                if (OUTPUT_DIR / f"scene_{i:02d}_{s}.mp3").exists())
    print(f"Done — {OUTPUT_DIR}  ({total/1024:.0f} KB total)")


if __name__ == "__main__":
    asyncio.run(generate_all())
