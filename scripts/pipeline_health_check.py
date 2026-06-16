"""pipeline_health_check.py — detect orders stuck mid-pipeline and email a digest.

Safety net so the invoicing agent NEVER strands an order silently. Reads the pipeline state
and finds orders sitting in a non-terminal "working" status longer than AGE_THRESHOLD_HOURS.
If any are found, emails a digest to NOTIFICATION_TO_EMAILS so a human can intervene. Defensive
by design: never raises, always exits 0 — a monitoring tool must not itself break a run.

Run by .github/workflows/pipeline_health.yml on a daily schedule.
"""

import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
JSON_STATE = os.path.join(_REPO_ROOT, "data", "pipeline_state.json")

AGE_THRESHOLD_HOURS = float(os.getenv("HEALTH_AGE_HOURS", "24"))

# Non-terminal "in-flight" statuses. An order resting here too long means something stalled
# (FTF/OneDrive outage, missing data, or a human never actioned the row).
STUCK_STATUSES = {
    "data_collected":    "waiting for A3 pricing",
    "invoice_approved":  "approved but A5 hasn't created the FTF invoice",
    "invoice_finalized": "invoice created but A6 hasn't sent it",
    "details_missing":   "A2 couldn't collect enough data — needs attention",
    "pricing_needed":    "awaiting manual pricing in the sheet",
    "delivered_flagged": "delivered order awaiting a human decision",
}


def _parse_dt(s: str):
    if not s:
        return None
    try:
        s = str(s).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _age_hours(order: dict):
    dt = _parse_dt(order.get("updated_at")) or _parse_dt(order.get("created_at"))
    if not dt:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


def _send_email(subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587") or "587")
    user = os.getenv("SMTP_USER", "")
    pwd  = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM") or user
    to_raw = os.getenv("NOTIFICATION_TO_EMAILS", "") or os.getenv("NOTIFICATION_FROM_EMAIL", "")
    recipients = [e.strip() for e in to_raw.replace(";", ",").split(",") if e.strip()]
    if not (host and sender and recipients):
        print(f"[health] SMTP not configured — digest NOT emailed. Body:\n{body}")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        if user and pwd:
            s.login(user, pwd)
        s.sendmail(sender, recipients, msg.as_string())
    print(f"[health] digest emailed to {recipients}")


def main() -> None:
    try:
        with open(JSON_STATE, encoding="utf-8") as f:
            orders = json.load(f).get("orders", [])
    except Exception as exc:
        print(f"[health] could not read state ({exc}) — skipping")
        return

    stuck = []
    for o in orders:
        status = o.get("status")
        if status not in STUCK_STATUSES:
            continue
        age = _age_hours(o)
        if age is None or age >= AGE_THRESHOLD_HOURS:
            stuck.append((status, o.get("order_id"), age))

    if not stuck:
        print(f"[health] OK — no orders stuck > {AGE_THRESHOLD_HOURS:.0f}h")
        return

    stuck.sort(key=lambda t: (t[0], -(t[2] or 1e9)))
    lines = [f"{len(stuck)} order(s) stuck > {AGE_THRESHOLD_HOURS:.0f}h in the FTF invoice pipeline:\n"]
    cur = None
    for status, oid, age in stuck:
        if status != cur:
            cur = status
            lines.append(f"\n[{status}] — {STUCK_STATUSES.get(status, '')}")
        age_str = f"{age:.0f}h" if age is not None else "unknown age"
        lines.append(f"  • {oid}  ({age_str})")
    lines.append("\nCheck the approval sheet / GitHub Actions logs and resolve.")
    body = "\n".join(lines)
    print(body)
    try:
        _send_email(f"⚠ FTF pipeline: {len(stuck)} stuck order(s)", body)
    except Exception as exc:
        print(f"[health] email send failed (non-fatal): {exc}")


if __name__ == "__main__":
    main()
    sys.exit(0)
