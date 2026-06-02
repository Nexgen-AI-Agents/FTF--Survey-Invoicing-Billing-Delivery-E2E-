"""
Sprint 9 — Agent 13 Pricing Trainer unit tests (I-067 + I-069)

All DB interactions mocked. Tests verify:
  1.  submit_pricing_example saves to DB when role is permitted (Robert → pricing)
  2.  submit_pricing_example raises GovernanceError when role is wrong (Jessica → pricing)
  3.  submit_pricing_example raises GovernanceError for unknown role
  4.  submit_pricing_example raises AgentError when job_description is missing
  5.  submit_pricing_example raises AgentError when final_price is missing/zero
  6.  submit_pricing_example raises AgentError when entered_by is missing
  7.  superuser (ryan) can submit to any domain
  8.  mark is permitted for pricing/logistics domain
  9.  jessica is permitted for ar domain
  10. returned dict contains expected keys after successful save
  11. get_training_summary delegates to get_recent_pricing_examples
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "shared"))
sys.path.insert(0, str(Path(__file__).parents[1] / "agents"))

from agent_13_pricing_trainer import submit_pricing_example, get_training_summary
from core.governance import GovernanceError
from core.exceptions import AgentError


def _base_example(**overrides) -> dict:
    base = {
        "entered_by": "Robert",
        "job_description": "Half-acre residential, pool + 2 sheds, Palm Beach",
        "final_price": 700.00,
        "service_type": "Boundary Survey",
        "county": "Palm Beach",
        "domain": "pricing",
    }
    base.update(overrides)
    return base


# ── 1. Permitted role saves successfully ────────────────────────────────────

@patch("agent_13_pricing_trainer.log_decision")
@patch("agent_13_pricing_trainer.save_pricing_example", return_value=42)
def test_submit_saves_when_permitted(mock_save, mock_log):
    result = submit_pricing_example(_base_example())
    assert result["saved"] is True
    assert result["id"] == 42
    assert result["entered_by"] == "Robert"
    assert result["service_type"] == "Boundary Survey"
    mock_save.assert_called_once()
    mock_log.assert_called_once()


# ── 2. Wrong role raises GovernanceError ────────────────────────────────────

@patch("agent_13_pricing_trainer.save_pricing_example")
def test_submit_raises_governance_error_for_jessica_pricing(mock_save):
    with pytest.raises(GovernanceError):
        submit_pricing_example(_base_example(entered_by="Jessica", domain="pricing"))
    mock_save.assert_not_called()


# ── 3. Unknown role raises GovernanceError ──────────────────────────────────

@patch("agent_13_pricing_trainer.save_pricing_example")
def test_submit_raises_governance_error_for_unknown_role(mock_save):
    with pytest.raises(GovernanceError):
        submit_pricing_example(_base_example(entered_by="Bob", domain="pricing"))
    mock_save.assert_not_called()


# ── 4. Missing job_description raises AgentError ────────────────────────────

def test_submit_raises_on_missing_job_description():
    with pytest.raises(AgentError):
        submit_pricing_example(_base_example(job_description=""))


# ── 5. Missing / zero final_price raises AgentError ─────────────────────────

def test_submit_raises_on_zero_price():
    with pytest.raises(AgentError):
        submit_pricing_example(_base_example(final_price=0))


def test_submit_raises_on_missing_price():
    ex = _base_example()
    del ex["final_price"]
    with pytest.raises(AgentError):
        submit_pricing_example(ex)


# ── 6. Missing entered_by raises AgentError ─────────────────────────────────

def test_submit_raises_on_missing_entered_by():
    with pytest.raises(AgentError):
        submit_pricing_example(_base_example(entered_by=""))


# ── 7. Superuser (ryan) bypasses domain check ───────────────────────────────

@patch("agent_13_pricing_trainer.log_decision")
@patch("agent_13_pricing_trainer.save_pricing_example", return_value=99)
def test_superuser_ryan_permitted_any_domain(mock_save, mock_log):
    result = submit_pricing_example(_base_example(entered_by="ryan", domain="ar"))
    assert result["saved"] is True
    assert result["id"] == 99


# ── 8. Mark denied for all domains (removed stakeholder) ─────────────────────

def test_mark_denied_pricing():
    with pytest.raises(Exception):   # GovernanceError — mark no longer in ROLE_DOMAINS
        submit_pricing_example(_base_example(entered_by="mark", domain="pricing"))


# ── 9. Jessica permitted for ar domain ───────────────────────────────────────

@patch("agent_13_pricing_trainer.log_decision")
@patch("agent_13_pricing_trainer.save_pricing_example", return_value=5)
def test_jessica_permitted_ar_domain(mock_save, mock_log):
    result = submit_pricing_example(_base_example(entered_by="jessica", domain="ar"))
    assert result["saved"] is True


# ── 10. Returned dict has expected keys ──────────────────────────────────────

@patch("agent_13_pricing_trainer.log_decision")
@patch("agent_13_pricing_trainer.save_pricing_example", return_value=10)
def test_submit_result_keys(mock_save, mock_log):
    result = submit_pricing_example(_base_example())
    assert set(result.keys()) == {"saved", "id", "entered_by", "service_type", "county", "final_price"}


# ── 11. get_training_summary delegates to get_recent_pricing_examples ────────

@patch("agent_13_pricing_trainer.get_recent_pricing_examples", return_value=[{"id": 1}])
def test_get_training_summary_delegates(mock_recent):
    result = get_training_summary(limit=5)
    mock_recent.assert_called_once_with(limit=5)
    assert result == [{"id": 1}]
