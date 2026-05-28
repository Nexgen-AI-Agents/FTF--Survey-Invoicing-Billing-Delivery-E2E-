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
    check_for_approvals,
    get_recent_messages,
    send_channel_message,
)
from config.settings import (
    TEAMS_APP_ID, TEAMS_CHANNEL_ID, TEAMS_CLIENT_SECRET,
    TEAMS_TEAM_ID, TEAMS_TENANT_ID,
)


def run_tests(read_only: bool = False) -> None:
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
        print(f"   ❌ Missing env vars: {', '.join(missing)}")
        print("   → Add them to .env and re-run.")
        return
    print(f"   ✅ All 5 env vars set")
    print(f"      Tenant:  {TEAMS_TENANT_ID}")
    print(f"      App ID:  {TEAMS_APP_ID}")
    print(f"      Team:    {TEAMS_TEAM_ID}")
    print(f"      Channel: {TEAMS_CHANNEL_ID}")

    # 2. Auth test
    print("\n2. Authentication (client_credentials token)")
    try:
        token = _get_token()
        print(f"   ✅ Token obtained — {token[:20]}...{token[-10:]}")
    except Exception as exc:
        print(f"   ❌ Auth failed: {exc}")
        print("   → Check TEAMS_APP_ID, TEAMS_TENANT_ID, TEAMS_CLIENT_SECRET in .env")
        return

    # 3. Read test
    print("\n3. Read channel messages (ChannelMessage.Read.All)")
    try:
        messages = get_recent_messages(limit=5)
        print(f"   ✅ Retrieved {len(messages)} recent message(s)")
        for m in messages[:3]:
            print(f"      [{m['created_at_dt'].strftime('%H:%M')}] {m['sender']}: {m['text'][:60]}")
    except Exception as exc:
        print(f"   ❌ Read failed: {exc}")
        print("   → Ensure ChannelMessage.Read.All is granted (admin consent in Azure portal)")
        print("   → The app may also need to be added to the Teams team as a member")

    if read_only:
        print("\n   (--read-only flag set — skipping send test)")
        return

    # 4. Send test
    print("\n4. Send test message (ChannelMessage.Send)")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html    = (
        f"<p><b>FTF Estimate Bot — Connection Test</b></p>"
        f"<p>✅ Graph API connection verified at {now_str}.<br>"
        f"This message confirms the bot can post to the FTF-Approvals channel.<br>"
        f"<i>You can delete this message.</i></p>"
    )
    try:
        result = send_channel_message(html, subject="FTF Bot — Connection Test")
        print(f"   ✅ Message sent — id={result.get('id')}")
        print(f"   → Check the #FTF-Approvals channel in Teams to confirm it appeared")
    except Exception as exc:
        print(f"   ❌ Send failed: {exc}")
        print("   → Ensure ChannelMessage.Send is granted (admin consent in Azure portal)")
        print("   → The app may need to be installed in the Teams team:")
        print("      Teams > your team > Manage Team > Apps > Upload custom app")

    print("\n=== Test complete ===\n")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Test Teams Graph API connection")
    parser.add_argument("--read-only", action="store_true",
                        help="Only test auth and read; skip sending a message")
    args = parser.parse_args(argv)
    run_tests(read_only=args.read_only)


if __name__ == "__main__":
    main()
