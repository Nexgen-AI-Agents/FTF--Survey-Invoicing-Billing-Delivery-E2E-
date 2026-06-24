"""Tests for intake_watermark + A1's 'process from today onward' gating."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from core import intake_watermark as wm


def test_load_returns_none_when_absent(tmp_path):
    assert wm.load_watermark(str(tmp_path / "nope.json")) is None


def test_save_then_load_roundtrip(tmp_path):
    f = str(tmp_path / "intake_watermark.json")
    wm.save_watermark(12345, path=f)
    assert wm.load_watermark(f) == 12345


def test_load_tolerates_garbage(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{ not json")
    assert wm.load_watermark(str(f)) is None


def test_a1_first_run_inits_watermark_and_queues_nothing(tmp_path, monkeypatch):
    """First A1 run (no watermark) records MAX(ng_id) and queues nothing."""
    from agents import agent_a1_flag_hunter as a1

    f = str(tmp_path / "intake_watermark.json")
    monkeypatch.setattr(a1, "load_watermark", lambda *a, **k: wm.load_watermark(f))
    monkeypatch.setattr(a1, "save_watermark", lambda v, *a, **k: wm.save_watermark(v, path=f))
    monkeypatch.setattr(a1, "get_max_ng_id", lambda: 50000)

    def _should_not_be_called(*a, **k):
        raise AssertionError("get_invoice_needed_orders must not run on init cycle")

    monkeypatch.setattr(a1, "get_invoice_needed_orders", _should_not_be_called)

    queued = a1.run()
    assert queued == []
    assert wm.load_watermark(f) == 50000


def test_a1_subsequent_run_filters_by_watermark(tmp_path, monkeypatch):
    """With a watermark set, A1 queries only ng_id > watermark and queues new orders."""
    from agents import agent_a1_flag_hunter as a1

    f = str(tmp_path / "intake_watermark.json")
    wm.save_watermark(50000, path=f)

    seen = {}
    monkeypatch.setattr(a1, "load_watermark", lambda *a, **k: wm.load_watermark(f))
    monkeypatch.setattr(a1, "get_invoice_needed_orders",
                        lambda min_ng_id=0: seen.update(min_ng_id=min_ng_id) or [
                            {"order_id": "60001", "service_type": "Boundary Survey",
                             "customer_email": "a@b.com", "customer_name": "X", "property_address": "1 St"},
                        ])
    monkeypatch.setattr(a1, "order_exists", lambda oid: False)
    monkeypatch.setattr(a1, "save_order_state", lambda *a, **k: None)
    monkeypatch.setattr(a1, "log_decision", lambda *a, **k: None)

    queued = a1.run()
    assert seen["min_ng_id"] == 50000   # passed the watermark as the cutoff
    assert queued == ["60001"]


def test_a1_respects_max_new_per_run(tmp_path, monkeypatch):
    from agents import agent_a1_flag_hunter as a1

    f = str(tmp_path / "intake_watermark.json")
    wm.save_watermark(1, path=f)
    many = [{"order_id": str(i), "service_type": "Boundary Survey", "customer_email": "a@b.com",
             "customer_name": "X", "property_address": "1 St"} for i in range(60001, 60050)]
    monkeypatch.setattr(a1, "load_watermark", lambda *a, **k: 1)
    monkeypatch.setattr(a1, "get_invoice_needed_orders", lambda min_ng_id=0: many)
    monkeypatch.setattr(a1, "order_exists", lambda oid: False)
    monkeypatch.setattr(a1, "save_order_state", lambda *a, **k: None)
    monkeypatch.setattr(a1, "log_decision", lambda *a, **k: None)
    monkeypatch.setattr(a1, "MAX_NEW_PER_RUN", 10)

    queued = a1.run()
    assert len(queued) == 10
