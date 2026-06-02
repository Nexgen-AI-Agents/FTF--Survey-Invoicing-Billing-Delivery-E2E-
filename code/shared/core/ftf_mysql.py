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


def get_invoice_needed_orders(limit: int = 50) -> list[dict]:
    """Return orders with ng_invoice_needed = 1 from FTF stage MySQL DB.

    Maps DB columns (ng_ prefix convention) to standardized field names
    expected by A1 flag hunter. Returns newest first (ORDER BY ng_id DESC)
    to prioritise recent orders over the 11k+ historical backlog.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ng_id, ng_order, ng_client_name, ng_email,
                          ng_property_address, ng_service_requested,
                          ng_status, ng_property_county
                   FROM ng_orders
                   WHERE ng_invoice_needed = 1
                   ORDER BY ng_id DESC
                   LIMIT %s""",
                (limit,),
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
                          ng_certifications
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
    address: str,
    county: str,
    parcel_id: str,
    company_id: int,
    service_type: str,
) -> list[dict]:
    """Multi-signal duplicate detection within a 6-month window.

    Scoring: same address+county = 3 pts, same parcel_id = 3 pts,
             same company = 1 pt, same service type = 1 pt.
    Score >= 3 is included in results. AI and human decide — never auto-rejects.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
            svc_pattern   = f"%{service_type[:20]}%" if service_type else "%"
            parcel_guard  = parcel_id if parcel_id else "__NO_PARCEL__"
            addr_guard    = address or "__NO_ADDR__"
            county_guard  = county or "__NO_COUNTY__"
            cur.execute(
                """SELECT ng_order, ng_property_address, ng_property_county,
                          ng_folio_mls_number, ng_company_id, ng_service_requested,
                          ng_timestamp
                   FROM ng_orders
                   WHERE ng_order != %s
                     AND ng_timestamp >= %s
                     AND (
                       (ng_property_address = %s AND ng_property_county = %s)
                       OR ng_folio_mls_number = %s
                       OR (ng_company_id = %s AND ng_service_requested LIKE %s)
                     )
                   LIMIT 10""",
                (
                    order_id, cutoff,
                    addr_guard, county_guard,
                    parcel_guard,
                    company_id or 0,
                    svc_pattern,
                ),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    candidates = []
    for row in rows:
        score, reasons = 0, []
        row_addr   = row.get("ng_property_address", "")
        row_county = row.get("ng_property_county", "")
        row_parcel = row.get("ng_folio_mls_number", "")
        row_svc    = row.get("ng_service_requested", "")
        row_co     = row.get("ng_company_id")

        if address and county and row_addr == address and row_county == county:
            score += 3; reasons.append("same address+county")
        if parcel_id and row_parcel and row_parcel == parcel_id:
            score += 3; reasons.append("same parcel ID")
        if company_id and row_co == company_id:
            score += 1; reasons.append("same client")
        if service_type and service_type[:10].lower() in row_svc.lower():
            score += 1; reasons.append("same service type")

        if score >= 3:
            candidates.append({
                "order_id":      str(row.get("ng_order", "")),
                "address":       row_addr,
                "county":        row_county,
                "service":       row_svc,
                "match_score":   score,
                "match_reasons": reasons,
                "timestamp":     str(row.get("ng_timestamp", "")),
            })

    candidates.sort(key=lambda x: -x["match_score"])
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
