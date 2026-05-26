import pytest
from unittest.mock import patch, MagicMock

from agents.agent_06_writer import write_estimate, run, AGENT_NAME
from core.exceptions import AgentError


# ── shared fixtures ───────────────────────────────────────────────────────────

_DB_ROW_PRICED = {
    "order_id": "ORD-101",
    "status": "priced",
    "service_type": "Boundary Survey",
    "customer_email": "jane@example.com",
    "estimate_amount": 450.00,
    "is_flood_zone": False,
    "retry_count": 0,
}

_DB_ROW_APPROVED = {
    "order_id": "ORD-102",
    "status": "approved",
    "service_type": "Topographic Survey",
    "customer_email": "company@titlecorp.com",
    "estimate_amount": 750.00,
    "is_flood_zone": True,
    "retry_count": 0,
}

_FTF_ORDER_INDIVIDUAL = {
    "order_id": "ORD-101",
    "customer_name": "Jane Smith",
    "customer_email": "jane@example.com",
    "property_address": "123 Oak Street, Miami, FL 33101",
    "service_type": "Boundary Survey",
    "customer_type": "individual",
}

_FTF_ORDER_B2B = {
    "order_id": "ORD-102",
    "company_name": "Title Corp LLC",
    "customer_email": "company@titlecorp.com",
    "property_address": "3721 NE 30TH AVE, Lighthouse Point, FL 33064",
    "service_type": "Topographic Survey",
    "customer_type": "b2b",
}

_CLAUSE = "Change Order Authorization\n\nBy approving this estimate, you authorize NexGen Surveying to issue a change order if the scope or complexity of the work changes after this estimate is accepted."

_DRAFT = (
    "Dear Jane Smith,\n\nThank you for reaching out to NexGen Surveying.\n\n"
    "Property: 123 Oak Street, Miami, FL 33101\n"
    "Service: Boundary Survey\n"
    "Total: $450.00\n\n"
    + _CLAUSE
)


def _patch_writer(
    db_row=None,
    ftf_order=None,
    llm_response=_DRAFT,
    clause=_CLAUSE,
):
    """Build a consistent patch context for write_estimate tests."""
    return (
        patch("agents.agent_06_writer.get_order_by_id", return_value=db_row or _DB_ROW_PRICED),
        patch("agents.agent_06_writer.get_order", return_value=ftf_order or _FTF_ORDER_INDIVIDUAL),
        patch("agents.agent_06_writer.llm_call", return_value=llm_response),
        patch("agents.agent_06_writer._load_clause", return_value=clause),
        patch("agents.agent_06_writer._load_system_prompt", return_value="You are the estimate writer."),
        patch("agents.agent_06_writer.save_order_state"),
        patch("agents.agent_06_writer.log_decision"),
    )


# ── UT-04-01  write_estimate returns draft for priced order ──────────────────

def test_write_estimate_returns_draft_for_priced_order():
    patches = _patch_writer()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        result = write_estimate("ORD-101")

    assert result["order_id"] == "ORD-101"
    assert result["status"] == "written"
    assert isinstance(result["draft_estimate"], str)
    assert len(result["draft_estimate"]) > 0


# ── UT-04-02  write_estimate works for approved (post-human-gate) order ──────

def test_write_estimate_works_for_approved_order():
    patches = _patch_writer(db_row=_DB_ROW_APPROVED, ftf_order=_FTF_ORDER_B2B)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        result = write_estimate("ORD-102")

    assert result["status"] == "written"


# ── UT-04-03  change order clause injected into LLM user message ─────────────

def test_clause_injected_into_llm_prompt():
    with patch("agents.agent_06_writer.get_order_by_id", return_value=_DB_ROW_PRICED), \
         patch("agents.agent_06_writer.get_order", return_value=_FTF_ORDER_INDIVIDUAL), \
         patch("agents.agent_06_writer.llm_call", return_value=_DRAFT) as mock_llm, \
         patch("agents.agent_06_writer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_06_writer._load_system_prompt", return_value="sys"), \
         patch("agents.agent_06_writer.save_order_state"), \
         patch("agents.agent_06_writer.log_decision"):
        write_estimate("ORD-101")

    call_args = mock_llm.call_args
    user_msg = call_args[1]["user"] if "user" in call_args[1] else call_args[0][2]
    assert _CLAUSE in user_msg


# ── UT-04-04  DB saved with status=written + draft_estimate ──────────────────

def test_db_saved_with_written_status_and_draft():
    with patch("agents.agent_06_writer.get_order_by_id", return_value=_DB_ROW_PRICED), \
         patch("agents.agent_06_writer.get_order", return_value=_FTF_ORDER_INDIVIDUAL), \
         patch("agents.agent_06_writer.llm_call", return_value=_DRAFT), \
         patch("agents.agent_06_writer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_06_writer._load_system_prompt", return_value="sys"), \
         patch("agents.agent_06_writer.save_order_state") as mock_save, \
         patch("agents.agent_06_writer.log_decision"):
        write_estimate("ORD-101")

    mock_save.assert_called_once()
    args, kwargs = mock_save.call_args
    assert args[0] == "ORD-101"
    assert kwargs["status"] == "written"
    assert kwargs["draft_estimate"] == _DRAFT


# ── UT-04-05  log_decision called with correct agent name ────────────────────

