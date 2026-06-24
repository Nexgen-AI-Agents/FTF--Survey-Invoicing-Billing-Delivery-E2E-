"""intake_watermark.py — 'process orders from today onward' high-water mark.

After the June-2026 reset the pipeline must IGNORE the entire historical backlog
of invoice-flagged orders and only process orders created from the reset point
forward. ng_orders.ng_id is a monotonic auto-increment, so 'ng_id > watermark'
cleanly means 'created after the reset'.

The watermark is captured ONCE, on A1's first run after deploy (when no watermark
file exists yet): A1 reads MAX(ng_id) from the DB, stores it here, and queues
nothing that cycle (everything existing is backlog). Every later run only queues
ng_id > watermark. The file lives in data/ and is committed by CI so it persists
across runs.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from core.logger import get_logger

logger = get_logger(__name__)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
WATERMARK_PATH = os.path.join(_REPO_ROOT, "data", "intake_watermark.json")


def load_watermark(path: str = WATERMARK_PATH) -> Optional[int]:
    """Return the stored start_ng_id, or None if not yet initialized. Never raises."""
    try:
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        val = data.get("start_ng_id")
        return int(val) if val is not None else None
    except Exception as exc:
        logger.warning("load_watermark failed (treating as uninitialized): %s", exc)
        return None


def save_watermark(start_ng_id: int, path: str = WATERMARK_PATH) -> None:
    """Persist the intake watermark. Raises on write error (caller logs)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "start_ng_id": int(start_ng_id),
        "set_at": datetime.now(timezone.utc).isoformat(),
        "note": "Only ng_orders with ng_id > start_ng_id are queued (process-from-today reset).",
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info("intake watermark saved: start_ng_id=%d", start_ng_id)
