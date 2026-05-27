"""Tests for agent_10_ar_scanner and ftf_books_client._parse_excel."""

import io
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from core.ftf_books_client import _parse_excel


def _make_excel(rows: list[list]) -> bytes:
    """Helper — build an in-memory XLSX from a list of rows (first row = headers)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── _parse_excel unit tests ──────────────────────────────────────────────────

def test_parse_excel_returns_list_of_dicts():
    today = date.today()
    invoice_date = today - timedelta(days=65)
    raw = _make_excel([
        ["order_id", "customer_email", "invoice_amount", "invoice_date"],
        ["ORD-001", "client@test.com", 1500.00, invoice_date],
    ])
    result = _parse_excel(raw)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["order_id"] == "ORD-001"


def test_parse_excel_calculates_days_overdue():
    today = date.today()
    invoice_date = today - timedelta(days=75)
    raw = _make_excel([
        ["order_id", "customer_email", "invoice_amount", "invoice_date"],
        ["ORD-002", "a@b.com", 500.0, invoice_date],
    ])
    result = _parse_excel(raw)
    assert result[0]["days_overdue"] == 75


def test_parse_excel_skips_rows_without_order_id():
    today = date.today()
    raw = _make_excel([
        ["order_id", "customer_email", "invoice_amount", "invoice_date"],
        [None, "x@y.com", 100.0, today - timedelta(days=30)],
        ["ORD-003", "z@z.com", 200.0, today - timedelta(days=30)],
    ])
    result = _parse_excel(raw)
    assert len(result) == 1
    assert result[0]["order_id"] == "ORD-003"


def test_parse_excel_empty_sheet_returns_empty_list():
    wb = openpyxl.Workbook()
    ws = wb.active
    buf = io.BytesIO()
    wb.save(buf)
    result = _parse_excel(buf.getvalue())
    assert result == []


def test_parse_excel_handles_string_date():
    raw = _make_excel([
        ["order_id", "customer_email", "invoice_amount", "invoice_date"],
        ["ORD-004", "d@e.com", 300.0, "2026-03-01"],
    ])
    result = _parse_excel(raw)
    assert result[0]["invoice_date"] == date(2026, 3, 1)


# ── agent_10_ar_scanner integration (mocked) ─────────────────────────────────

def test_ar_scanner_run_upserts_overdue_invoices():
    today = date.today()
    mock_invoices = [
        {"order_id": "ORD-010", "customer_email": "a@test.com",
         "invoice_amount": 1000.0, "invoice_date": today - timedelta(days=70),
         "days_overdue": 70},
        {"order_id": "ORD-011", "customer_email": "b@test.com",
         "invoice_amount": 500.0,  "invoice_date": today - timedelta(days=45),
         "days_overdue": 45},
    ]

    with patch("agents.agent_10_ar_scanner.get_unpaid_invoices", return_value=mock_invoices), \
         patch("agents.agent_10_ar_scanner.upsert_ar_reminder") as mock_upsert:

        from agents.agent_10_ar_scanner import run
        result = run()

    assert result["scanned"] == 2
    assert result["tracked"] == 1
    mock_upsert.assert_called_once_with(
        order_id="ORD-010",
        customer_email="a@test.com",
        invoice_amount=1000.0,
        invoice_date=today - timedelta(days=70),
        days_overdue=70,
    )
