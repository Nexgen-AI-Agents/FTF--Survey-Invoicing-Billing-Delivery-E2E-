"""Direct MySQL connection to FTF stage DB.

Used by A1 (flag hunter) to find invoice_needed orders without the FTF REST API.
All other order data (details, history, invoice creation) still uses ftf_client.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

import pymysql
import pymysql.cursors

from config.settings import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
from core.logger import get_logger

logger = get_logger(__name__)


def _connect():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=30,
    )


def get_invoice_needed_orders(limit: int = 500) -> list[dict]:
    """Return orders with ng_invoice_needed = 1 from FTF stage MySQL DB.

    Maps DB columns (ng_ prefix convention) to standardized field names
    expected by A1 flag hunter.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM ng_orders WHERE ng_invoice_needed = 1 LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        order_id = (
            row.get("ng_order_id") or
            row.get("order_id") or
            str(row.get("id", ""))
        )
        if not order_id:
            continue
        results.append({
            "order_id":        str(order_id),
            "service_type":    row.get("ng_job_type") or row.get("ng_service_type") or row.get("service_type") or "",
            "customer_email":  row.get("ng_email") or row.get("customer_email") or row.get("email") or "",
            "customer_name":   row.get("ng_customer") or row.get("ng_name") or row.get("customer_name") or "",
            "property_address": row.get("ng_address") or row.get("ng_site_address") or row.get("address") or "",
        })

    logger.info("get_invoice_needed_orders: %d orders from MySQL", len(results))
    return results
