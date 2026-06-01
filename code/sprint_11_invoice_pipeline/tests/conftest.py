"""conftest.py — Sprint 11 Invoice Pipeline tests."""
import os
import sys
import pytest

# Ensure shared is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))


@pytest.fixture
def sample_ftf_order():
    return {
        "order_id": "TEST-001",
        "service_type": "Land Survey Only",
        "customer_email": "client@example.com",
        "customer_name": "John Smith",
        "property_address": "123 Main St, Miami FL 33101",
        "county": "Miami-Dade",
        "status": "Assigned",
        "customer_id": "CUST-99",
    }


@pytest.fixture
def sample_order_packet():
    return {
        "client_name":        {"value": "John Smith",             "confidence": "HIGH"},
        "client_email":       {"value": "client@example.com",     "confidence": "HIGH"},
        "property_address":   {"value": "123 Main St, Miami FL",  "confidence": "HIGH"},
        "property_county":    {"value": "Miami-Dade",             "confidence": "HIGH"},
        "services_requested": {"value": ["Land Survey Only"],     "confidence": "MEDIUM", "notes": "from FTF"},
        "special_requirements": {"value": "",                     "confidence": "LOW"},
        "lot_size_acres":     {"value": None,                     "confidence": "LOW"},
        "property_features":  {"value": {},                       "confidence": "LOW", "notes": ""},
        "client_tier":        {"value": "residential",            "confidence": "MEDIUM"},
        "urgency":            {"value": "normal",                 "confidence": "MEDIUM"},
        "source_of_truth":    "ftf_only",
        "gaps":               ["lot size not available"],
        "summary":            "Land Survey Only for 123 Main St",
    }


@pytest.fixture
def sample_invoice_draft():
    return {
        "services": [
            {"name": "Land Survey Only", "description": "Boundary survey of property", "amount": 450.0}
        ],
        "total_amount": 450.0,
        "invoice_notes": "",
        "questions_for_approver": [],
        "low_confidence_fields": [],
        "pricing_rationale": "Base rate for Land Survey Only",
        "ready_to_approve": True,
    }