def test_log_decision_called_with_agent_name():
    with patch("agents.agent_06_writer.get_order_by_id", return_value=_DB_ROW_PRICED), \
         patch("agents.agent_06_writer.get_order", return_value=_FTF_ORDER_INDIVIDUAL), \
         patch("agents.agent_06_writer.llm_call", return_value=_DRAFT), \
         patch("agents.agent_06_writer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_06_writer._load_system_prompt", return_value="sys"), \
         patch("agents.agent_06_writer.save_order_state"), \
         patch("agents.agent_06_writer.log_decision") as mock_log:
        write_estimate("ORD-101")

    mock_log.assert_called_once()
    assert mock_log.call_args[1]["agent_name"] == AGENT_NAME
    assert mock_log.call_args[1]["decision"] == "written"


# ── UT-04-06  zero estimate_amount raises AgentError ─────────────────────────

def test_zero_amount_raises_agent_error():
    row = {**_DB_ROW_PRICED, "estimate_amount": 0}
    with patch("agents.agent_06_writer.get_order_by_id", return_value=row):
        with pytest.raises(AgentError, match="no estimate_amount"):
            write_estimate("ORD-101")


# ── UT-04-07  order not in DB raises AgentError ──────────────────────────────

def test_order_not_found_raises_agent_error():
    with patch("agents.agent_06_writer.get_order_by_id", return_value=None):
        with pytest.raises(AgentError, match="not found"):
            write_estimate("ORD-999")


# ── UT-04-08  correction_note injected into LLM prompt on retry ──────────────

def test_correction_note_injected_into_prompt():
    correction = "Fix: price $450.00 not found in estimate"
    with patch("agents.agent_06_writer.get_order_by_id", return_value=_DB_ROW_PRICED), \
         patch("agents.agent_06_writer.get_order", return_value=_FTF_ORDER_INDIVIDUAL), \
         patch("agents.agent_06_writer.llm_call", return_value=_DRAFT) as mock_llm, \
         patch("agents.agent_06_writer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_06_writer._load_system_prompt", return_value="sys"), \
         patch("agents.agent_06_writer.save_order_state"), \
         patch("agents.agent_06_writer.log_decision"):
        write_estimate("ORD-101", correction_note=correction)

    user_msg = mock_llm.call_args[1].get("user") or mock_llm.call_args[0][2]
    assert correction in user_msg


# ── UT-04-09  individual tone selected for non-B2B customers ─────────────────

def test_individual_tone_in_prompt():
    with patch("agents.agent_06_writer.get_order_by_id", return_value=_DB_ROW_PRICED), \
         patch("agents.agent_06_writer.get_order", return_value=_FTF_ORDER_INDIVIDUAL), \
         patch("agents.agent_06_writer.llm_call", return_value=_DRAFT) as mock_llm, \
         patch("agents.agent_06_writer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_06_writer._load_system_prompt", return_value="sys"), \
         patch("agents.agent_06_writer.save_order_state"), \
         patch("agents.agent_06_writer.log_decision"):
        write_estimate("ORD-101")

    user_msg = mock_llm.call_args[1].get("user") or mock_llm.call_args[0][2]
    assert "warm and friendly" in user_msg


# ── UT-04-10  B2B tone selected for business customers ───────────────────────

def test_b2b_tone_in_prompt():
    with patch("agents.agent_06_writer.get_order_by_id", return_value=_DB_ROW_APPROVED), \
         patch("agents.agent_06_writer.get_order", return_value=_FTF_ORDER_B2B), \
         patch("agents.agent_06_writer.llm_call", return_value=_DRAFT) as mock_llm, \
         patch("agents.agent_06_writer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_06_writer._load_system_prompt", return_value="sys"), \
         patch("agents.agent_06_writer.save_order_state"), \
         patch("agents.agent_06_writer.log_decision"):
        write_estimate("ORD-102")

    user_msg = mock_llm.call_args[1].get("user") or mock_llm.call_args[0][2]
    assert "concise and professional" in user_msg


# ── UT-04-11  flood zone note injected when is_flood_zone=True ───────────────

def test_flood_zone_note_in_prompt():
    with patch("agents.agent_06_writer.get_order_by_id", return_value=_DB_ROW_APPROVED), \
         patch("agents.agent_06_writer.get_order", return_value=_FTF_ORDER_B2B), \
         patch("agents.agent_06_writer.llm_call", return_value=_DRAFT) as mock_llm, \
         patch("agents.agent_06_writer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_06_writer._load_system_prompt", return_value="sys"), \
         patch("agents.agent_06_writer.save_order_state"), \
         patch("agents.agent_06_writer.log_decision"):
        write_estimate("ORD-102")

    user_msg = mock_llm.call_args[1].get("user") or mock_llm.call_args[0][2]
    assert "Elevation Certificate" in user_msg


# ── UT-04-12  run() picks first ready-to-write order ─────────────────────────

def test_run_picks_first_ready_to_write_order():
    with patch("agents.agent_06_writer.get_ready_to_write_order",
               return_value=_DB_ROW_PRICED) as mock_get, \
         patch("agents.agent_06_writer.get_order_by_id", return_value=_DB_ROW_PRICED), \
         patch("agents.agent_06_writer.get_order", return_value=_FTF_ORDER_INDIVIDUAL), \
         patch("agents.agent_06_writer.llm_call", return_value=_DRAFT), \
         patch("agents.agent_06_writer._load_clause", return_value=_CLAUSE), \
         patch("agents.agent_06_writer._load_system_prompt", return_value="sys"), \
         patch("agents.agent_06_writer.save_order_state"), \
         patch("agents.agent_06_writer.log_decision"):
        result = run()

    mock_get.assert_called_once()
    assert result["order_id"] == "ORD-101"


# ── UT-04-13  run() returns None when no orders ready ────────────────────────

def test_run_returns_none_when_no_orders():
    with patch("agents.agent_06_writer.get_ready_to_write_order", return_value=None):
        result = run()
    assert result is None
