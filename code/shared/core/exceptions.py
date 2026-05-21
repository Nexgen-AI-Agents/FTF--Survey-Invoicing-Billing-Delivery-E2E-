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
