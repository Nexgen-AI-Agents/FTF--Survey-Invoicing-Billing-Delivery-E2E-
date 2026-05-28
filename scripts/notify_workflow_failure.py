"""
notify_workflow_failure.py — Post a workflow failure alert to Teams.

Called by GitHub Actions on any workflow failure via:
    python scripts/notify_workflow_failure.py --workflow "Teams Approval Monitor"

Reads TEAMS_INCOMING_WEBHOOK_URL (and Graph API fallback) from env.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.teams_graph_client import send_channel_message


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", default="Unknown Workflow", help="Workflow name")
    parser.add_argument("--run-url", default="", help="GitHub Actions run URL")
    args = parser.parse_args()

    run_link = f"<a href='{args.run_url}'>View run</a>" if args.run_url else "Check GitHub Actions"
    html = (
        f"<h3>&#9888; GitHub Actions Failure — {args.workflow}</h3>"
        f"<p>The <strong>{args.workflow}</strong> workflow failed on its last run.<br>"
        f"Pending orders may <strong>not</strong> be processed until this is resolved.</p>"
        f"<p>{run_link}</p>"
        f"<p>Common causes: DB connection timeout, Teams API rate limit, Python dependency error.<br>"
        f"Check the run log and re-trigger manually if needed.</p>"
    )

    result = send_channel_message(html, subject=f"Workflow Failure — {args.workflow}")
    print(f"Teams alert sent: {result}")


if __name__ == "__main__":
    main()
