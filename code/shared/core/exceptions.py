class AgentError(Exception):
    pass


class ReviewerFailError(AgentError):
    pass


class MaxRetriesError(AgentError):
    pass


class LLMUnavailableError(AgentError):
    pass


class PricingError(AgentError):
    pass


class FEMAUnavailableError(AgentError):
    pass


# ── Invoice-delivery failure location (A6 exactly-once send) ──────────────────
# Distinguish WHERE a delivery attempt failed so the caller knows whether it is
# safe to retry. The email send is irreversible and FTF exposes no "already sent"
# flag, so the failure location is the only signal we have.
class PreDeliveryError(AgentError):
    """Failure BEFORE the deliver POST (login / PDF generation). Nothing was sent —
    safe to retry in-run and on the next run."""
    pass


class DeliveryAttemptedError(AgentError):
    """Failure AT OR AFTER the deliver POST. The email may or may not have gone out —
    outcome unknown. Must NOT be retried automatically (would risk a duplicate send)."""
    pass
