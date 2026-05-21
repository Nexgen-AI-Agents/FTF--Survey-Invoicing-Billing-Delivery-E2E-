import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Optional

from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from core.exceptions import AgentError
from core.logger import get_logger

logger = get_logger(__name__)

_VALID_ORDER_COLUMNS = {
    "status", "service_type", "customer_email", "property_lat", "property_lng",
    "is_flood_zone", "estimate_amount", "flag_reason", "retry_count",
    "classified_at", "priced_at", "written_at", "reviewed_at", "sent_at", "flagged_at",
}


@contextmanager
def _get_cursor():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def order_exists(order_id: str) -> bool:
    """Return True if any row for this order_id already exists in processed_orders."""
    with _get_cursor() as cur:
        cur.execute(
            "SELECT 1 FROM processed_orders WHERE order_id = %s LIMIT 1",
            (order_id,),
        )
        return cur.fetchone() is not None


def get_pending_order() -> Optional[dict]:
    with _get_cursor() as cur:
        cur.execute(
            "SELECT * FROM processed_orders WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
        )
        row = cur.fetchone()
        return dict(row) if row else None


def save_order_state(order_id: str, **fields) -> None:
    if not fields:
        return

    invalid = set(fields.keys()) - _VALID_ORDER_COLUMNS
    if invalid:
        raise AgentError(f"save_order_state: unknown columns {invalid}")

    set_parts = [f"{col} = %s" for col in fields.keys()]
    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)
    values = list(fields.values()) + [order_id]

    with _get_cursor() as cur:
        cur.execute(
            f"UPDATE processed_orders SET {set_clause} WHERE order_id = %s",
            values,
        )
        if cur.rowcount == 0:
            cols = ["order_id"] + list(fields.keys())
            placeholders = ", ".join(["%s"] * len(cols))
            cur.execute(
                f"INSERT INTO processed_orders ({', '.join(cols)}) VALUES ({placeholders})",
                [order_id] + list(fields.values()),
            )


def log_decision(
    agent_name: str,
    decision: str,
    order_id: Optional[str] = None,
    reason: Optional[str] = None,
    input_summary: Optional[str] = None,
    output_summary: Optional[str] = None,
    model_used: Optional[str] = None,
) -> None:
    with _get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_decision_log
                (agent_name, order_id, decision, reason, input_summary, output_summary, model_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (agent_name, order_id, decision, reason, input_summary, output_summary, model_used),
        )


def get_unprocessed_reminder() -> Optional[dict]:
    with _get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM ar_reminders
            WHERE status = 'pending'
              AND (next_reminder_date IS NULL OR next_reminder_date <= CURRENT_DATE)
            ORDER BY next_reminder_date ASC NULLS FIRST
            LIMIT 1
            """
        )
        row = cur.fetchone()
        return dict(row) if row else None
