"""Role-based domain ownership for AI rule modification (I-069).

Each role maps to the set of domains it is permitted to modify.
No role may modify another role's domain without cross-approval.

Domains:
  pricing   — rate tables, service-type pricing, complexity factors, county modifiers
  logistics — crew scheduling, travel fees, turnaround rules
  ar        — AR reminder schedule, escalation thresholds, exclusion list
  refund    — refund routing rules, Jessica alert triggers
  all       — superuser roles (Ryan, Prateek) — no restrictions
"""

ROLE_DOMAINS: dict[str, set[str]] = {
    "robert": {"pricing", "logistics"},
    "mark":   {"pricing", "logistics"},
    "jessica": {"ar", "refund"},
    "ryan":   {"all"},
    "prateek": {"all"},
}

# Human-readable contact for cross-domain notifications
CROSS_DOMAIN_NOTIFY_EMAIL = "ai@nexgen.enterprises"

# Teams webhook used by governance alerts (falls back to TEAMS_WEBHOOK_URL env var)
GOVERNANCE_TEAMS_CHANNEL = "FTF Agentic AI — Governance Alerts"
