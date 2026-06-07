"""Direct MySQL connection to FTF stage DB.

Used by A1 (flag hunter) to find invoice_needed orders without the FTF REST API.
All other order data (details, history, invoice creation) still uses ftf_client.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from datetime import datetime, timedelta

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


def get_invoice_needed_orders() -> list[dict]:
    """Return ALL orders with ng_invoice_needed = 1 from FTF stage MySQL DB.

    No LIMIT — every flagged order is returned so none are permanently invisible.
    A1 flag hunter deduplicates via order_exists() and caps new intake per run
    to avoid flooding the Excel state on a sudden backlog.

    Returns newest first (ORDER BY ng_id DESC) so recent orders get priority.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ng_id, ng_order, ng_client_name, ng_email,
                          ng_property_address, ng_service_requested,
                          ng_status, ng_property_county, ng_notes
                   FROM ng_orders
                   WHERE ng_invoice_needed = 1
                     AND ng_status != 0
                   ORDER BY ng_id DESC"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        order_id = str(row.get("ng_order") or row.get("ng_id") or "")
        if not order_id:
            continue
        results.append({
            "order_id":        order_id,
            "service_type":    row.get("ng_service_requested") or "",
            "customer_email":  row.get("ng_email") or "",
            "customer_name":   row.get("ng_client_name") or "",
            "property_address": row.get("ng_property_address") or "",
            "county":          row.get("ng_property_county") or "",
            "notes":           (row.get("ng_notes") or "").strip(),
        })

    logger.info("get_invoice_needed_orders: %d orders from MySQL", len(results))
    return results


def get_order_details(order_id: str) -> dict:
    """Fetch ng_orders fields needed by A3 for pre-flight validation and pricing."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ng_company_id, ng_unit_number, ng_legal_description,
                          ng_property_address, ng_property_county, ng_folio_mls_number,
                          ng_service_requested, ng_flood, ng_commercial, ng_size,
                          ng_certifications, ng_lat, ng_long,
                          ng_status, ng_status_desc
                   FROM ng_orders WHERE ng_order = %s LIMIT 1""",
                (order_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return row or {}


def get_company_info(company_id: int) -> dict:
    """Fetch ng_company record for pricing and client tier classification.

    company_type: 1 = individual, 0 = company/title
    ng_rate: negotiated survey base rate — PRIMARY pricing source (0 if unset)
    """
    if not company_id:
        return {}
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ng_company_name, company_type, ng_rate,
                          ng_dtentered, ng_order_count
                   FROM ng_company WHERE ng_company_id = %s LIMIT 1""",
                (company_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        logger.warning("get_company_info: no record for company_id=%s", company_id)
        return {}
    return {
        "company_name":   row.get("ng_company_name") or "",
        "company_type":   int(row.get("company_type") or 0),
        "ng_rate":        float(row.get("ng_rate") or 0.0),
        "ng_dtentered":   row.get("ng_dtentered"),
        "ng_order_count": int(row.get("ng_order_count") or 0),
    }


def find_duplicate_orders(
    order_id: str,
    lat: str,
    lng: str,
    folio_mls: str,
) -> list[dict]:
    """Duplicate detection using Latitude, Longitude, and Folio/MLS number.

    Checks within a 6-month window. Either signal alone flags a duplicate —
    flagged in the approval spreadsheet; human decides.

    Lat/lng match uses 0.0001° tolerance (~11 m) and skips zero coordinates.
    Human approver decides via Excel spreadsheet — never auto-rejects.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

            # Build WHERE clause dynamically based on which signals are available
            conditions = ["ng_order != %s", "ng_timestamp >= %s"]
            params: list = [order_id, cutoff]
            signal_parts = []

            lat_val  = float(lat)  if lat  else 0.0
            lng_val  = float(lng)  if lng  else 0.0
            has_coords = lat_val != 0.0 and lng_val != 0.0

            if has_coords:
                signal_parts.append(
                    "(ABS(CAST(ng_lat AS DECIMAL(12,6)) - %s) < 0.0001 "
                    "AND ABS(CAST(ng_long AS DECIMAL(12,6)) - %s) < 0.0001 "
                    "AND CAST(ng_lat AS DECIMAL(12,6)) != 0)"
                )
                params += [lat_val, lng_val]

            folio_clean = (folio_mls or "").strip()
            if folio_clean:
                signal_parts.append("ng_folio_mls_number = %s")
                params.append(folio_clean)

            if not signal_parts:
                return []  # nothing to match on

            conditions.append(f"({' OR '.join(signal_parts)})")
            sql = (
                "SELECT ng_order, ng_property_address, ng_property_county, "
                "ng_folio_mls_number, ng_service_requested, ng_lat, ng_long, ng_timestamp "
                "FROM ng_orders WHERE " + " AND ".join(conditions) + " LIMIT 10"
            )
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    candidates = []
    for row in rows:
        reasons = []
        row_lat    = row.get("ng_lat") or "0"
        row_lng    = row.get("ng_long") or "0"
        row_folio  = (row.get("ng_folio_mls_number") or "").strip()

        if has_coords and float(row_lat) != 0.0:
            if abs(float(row_lat) - lat_val) < 0.0001 and abs(float(row_lng) - lng_val) < 0.0001:
                reasons.append(f"same location ({row_lat}, {row_lng})")
        if folio_clean and row_folio and row_folio == folio_clean:
            reasons.append(f"same Folio/MLS ({row_folio})")

        if reasons:
            candidates.append({
                "order_id":      str(row.get("ng_order", "")),
                "address":       row.get("ng_property_address", ""),
                "county":        row.get("ng_property_county", ""),
                "service":       row.get("ng_service_requested", ""),
                "match_reasons": reasons,
                "timestamp":     str(row.get("ng_timestamp", "")),
            })

    if candidates:
        logger.info("find_duplicate_orders: %d candidate(s) for order=%s", len(candidates), order_id)
    return candidates


def get_county_urls(county: str) -> dict:
    """Return url_appr and url_aerial for the given county from county_url_list.

    Matching is case-insensitive. Strips " County" suffix from input if present
    so callers can pass either "Broward" or "Broward County".
    Returns empty dict if no match found.
    """
    county_clean = county.strip()
    # Try exact match first, then with/without " County" suffix
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT url_appr, url_aerial
                FROM county_url_list
                WHERE LOWER(county_name) = LOWER(%s)
                   OR LOWER(county_name) = LOWER(CONCAT(%s, ' County'))
                   OR LOWER(REPLACE(county_name, ' County', '')) = LOWER(REPLACE(%s, ' County', ''))
                LIMIT 1
                """,
                (county_clean, county_clean, county_clean),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        logger.warning("get_county_urls: no URL found for county=%s", county)
        return {}
    return {
        "url_appr":   row.get("url_appr") or "",
        "url_aerial": row.get("url_aerial") or "",
    }
