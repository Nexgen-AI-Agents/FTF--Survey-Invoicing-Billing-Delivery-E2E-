"""notify_failure_email.py — email a failure alert when a pipeline workflow fails.

Wired into GitHub Actions with `if: failure()` so a human is ALWAYS told when a run breaks
(the pipeline must never fail silently). Uses the SMTP_* env vars already present in the job
and sends to NOTIFICATION_TO_EMAILS. This script is defensive by design: it NEVER raises and
ALWAYS exits 0, so the alerting step itself can't turn a failure into a confusing second error.

Usage:
    python scripts/notify_failure_email.py --workflow "Invoice Pipeline" --run-url "<url>"
"""

import argparse
import os
import smtplib
import sys
from email.mime.text import MIMEText

from dotenv import load_dotenv

# Server runs this standalone (not under the orchestrator), so pull SMTP_* from the
# deploy .env here. No-op in GitHub Actions where these are already real env vars
# (load_dotenv does not override values already present in the environment).
load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", default="Invoice Pipeline")
    parser.add_argument("--run-url", default="")
    args = parser.parse_args()

    try:
        host = os.getenv("SMTP_HOST", "")
        port = int(os.getenv("SMTP_PORT", "587") or "587")
        user = os.getenv("SMTP_USER", "")
        pwd  = os.getenv("SMTP_PASSWORD", "")
        sender = os.getenv("SMTP_FROM") or user
        to_raw = os.getenv("NOTIFICATION_TO_EMAILS", "") or os.getenv("NOTIFICATION_FROM_EMAIL", "")
        recipients = [e.strip() for e in to_raw.replace(";", ",").split(",") if e.strip()]

        if not (host and sender and recipients):
            print(f"[notify] SMTP not fully configured (host={bool(host)} from={bool(sender)} "
                  f"to={len(recipients)}) — skipping email, but FAILURE WAS LOGGED.")
            return

        body = (
            f"The '{args.workflow}' workflow FAILED on its last run.\n\n"
            f"Run: {args.run_url or 'check GitHub Actions'}\n\n"
            "Impact: invoices may not be processed/sent until this is resolved.\n"
            "Action: open the run log, fix the cause, then re-trigger.\n\n"
            "Common causes: FTF API/MySQL timeout, OneDrive/Graph auth, Anthropic+OpenAI both "
            "unreachable, or a dependency error.\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"⚠ FTF {args.workflow} FAILED — action needed"
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)

        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls()
            if user and pwd:
                s.login(user, pwd)
            s.sendmail(sender, recipients, msg.as_string())
        print(f"[notify] failure email sent to {recipients}")
    except Exception as exc:
        # Never let the alerting step itself fail the job or mask the real error.
        print(f"[notify] failed to send failure email (non-fatal): {exc}")


if __name__ == "__main__":
    main()
    sys.exit(0)
