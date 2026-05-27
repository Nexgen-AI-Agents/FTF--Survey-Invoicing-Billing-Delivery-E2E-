"""Role-based AI modification governance (I-069).

Enforces domain ownership: Robert modifies pricing/logistics, Jessica modifies
AR/refund rules. Neither may modify the other's domain without explicit
cross-approval and Prateek notification.

Hard rules:
  - check_permission() raises GovernanceError if role lacks domain access
  - cross_domain_alert() sends Teams notification to Prateek and logs the attempt
  - Superuser roles (ryan, prateek) bypass all domain checks
"""

import os
from core.exceptions import AgentError
from core.logger import get_logger
from config.roles import ROLE_DOMAINS, CROSS_DOMAIN_NOTIFY_EMAIL

log = get_logger("governance")

TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")


class GovernanceError(AgentError):
    """Raised when a role attempts to modify a domain it does not own."""


def _is_superuser(role: str) -> bool:
    domains = ROLE_DOMAINS.get(role.lower(), set())
    return "all" in domains


def check_permission(role: str, domain: str) -> None:
    """Raise GovernanceError if `role` is not permitted to modify `domain`.

    Superuser roles (ryan, prateek) always pass.
    Unknown roles have no permissions.
    """
    role_lower = role.lower()
    domain_lower = domain.lower()

    if _is_superuser(role_lower):
        log.info("governance: superuser %s accessing domain=%s — allowed", role, domain)
        return

    allowed = ROLE_DOMAINS.get(role_lower, set())
    if domain_lower not in allowed:
        log.warning(
            "governance: DENIED role=%s domain=%s allowed_domains=%s",
            role, domain, allowed,
        )
        raise GovernanceError(
            f"Role '{role}' is not permitted to modify domain '{domain}'. "
            f"Permitted domains: {sorted(allowed) if allowed else 'none'}. "
            f"Contact Prateek ({CROSS_DOMAIN_NOTIFY_EMAIL}) for cross-domain changes."
        )

    log.info("governance: ALLOWED role=%s domain=%s", role, domain)


def cross_domain_alert(requester: str, target_domain: str, change_description: str) -> None:
    """Send Teams + log a cross-domain modification attempt that was blocked.

    Called when check_permission() would have raised but the caller wants to
    surface the attempt for human escalation instead of hard-stopping.
    """
    log.warning(
        "CROSS-DOMAIN ATTEMPT: requester=%s target_domain=%s description=%s",
        requester, target_domain, change_description[:200],
    )

    if not TEAMS_WEBHOOK_URL:
        log.warning("TEAMS_WEBHOOK_URL not set — cross-domain alert not sent to Teams")
        return

    try:
        import httpx
        title = f"Governance Alert: Cross-Domain Modification Attempt"
        body = (
            f"**Requester:** {requester}  \n"
            f"**Target Domain:** {target_domain}  \n"
            f"**Change Requested:** {change_description[:400]}  \n\n"
            f"This change requires approval from the domain owner AND Prateek "
            f"({CROSS_DOMAIN_NOTIFY_EMAIL}) before it can be applied."
        )
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "FF0000",
            "summary": title,
            "title": title,
            "text": body,
        }
        httpx.post(TEAMS_WEBHOOK_URL, json=payload, timeout=15)
        log.info("cross-domain Teams alert sent for requester=%s domain=%s", requester, target_domain)
    except Exception as exc:
        log.error("failed to send cross-domain Teams alert: %s", exc)


def get_role_domains(role: str) -> set[str]:
    """Return the set of domains a role is permitted to modify."""
    role_lower = role.lower()
    if _is_superuser(role_lower):
        return {"all"}
    return ROLE_DOMAINS.get(role_lower, set())
