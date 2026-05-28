"""
test_teams_connection.py — Verify Graph API credentials and send a test message.

Run this once after configuring .env to confirm everything is wired up correctly.

Usage:
    python scripts/test_teams_connection.py
    python scripts/test_teams_connection.py --read-only   # only test auth + read, no send
"""

import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.teams_graph_client import (
    _get_token,
    get_recent_messages,
    send_channel_message,
)
from config.settings import (
    TEAMS_APP_ID, TEAMS_CHANNEL_ID, TEAMS_CLIENT_SECRET,
    TEAMS_TEAM_ID, TEAMS_TENANT_ID,
)

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "      "


def run_tests(read_only: bool = False) -> dict:
    results = {}
    print("\n=== FTF Teams Graph API Connection Test ===\n")

    # 1. Config check
    print("1. Config check")
    missing = [
        var for var, val in [
            ("TEAMS_TENANT_ID",     TEAMS_TENANT_ID),
            ("TEAMS_APP_ID",        TEAMS_APP_ID),
            ("TEAMS_CLIENT_SECRET", TEAMS_CLIENT_SECRET),
            ("TEAMS_TEAM_ID",       TEAMS_TEAM_ID),
            ("TEAMS_CHANNEL_ID",    TEAMS_CHANNEL_ID),
        ] if not val
    ]
    if missing:
        print(f"   {FAIL} Missing env vars: {', '.join(missing)}")
        print("   -> Add them to .env and re-run.")
        results["config"] = "FAIL"
        return results
    print(f"   {PASS} All 5 env vars set")
    print(f"   {INFO} Tenant:  {TEAMS_TENANT_ID}")
    print(f"   {INFO} App ID:  {TEAMS_APP_ID}")
    print(f"   {INFO} Team:    {TEAMS_TEAM_ID}")
    print(f"   {INFO} Channel: {TEAMS_CHANNEL_ID}")
    results["config"] = "PASS"

    # 2. Auth test
    print("\n2. Authentication (client_credentials token)")
    try:
        token = _get_token()
        print(f"   {PASS} Token obtained — {token[:20]}...{token[-10:]}")
        results["auth"] = "PASS"
    except Exception as exc:
        print(f"   {FAIL} Auth failed: {exc}")
        print("   -> Check TEAMS_APP_ID, TEAMS_TENANT_ID, TEAMS_CLIENT_SECRET in .env")
        results["auth"] = f"FAIL: {exc}"
        return results

    # 3. Read test
    print("\n3. Read channel messages (ChannelMessage.Read.All — Application permission)")
    try:
        messages = get_recent_messages(limit=5)
        print(f"   {PASS} Retrieved {len(messages)} recent message(s)")
        for m in messages[:3]:
            sender = m["sender"][:20]
            text   = m["text"][:55]
            print(f"   {INFO} [{m['created_at_dt'].strftime('%H:%M')}] {sender}: {text}")
        results["read"] = "PASS"
    except Exception as exc:
        print(f"   {FAIL} Read failed: {exc}")
        print("   -> Ensure ChannelMessage.Read.All Application permission is granted")
        print("      (portal.azure.com -> App registrations -> API permissions)")
        results["read"] = f"FAIL: {exc}"

    if read_only:
        print("\n   (--read-only flag set — skipping send test)")
        results["send"] = "SKIPPED"
        return results

    # 4. Send test
    print("\n4. Send test message (ChannelMessage.Send — Application permission)")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = (
        f"<p><b>FTF Estimate Bot — Connection Test</b></p>"
        f"<p>Graph API connection verified at {now_str}.<br>"
        f"This message confirms the bot can post to the FTF-Approvals channel.<br>"
        f"<i>You can delete this message.</i></p>"
    )
    try:
        result = send_channel_message(html, subject="FTF Bot — Connection Test")
        print(f"   {PASS} Message sent — id={result.get('id')}")
        print(f"   -> Check the #FTF-Approvals channel in Teams to confirm it appeared")
        results["send"] = "PASS"
    except Exception as exc:
        print(f"   {FAIL} Send failed: {exc}")
        print("   -> Ensure ChannelMessage.Send Application permission is granted + admin consent")
        print("   -> If HTTP 403: the app may need to be installed in the Teams team:")
        print("      Teams -> your team -> Manage Team -> Apps -> Upload a custom app")
        results["send"] = f"FAIL: {exc}"

    # Summary
    print("\n--- Summary ---")
    overall = "PASS" if all(v == "PASS" for v in results.values()) else "PARTIAL/FAIL"
    for step, status in results.items():
        marker = PASS if status == "PASS" else FAIL
        print(f"   {marker} {step}: {status}")
    print(f"\n   Overall: {overall}")
    print("\n=== Test complete ===\n")
    return results


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Test Teams Graph API connection")
    parser.add_argument("--read-only", action="store_true",
                        help="Only test auth and read; skip sending a message")
    args = parser.parse_args(argv)
    run_tests(read_only=args.read_only)


if __name__ == "__main__":
    main()
