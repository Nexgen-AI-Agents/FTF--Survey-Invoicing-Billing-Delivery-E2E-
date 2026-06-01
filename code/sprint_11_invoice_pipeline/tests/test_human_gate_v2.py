"""Tests for A4 Human Gate v2 — modification application logic."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))


def test_apply_modification_change_price(sample_invoice_draft):
    from agents.agent_a4_human_gate_v2 import _apply_modification
    mod = {"type": "change_price", "description": "change to 500", "new_value": 500.0, "service_name": ""}
    updated = _apply_modification(sample_invoice_draft, mod)
    assert updated["total_amount"] == 500.0
    assert updated["services"][0]["amount"] == 500.0


def test_apply_modification_add_service(sample_invoice_draft):
    from agents.agent_a4_human_gate_v2 import _apply_modification
    mod = {"type": "add_service", "description": "add elevation cert", "new_value": None, "service_name": "Elevation Certificate"}
    updated = _apply_modification(sample_invoice_draft, mod)
    names = [s["name"] for s in updated["services"]]
    assert "Elevation Certificate" in names


def test_apply_modification_remove_service(sample_invoice_draft):
    from agents.agent_a4_human_gate_v2 import _apply_modification
    mod = {"type": "remove_service", "description": "remove", "new_value": None, "service_name": "Land Survey Only"}
    updated = _apply_modification(sample_invoice_draft, mod)
    names = [s["name"] for s in updated["services"]]
    assert "Land Survey Only" not in names
    assert updated["total_amount"] == 0.0


def test_is_approved_sender():
    from agents.agent_a4_human_gate_v2 import _is_approved_sender
    assert _is_approved_sender("Robert Smith") is True
    assert _is_approved_sender("Ryan Jones")   is True
    assert _is_approved_sender("Prateek C")    is True
    assert _is_approved_sender("Jessica M")    is False
    assert _is_approved_sender("random user")  is False
    assert _is_approved_sender("ROBERT")       is True   # case-insensitive
