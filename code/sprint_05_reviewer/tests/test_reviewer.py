import pytest
from unittest.mock import patch, MagicMock, call

from agents.agent_07_reviewer import (
    review_estimate,
    run,
    _run_checks,
    AGENT_NAME,
)
from core.exceptions import AgentError, ReviewerFailError


# ── shared fixtures ───────────────────────────────────────────────────────────

_CLAUSE = (
    "Change Order Authorization\n\n"
    "By approving this estimate, you authorize NexGen Surveying to issue a change order "
    "if the scope or complexity of the work changes after this estimate is accepted. "
    "Change orders may arise from conditions discovered during field work that were not "
    "evident at the time of estimation, including but not limited to: additional structures "
    "or features requiring documentation, flood zone determination requirements, title chain "
    "issues, or additional county-required reviews.\n\n"
    "NexGen Surveying will contact you prior to performing any out-of-scope work to explain "
    "the reason for the change and obtain your written or verbal authorization. No additional "
    "charges will be added to your invoice without your prior approval.\n\n"
    "Change order rates are billed at NexGen Surveying's standard rates in effect at the time of service."
)

_GOOD_DRAFT = (
    "Dear Jane Smith,\n\n"
    "Thank you for contacting NexGen Surveying.\n\n"
    "Property: 123 Oak Street, Miami, FL 33101\n"
    "Service: Boundary Survey\n"
    "Total: $450.00\n\n"
    + _CLAUSE
)

_DB_ROW = {
    "order_id": "ORD-201",
    "status": "written",
    "service_type": "Boundary Survey",
    "customer_email": "jane@example.com",
    "estimate_amount": 450.00,
    "draft_estimate": _GOOD_DRAFT,
    "retry_count": 0,
}

_FTF_ORDER = {
    "order_id": "ORD-201",
    "customer_name": "Jane Smith",
    "property_address": "123 Oak Street, Miami, FL 33101",
    "service_type": "Boundary Survey",
    "customer_type": "individual",
}


# ── unit tests for _run_checks (pure function, no mocks needed) ───────────────

def test_run_checks_all_pass():
    failures = _run_checks(_GOOD_DRAFT, 450.00, "Jane Smith", "123 Oak Street, Miami, FL 33101", _CLAUSE)
    assert failures == []


def test_run_checks_wrong_price():
    failures = _run_checks(_GOOD_DRAFT, 999.00, "Jane Smith", "123 Oak Street, Miami, FL 33101", _CLAUSE)
    assert any("price" in f for f in failures)


def test_run_checks_missing_customer_name():
    draft = _GOOD_DRAFT.replace("Jane Smith", "Valued Customer")
    failures = _run_checks(draft, 450.00, "Jane Smith", "123 Oak Street, Miami, FL 33101", _CLAUSE)
    assert any("customer name" in f for f in failures)


def test_run_checks_missing_address():
    draft = _GOOD_DRAFT.replace("123 Oak Street", "See attached")
    failures = _run_checks(draft, 450.00, "Jane Smith", "123 Oak Street, Miami, FL 33101", _CLAUSE)
    assert any("address" in f for f in failures)


def test_run_checks_clause_modified():
    bad_clause = "You agree to pay extra if needed."
    draft = _GOOD_DRAFT.replace(_CLAUSE, bad_clause)
    failures = _run_checks(draft, 450.00, "Jane Smith", "123 Oak Street, Miami, FL 33101", _CLAUSE)
    assert any("clause" in f for f in failures)


def test_run_checks_clause_whitespace_variation():
    # Extra spaces in draft should still pass
    draft_with_extra_spaces = _GOOD_DRAFT.replace("Change Order Authorization", "Change  Order  Authorization")
    failures = _run_checks(draft_with_extra_spaces, 450.00, "Jane Smith", "123 Oak Street, Miami, FL 33101", _CLAUSE)
    # Whitespace normalization means clause check should still pass
    clause_failures = [f for f in failures if "clause" in f]
    assert clause_failures == []


# ── UT-05-01  correct estimate passes all 4 checks, returns reviewed ─────────

def test_review_estimate_passes_all_checks():
    with patch("agents.agent_07_reviewer.get_order_by_id", return_value=_DB_ROW), \
         patch("agents.agent_07_reviewer.get_order", return_value=_FTF_ORDER), \
         patch("agents.agent_07_reviewer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_07_reviewer.save_order_state") as mock_save, \
         patch("agents.agent_07_reviewer.log_decision"):
        result = review_estimate("ORD-201")

    assert result["status"] == "reviewed"
    assert result["checks_passed"] == 4
    assert result["order_id"] == "ORD-201"
    # DB must be updated to "reviewed"
    mock_save.assert_called_once()
    assert mock_save.call_args[1]["status"] == "reviewed"


# ── UT-05-02  wrong price detected → rewrite triggered → passes on 2nd ───────

def test_wrong_price_triggers_rewrite_then_passes():
    wrong_draft = _GOOD_DRAFT.replace("$450.00", "$999.00")
    rows = [
        {**_DB_ROW, "draft_estimate": wrong_draft},  # attempt 1 — fail
        {**_DB_ROW, "draft_estimate": _GOOD_DRAFT},  # attempt 2 — pass (after rewrite)
    ]
    row_iter = iter(rows)

    with patch("agents.agent_07_reviewer.get_order_by_id", side_effect=lambda _: next(row_iter)), \
         patch("agents.agent_07_reviewer.get_order", return_value=_FTF_ORDER), \
         patch("agents.agent_07_reviewer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_07_reviewer.save_order_state"), \
         patch("agents.agent_07_reviewer.log_decision"), \
         patch("agents.agent_07_reviewer.write_estimate") as mock_write:
        result = review_estimate("ORD-201")

    mock_write.assert_called_once()
    assert "price" in mock_write.call_args[1]["correction_note"].lower()
    assert result["status"] == "reviewed"


