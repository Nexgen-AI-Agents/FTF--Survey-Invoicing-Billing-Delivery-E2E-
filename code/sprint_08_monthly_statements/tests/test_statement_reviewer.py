"""Tests for agent_16_statement_reviewer."""

import io
import os
from datetime import date
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from agents.agent_15_statement_generator import _build_excel
from agents.agent_16_statement_reviewer import _validate_excel


def _make_excel(tmp_path, orders, client="a@co.com", month=None):
    month = month or date(2026, 4, 1)
    return _build_excel(client, orders, month, str(tmp_path))


def _sample_orders(n=2, amount=500.0, paid=False):
    status = "Paid" if paid else "Unpaid"
    return [
        {
            "order_id": f"ORD-{i}", "service_type": "Survey",
            "order_date": "2026-04-10", "invoice_amount": amount,
            "payment_status": status, "billing_email": "a@co.com",
        }
        for i in range(n)
    ]


# ── _validate_excel ───────────────────────────────────────────────────────────

def test_validate_excel_passes_correct_statement(tmp_path):
    orders = _sample_orders(3, 400.0)
    path = _make_excel(tmp_path, orders)
    errors = _validate_excel(path, expected_count=3, expected_total=1200.0)
    assert errors == []


def test_validate_excel_detects_count_mismatch(tmp_path):
    orders = _sample_orders(3, 300.0)
    path = _make_excel(tmp_path, orders)
    errors = _validate_excel(path, expected_count=5, expected_total=900.0)
    assert any("count mismatch" in e.lower() for e in errors)


def test_validate_excel_missing_file_returns_error():
    errors = _validate_excel("/nonexistent/path.xlsx", expected_count=1, expected_total=100.0)
    assert any("not found" in e.lower() for e in errors)


# ── agent_16 run (mocked) ─────────────────────────────────────────────────────

def test_run_marks_valid_statement_reviewed(tmp_path):
    month = date(2026, 4, 1)
    orders = _sample_orders(2, 500.0)
    excel_path = _make_excel(tmp_path, orders)
    pdf_path   = str(tmp_path / "stmt.pdf")
    # Create dummy PDF so file-exists check passes
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 dummy")

    stmt = {
        "client_email": "a@co.com",
        "order_count": 2,
        "total_amount": 1000.0,
        "excel_path": excel_path,
        "pdf_path": pdf_path,
    }

    with patch("agents.agent_16_statement_reviewer.get_generated_statements",
               return_value=[stmt]), \
         patch("agents.agent_16_statement_reviewer.update_statement_status") as mock_update, \
         patch("agents.agent_16_statement_reviewer.log_decision"):

        from agents.agent_16_statement_reviewer import run
        result = run(statement_month=month)

    assert result["passed"] == 1
    assert result["failed"] == 0
    mock_update.assert_called_once_with("a@co.com", month, "reviewed")


def test_run_marks_failed_when_pdf_missing(tmp_path):
    month = date(2026, 4, 1)
    orders = _sample_orders(2, 500.0)
    excel_path = _make_excel(tmp_path, orders)

    stmt = {
        "client_email": "b@co.com",
        "order_count": 2,
        "total_amount": 1000.0,
        "excel_path": excel_path,
        "pdf_path": "/nonexistent/file.pdf",
    }

    with patch("agents.agent_16_statement_reviewer.get_generated_statements",
               return_value=[stmt]), \
         patch("agents.agent_16_statement_reviewer.update_statement_status") as mock_update, \
         patch("agents.agent_16_statement_reviewer.log_decision"), \
         patch("agents.agent_16_statement_reviewer.TEAMS_WEBHOOK_URL", None):

        from agents.agent_16_statement_reviewer import run
        result = run(statement_month=month)

    assert result["failed"] == 1
    assert result["passed"] == 0
    mock_update.assert_called_once_with("b@co.com", month, "failed")
