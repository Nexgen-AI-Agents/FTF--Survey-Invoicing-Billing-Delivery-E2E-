"""
Foundation tests — Governance module (I-069)

All external calls (Teams webhook, httpx) are mocked.
Tests verify:
  1.  check_permission allows Robert to access pricing domain
  2.  check_permission allows Mark to access logistics domain
  3.  check_permission allows Jessica to access ar domain
  4.  check_permission allows Jessica to access refund domain
  5.  check_permission raises GovernanceError for Robert → ar domain
  6.  check_permission raises GovernanceError for Jessica → pricing domain
  7.  check_permission allows Ryan (superuser) to access any domain
  8.  check_permission allows Prateek (superuser) to access any domain
  9.  check_permission raises GovernanceError for unknown role
  10. get_role_domains returns correct set for Robert
  11. get_role_domains returns {'all'} for Ryan (superuser)
  12. get_role_domains returns empty set for unknown role
  13. cross_domain_alert logs warning and sends Teams card when webhook is set
  14. cross_domain_alert skips Teams silently when no webhook configured
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "shared"))

from core.governance import (
    GovernanceError,
    check_permission,
    cross_domain_alert,
    get_role_domains,
)


# ── 1-4. Allowed role→domain pairs ───────────────────────────────────────────

@pytest.mark.parametrize("role,domain", [
    ("Robert", "pricing"),
    ("robert", "pricing"),
    ("Mark", "logistics"),
    ("mark", "logistics"),
    ("Jessica", "ar"),
    ("jessica", "refund"),
])
def test_check_permission_allowed(role, domain):
    check_permission(role, domain)  # must not raise


# ── 5-6. Denied role→domain pairs ────────────────────────────────────────────

@pytest.mark.parametrize("role,domain", [
    ("Robert", "ar"),
    ("robert", "refund"),
    ("Jessica", "pricing"),
    ("jessica", "logistics"),
])
def test_check_permission_denied(role, domain):
    with pytest.raises(GovernanceError):
        check_permission(role, domain)


# ── 7-8. Superusers bypass all domain checks ─────────────────────────────────

@pytest.mark.parametrize("role,domain", [
    ("ryan", "pricing"),
    ("ryan", "ar"),
    ("ryan", "logistics"),
    ("ryan", "refund"),
    ("prateek", "pricing"),
    ("prateek", "ar"),
])
def test_superuser_bypasses_domain_check(role, domain):
    check_permission(role, domain)  # must not raise


# ── 9. Unknown role denied ───────────────────────────────────────────────────

def test_check_permission_unknown_role_raises():
    with pytest.raises(GovernanceError):
        check_permission("bob_the_builder", "pricing")


# ── 10. get_role_domains for Robert ──────────────────────────────────────────

def test_get_role_domains_robert():
    domains = get_role_domains("Robert")
    assert "pricing" in domains
    assert "logistics" in domains
    assert "ar" not in domains


# ── 11. get_role_domains for superuser ───────────────────────────────────────

def test_get_role_domains_superuser():
    assert get_role_domains("ryan") == {"all"}
    assert get_role_domains("prateek") == {"all"}


# ── 12. get_role_domains for unknown role ────────────────────────────────────

def test_get_role_domains_unknown():
    assert get_role_domains("stranger") == set()


# ── 13. cross_domain_alert sends Teams card when webhook present ─────────────

@patch("core.governance.TEAMS_WEBHOOK_URL", "https://hooks.example.com/webhook")
@patch("httpx.post")
def test_cross_domain_alert_sends_teams_card(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    cross_domain_alert("Robert", "ar", "trying to change AR escalation threshold")
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
    assert payload["themeColor"] == "FF0000"
    assert "Robert" in payload["text"]
    assert "ar" in payload["text"]


# ── 14. cross_domain_alert is silent when no webhook configured ──────────────

@patch("core.governance.TEAMS_WEBHOOK_URL", None)
@patch("httpx.post")
def test_cross_domain_alert_silent_without_webhook(mock_post):
    cross_domain_alert("Robert", "ar", "some change")
    mock_post.assert_not_called()