# ── UT-05-03  missing clause triggers rewrite ─────────────────────────────────

def test_missing_clause_triggers_rewrite():
    no_clause_draft = _GOOD_DRAFT.replace(_CLAUSE, "")
    rows = [
        {**_DB_ROW, "draft_estimate": no_clause_draft},
        {**_DB_ROW, "draft_estimate": _GOOD_DRAFT},
    ]
    row_iter = iter(rows)

    with patch("agents.agent_07_reviewer.get_order_by_id", side_effect=lambda _: next(row_iter)), \
         patch("agents.agent_07_reviewer.get_order", return_value=_FTF_ORDER), \
         patch("agents.agent_07_reviewer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_07_reviewer.save_order_state"), \
         patch("agents.agent_07_reviewer.log_decision"), \
         patch("agents.agent_07_reviewer.write_estimate") as mock_write:
        result = review_estimate("ORD-201")

    mock_write.assert_called_once()
    assert "clause" in mock_write.call_args[1]["correction_note"].lower()
    assert result["status"] == "reviewed"


# ── UT-05-04  3 consecutive failures → ReviewerFailError + order flagged ─────

def test_three_failures_raise_reviewer_fail_error():
    bad_draft = _GOOD_DRAFT.replace("$450.00", "$999.00")
    bad_row = {**_DB_ROW, "draft_estimate": bad_draft, "retry_count": 0}

    with patch("agents.agent_07_reviewer.get_order_by_id", return_value=bad_row), \
         patch("agents.agent_07_reviewer.get_order", return_value=_FTF_ORDER), \
         patch("agents.agent_07_reviewer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_07_reviewer.save_order_state") as mock_save, \
         patch("agents.agent_07_reviewer.log_decision"), \
         patch("agents.agent_07_reviewer.write_estimate"):
        with pytest.raises(ReviewerFailError):
            review_estimate("ORD-201")

    # Order must be set to 'flagged' on final failure
    flagged_call = next(
        (c for c in mock_save.call_args_list if c[1].get("status") == "flagged"), None
    )
    assert flagged_call is not None, "save_order_state was never called with status='flagged'"


# ── UT-05-05  order not found → AgentError ───────────────────────────────────

def test_order_not_found_raises_agent_error():
    with patch("agents.agent_07_reviewer.get_order_by_id", return_value=None):
        with pytest.raises(AgentError, match="not found"):
            review_estimate("ORD-999")


# ── UT-05-06  no draft_estimate in DB → AgentError ───────────────────────────

def test_no_draft_raises_agent_error():
    row_no_draft = {**_DB_ROW, "draft_estimate": None}
    with patch("agents.agent_07_reviewer.get_order_by_id", return_value=row_no_draft), \
         patch("agents.agent_07_reviewer.get_order", return_value=_FTF_ORDER), \
         patch("agents.agent_07_reviewer._load_clause", return_value=_CLAUSE):
        with pytest.raises(AgentError, match="no draft_estimate"):
            review_estimate("ORD-201")


# ── UT-05-07  run() picks first written order ─────────────────────────────────

def test_run_picks_first_written_order():
    with patch("agents.agent_07_reviewer.get_written_order",
               return_value=_DB_ROW) as mock_get, \
         patch("agents.agent_07_reviewer.get_order_by_id", return_value=_DB_ROW), \
         patch("agents.agent_07_reviewer.get_order", return_value=_FTF_ORDER), \
         patch("agents.agent_07_reviewer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_07_reviewer.save_order_state"), \
         patch("agents.agent_07_reviewer.log_decision"):
        result = run()

    mock_get.assert_called_once()
    assert result["order_id"] == "ORD-201"


# ── UT-05-08  run() returns None when no written orders ──────────────────────

def test_run_returns_none_when_no_written_orders():
    with patch("agents.agent_07_reviewer.get_written_order", return_value=None):
        result = run()
    assert result is None


# ── UT-05-09  reviewer flag_reason contains failure description ───────────────

def test_flag_reason_contains_failure_description():
    bad_draft = _GOOD_DRAFT.replace("$450.00", "$999.00")
    bad_row = {**_DB_ROW, "draft_estimate": bad_draft}

    flag_reason_captured = {}

    def capture_save(order_id, **kwargs):
        if kwargs.get("status") == "flagged":
            flag_reason_captured["reason"] = kwargs.get("flag_reason", "")

    with patch("agents.agent_07_reviewer.get_order_by_id", return_value=bad_row), \
         patch("agents.agent_07_reviewer.get_order", return_value=_FTF_ORDER), \
         patch("agents.agent_07_reviewer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_07_reviewer.save_order_state", side_effect=capture_save), \
         patch("agents.agent_07_reviewer.log_decision"), \
         patch("agents.agent_07_reviewer.write_estimate"):
        with pytest.raises(ReviewerFailError):
            review_estimate("ORD-201")

    assert "price" in flag_reason_captured.get("reason", "").lower()


# ── UT-05-10  log_decision called with agent_name on success ─────────────────

def test_log_decision_called_on_success():
    with patch("agents.agent_07_reviewer.get_order_by_id", return_value=_DB_ROW), \
         patch("agents.agent_07_reviewer.get_order", return_value=_FTF_ORDER), \
         patch("agents.agent_07_reviewer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_07_reviewer.save_order_state"), \
         patch("agents.agent_07_reviewer.log_decision") as mock_log:
        review_estimate("ORD-201")

    mock_log.assert_called_once()
    assert mock_log.call_args[1]["agent_name"] == AGENT_NAME
    assert mock_log.call_args[1]["decision"] == "reviewed"
