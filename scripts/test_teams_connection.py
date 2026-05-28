"""
test_teams_connection.py — Verify Graph API credentials and send a test notification.

Tests: config -> auth -> read channel -> send notification (email or webhook).

Usage:
    python scripts/test_teams_connection.py
    python scripts/test_teams_connection.py --read-only   # auth + read only, no send
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
    send_email_notification,
)
from config.settings import (
    NOTIFICATION_FROM_EMAIL, NOTIFICATION_TO_EMAILS,
    TEAMS_APP_ID, TEAMS_CHANNEL_ID, TEAMS_CLIENT_SECRET,
    TEAMS_INCOMING_WEBHOOK_URL, TEAMS_TEAM_ID, TEAMS_TENANT_ID,
)

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
INFO = "      "


def run_tests(read_only: bool = False) -> dict:
    results = {}
    print("\n=== FTF Teams Connection Test ===\n")

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
        results["config"] = "FAIL"
        return results
    print(f"   {PASS} Graph API env vars set")
    print(f"   {INFO} Tenant:  {TEAMS_TENANT_ID}")
    print(f"   {INFO} App ID:  {TEAMS_APP_ID}")
    print(f"   {INFO} Team:    {TEAMS_TEAM_ID}")
    print(f"   {INFO} Channel: {TEAMS_CHANNEL_ID}")

    # Notification method
    if NOTIFICATION_FROM_EMAIL and NOTIFICATION_TO_EMAILS:
        print(f"   {PASS} Notification: Graph API email")
        print(f"   {INFO} From: {NOTIFICATION_FROM_EMAIL}")
        print(f"   {INFO} To:   {NOTIFICATION_TO_EMAILS}")
    elif TEAMS_INCOMING_WEBHOOK_URL:
        wtype = "O365 connector" if "webhook.office.com" in TEAMS_INCOMING_WEBHOOK_URL \
                else "Logic App" if "logic.azure.com" in TEAMS_INCOMING_WEBHOOK_URL \
                else "Workflows"
        print(f"   {PASS} Notification: webhook ({wtype})")
    else:
        print(f"   {FAIL} No notification method configured")
        print(f"   {INFO} Set NOTIFICATION_FROM_EMAIL + NOTIFICATION_TO_EMAILS for email")
        print(f"   {INFO} Or set TEAMS_INCOMING_WEBHOOK_URL for webhook")
        results["config"] = "WARN"

    results["config"] = results.get("config", "PASS")

    # 2. Auth test
    print("\n2. Authentication (client_credentials token)")
    try:
        token = _get_token()
        print(f"   {PASS} Token obtained — {token[:20]}...{token[-10:]}")
        results["auth"] = "PASS"
    except Exception as exc:
        print(f"   {FAIL} Auth failed: {exc}")
        results["auth"] = f"FAIL: {exc}"
        return results

    # 3. Read test
    print("\n3. Read channel messages (ChannelMessage.Read.All)")
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
        print("   -> Ensure ChannelMessage.Read.All Application permission is granted with admin consent")
        results["read"] = f"FAIL: {exc}"

    if read_only:
        print(f"\n   ({SKIP} --read-only — skipping send test)")
        results["send"] = "SKIPPED"
        _print_summary(results)
        return results

    # 4. Send test
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if NOTIFICATION_FROM_EMAIL and NOTIFICATION_TO_EMAILS:
        print("\n4. Send test notification (Graph API email)")
        html = (
            f"<h3>FTF Estimate Bot -- Connection Test</h3>"
            f"<p>Graph API email verified at {now_str}.</p>"
            f"<p>The bot can send approval notifications via email.<br>"
            f"Robert/Ryan: type <code>APPROVE &lt;order_id&gt;</code> or "
            f"<code>REJECT &lt;order_id&gt; reason</code> in the FTF-Approvals Teams channel.</p>"
            f"<p><i>You can delete this email.</i></p>"
        )
        try:
            result = send_email_notification(html, subject="FTF Bot -- Connection Test")
            print(f"   {PASS} Email sent via {result.get('method')}")
            print(f"   -> Check inbox of {NOTIFICATION_TO_EMAILS}")
            results["send"] = "PASS"
        except Exception as exc:
            print(f"   {FAIL} Email send failed: {exc}")
            print("   -> Check Mail.Send Application permission + admin consent on Azure AD app")
            print("      portal.azure.com -> App registrations -> FTF Estimate Bot -> API permissions")
            results["send"] = f"FAIL: {exc}"

    elif TEAMS_INCOMING_WEBHOOK_URL:
        wtype = "O365 connector" if "webhook.office.com" in TEAMS_INCOMING_WEBHOOK_URL \
                else "Logic App" if "logic.azure.com" in TEAMS_INCOMING_WEBHOOK_URL \
                else "Workflows"
        print(f"\n4. Send test notification (webhook: {wtype})")
        html = (
            f"<p><b>FTF Estimate Bot -- Connection Test</b></p>"
            f"<p>Webhook verified at {now_str}. Type: {wtype}.</p>"
        )
        try:
            result = send_channel_message(html, subject="FTF Bot -- Connection Test")
            print(f"   {PASS} Message sent via {result.get('method')}")
            print("   -> Check FTF-Approvals channel in Teams")
            results["send"] = "PASS"
        except Exception as exc:
            print(f"   {FAIL} Webhook send failed: {exc}")
            results["send"] = f"FAIL: {exc}"

    else:
        print(f"\n4. Send test  {SKIP} — no notification method configured")
        results["send"] = "SKIPPED"

    _print_summary(results)
    return results


def _print_summary(results: dict) -> None:
    print("\n--- Summary ---")
    overall = "PASS" if all(v in ("PASS", "SKIPPED") for v in results.values()) else "PARTIAL/FAIL"
    for step, status in results.items():
        marker = PASS if status in ("PASS", "SKIPPED") else FAIL
        print(f"   {marker} {step}: {status}")
    print(f"\n   Overall: {overall}")
    print("\n=== Test complete ===\n")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Test FTF Teams connection")
    parser.add_argument("--read-only", action="store_true",
                        help="Only test auth and read; skip send")
    args = parser.parse_args(argv)
    run_tests(read_only=args.read_only)


if __name__ == "__main__":
    main()
