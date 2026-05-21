import pytest
from core.exceptions import (
    AgentError,
    FEMAUnavailableError,
    LLMUnavailableError,
    MaxRetriesError,
    PricingError,
    ReviewerFailError,
)


def test_all_exceptions_are_agent_error_subclasses():
    for cls in (ReviewerFailError, MaxRetriesError, LLMUnavailableError, PricingError, FEMAUnavailableError):
        assert issubclass(cls, AgentError)


def test_exceptions_can_be_raised_and_caught():
    with pytest.raises(AgentError):
        raise ReviewerFailError("review failed")

    with pytest.raises(LLMUnavailableError):
        raise LLMUnavailableError("claude down")

    with pytest.raises(PricingError):
        raise PricingError("pricing api failed")

    with pytest.raises(FEMAUnavailableError):
        raise FEMAUnavailableError("fema timeout")

    with pytest.raises(MaxRetriesError):
        raise MaxRetriesError("max retries exceeded")


def test_exception_messages_preserved():
    exc = AgentError("something went wrong")
    assert "something went wrong" in str(exc)
