"""Agent A2 — Data Collector (Invoice Pipeline)

For each order queued by A1 (status=invoice_needed), this agent collects
all available information from 4 sources:

  1. FTF API               — order details, client details, service type, property info
  2. Email inbox           — nesa@nexgenlogix.com: emails matching this order (90 days)
  3. County property appr  — legal description, lot size, sqft, parcel ID
  4. Google aerial image   — satellite view analyzed by Claude vision

If key fields (client_email, services_requested) cannot be determined with
at least MEDIUM confidence, the order is set to status='details_missing' and
a Teams channel alert is posted: "Client details not found for order #ORDER".

Otherwise status → data_collected (proceed to A3).

Status flow: invoice_needed → data_collected | details_missing
"""

import base64
import json
import os
import re
import sys
import imaplib
import email as email_lib
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from typing import Optional

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from config.settings import IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD, GOOGLE_MAPS_API_KEY
from config.models import CLASSIFIER_MODEL, VISION_MODEL
from core.claude_client import call as llm_call, call_with_image
from core.excel_db import get_orders_by_status, get_order_by_id, save_order_state, log_decision
from core.exceptions import AgentError
from core.ftf_client import get_order, get_customer
from core.ftf_mysql import get_county_urls
from core.logger import get_logger

AGENT_NAME = "agent_a2_data_collector"
log = get_logger(AGENT_NAME)

LOOKBACK_DAYS = 90


def _decode_header_field(value: str) -> str:
    parts = decode_header(value or "")
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _extract_email_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")
    return body.strip()


def _text_matches_order(text: str, property_address: str, client_name: str, order_id: str) -> bool:
    lower = text.lower()
    if property_address and len(property_address) > 5:
        addr_parts = property_address.lower().split()
        if len(addr_parts) >= 2 and addr_parts[0].isdigit():
            if f"{addr_parts[0]} {addr_parts[1]}" in lower:
                return True
        if property_address.lower() in lower:
            return True
    if client_name and len(client_name) > 3:
        if client_name.lower() in lower:
            return True
    if order_id and order_id in text:
        return True
    return False


def _fetch_matching_emails(
    property_address: str,
    client_name: str,
    order_id: str,
) -> list[dict]:
    """Search nesa@nexgenlogix.com inbox for emails related to this order."""
    if not IMAP_USER or not IMAP_PASSWORD:
        log.warning("IMAP not configured — skipping email search")
        return []

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("INBOX")

        since_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
        _, data = mail.search(None, f"SINCE {since_date}")
        email_ids = data[0].split()

        matching = []
        for eid in email_ids:
            try:
                _, msg_data = mail.fetch(eid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                subject  = _decode_header_field(msg.get("Subject", ""))
                from_addr = _decode_header_field(msg.get("From", ""))
                body     = _extract_email_body(msg)
                combined = f"{subject} {body}"

                if _text_matches_order(combined, property_address, client_name, order_id):
                    matching.append({
                        "from":    from_addr,
                        "subject": subject,
                        "body":    body[:3000],
                        "date":    msg.get("Date", ""),
                    })
            except Exception as exc:
                log.debug("email fetch error eid=%s: %s", eid, exc)

        mail.close()
        mail.logout()
        log.info("email search complete matches=%d", len(matching))
        return matching

    except imaplib.IMAP4.error as exc:
        log.warning("IMAP connection failed: %s", exc)
        return []
    except Exception as exc:
        log.warning("email search failed: %s", exc)
        return []


_APPRAISER_TIMEOUT = 15
_AERIAL_ZOOM       = 19
_AERIAL_SIZE       = "640x640"
_GMAPS_STATIC_URL  = "https://maps.googleapis.com/maps/api/staticmap"
_HTTP_HEADERS      = {"User-Agent": "Mozilla/5.0 (compatible; NexGenSurveyBot/1.0)"}


def _fetch_property_appraiser_data(address: str, county: str) -> dict:
    """Fetch legal description, lot size, and sqft from the county property appraiser site.

    Uses url_appr from county_url_list. Tries address-based search paths on the
    base domain since stored URLs expect a parcel ID suffix. Falls back gracefully
    on any failure — never blocks invoice generation.
    """
    empty: dict = {
        "legal_description": None,
        "lot_size":          None,
        "structure_sqft":    None,
        "parcel_id":         None,
        "year_built":        None,
        "notes":             None,
        "source_url":        None,
        "confidence":        "LOW",
        "error":             None,
    }

    if not county:
        empty["error"] = "No county provided"
        return empty

    try:
        county_urls = get_county_urls(county)
    except Exception as exc:
        empty["error"] = f"County URL DB lookup failed: {exc}"
        return empty

    appr_url = county_urls.get("url_appr", "")
    if not appr_url:
        empty["error"] = f"No appraiser URL in DB for county: {county}"
        return empty

    empty["source_url"] = appr_url

    # Extract base domain — stored URL needs a parcel ID appended, so we search by address instead
    try:
        parsed     = urllib.parse.urlparse(appr_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        base_domain = appr_url

    encoded_addr = urllib.parse.quote(address)
    urls_to_try  = [
        f"{base_domain}/search?address={encoded_addr}",
        f"{base_domain}/search?q={encoded_addr}",
        f"{base_domain}/propertysearch?address={encoded_addr}",
        f"{base_domain}/?address={encoded_addr}",
        base_domain,
    ]

    html_content = None
    working_url  = None
    for url in urls_to_try:
        try:
            resp = httpx.get(url, timeout=_APPRAISER_TIMEOUT,
                             follow_redirects=True, headers=_HTTP_HEADERS)
            if resp.status_code == 200 and len(resp.text) > 500:
                html_content = resp.text
                working_url  = url
                break
        except Exception:
            continue

    if not html_content:
        log.warning("appraiser site unreachable county=%s url=%s", county, appr_url)
        empty["error"] = f"Appraiser site unreachable (possible broken URL): {appr_url}"
        return empty

    # Strip to readable text for Claude
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        page_text = soup.get_text(separator=" ", strip=True)[:4000]
    except Exception:
        page_text = html_content[:4000]

    prompt = f"""Extract property data from this county property appraiser page.

Property Address: {address}
County: {county}
Page: {working_url}

Page text:
{page_text}

Return ONLY valid JSON:
{{
  "legal_description": "full legal description or null",
  "lot_size": "lot size with units (e.g. 0.23 acres, 10000 sq ft) or null",
  "structure_sqft": living area sqft as integer or null,
  "parcel_id": "folio/parcel/account number or null",
  "year_built": year as integer or null,
  "notes": "any other property details relevant to a survey"
}}"""

    try:
        raw = llm_call(
            model=CLASSIFIER_MODEL,
            system="You extract property data from county appraiser websites. Return only valid JSON.",
            user=prompt,
            max_tokens=400,
        ).strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        extracted              = json.loads(raw)
        extracted["source_url"]  = working_url
        extracted["error"]       = None
        extracted["confidence"]  = "MEDIUM" if extracted.get("legal_description") else "LOW"
        return extracted
    except Exception as exc:
        log.warning("appraiser extraction failed county=%s: %s", county, exc)
        empty["error"] = f"Extraction failed: {exc}"
        return empty


def _fetch_aerial_image_b64(address: str) -> str | None:
    """Fetch Google Maps Static API satellite image for the address.

    Returns base64-encoded PNG string. Returns None if API key missing or request fails.
    """
    if not GOOGLE_MAPS_API_KEY:
        log.debug("GOOGLE_MAPS_API_KEY not configured — skipping aerial image")
        return None

    params = {
        "center":  address,
        "zoom":    str(_AERIAL_ZOOM),
        "size":    _AERIAL_SIZE,
        "maptype": "satellite",
        "key":     GOOGLE_MAPS_API_KEY,
    }
    url = f"{_GMAPS_STATIC_URL}?{urllib.parse.urlencode(params)}"

    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            log.warning("aerial image HTTP %d for address=%s", resp.status_code, address)
            return None
        return base64.b64encode(resp.content).decode("utf-8")
    except Exception as exc:
        log.warning("aerial image fetch failed address=%s: %s", address, exc)
        return None


def _analyze_aerial_image(image_b64: str, address: str) -> dict:
    """Use Claude vision to analyze the satellite image of the property."""
    prompt = f"""Analyze this satellite/aerial image for a land survey order.

Property Address: {address}

Return ONLY valid JSON:
{{
  "lot_shape": "rectangular|irregular|corner|flag|other",
  "estimated_lot_size": "rough estimate with units (e.g. ~0.25 acres) or null",
  "main_structure_footprint_sqft": estimated sqft of main building footprint as integer or null,
  "visible_structures": ["list: main house, detached garage, shed, pool, etc."],
  "driveway_count": integer or null,
  "pool_visible": true or false,
  "apparent_encroachments": "description or null",
  "access_type": "street|alley|shared|unclear",
  "site_notes": "observations relevant to a boundary or elevation survey or null",
  "confidence": "HIGH|MEDIUM|LOW"
}}"""

    try:
        raw = call_with_image(
            model=VISION_MODEL,
            system="You analyze property aerial images for a land surveying company. Return only valid JSON.",
            user_text=prompt,
            image_b64=image_b64,
            media_type="image/png",
            max_tokens=500,
        ).strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        return json.loads(raw)
    except Exception as exc:
        log.warning("aerial analysis failed: %s", exc)
        return {
            "lot_shape": None,
            "estimated_lot_size": None,
            "main_structure_footprint_sqft": None,
            "visible_structures": [],
            "driveway_count": None,
            "pool_visible": None,
            "apparent_encroachments": None,
            "access_type": None,
            "site_notes": None,
            "confidence": "LOW",
        }


def _ai_extract_order_packet(
    ftf_order: dict,
    ftf_customer: dict,
    emails: list[dict],
    appraiser_data: dict | None = None,
    aerial_analysis: dict | None = None,
) -> dict:
    """Use Claude to synthesize FTF data and emails into a structured order packet."""
    email_block = ""
    for i, em in enumerate(emails[:5], 1):
        email_block += f"\n--- Email {i} from {em['from']} ({em['date']}) ---\n"
        email_block += f"Subject: {em['subject']}\n{em['body'][:1000]}\n"

    appraiser_block = ""
    if appraiser_data and appraiser_data.get("confidence") != "LOW":
        appraiser_block = f"""
COUNTY PROPERTY APPRAISER DATA (confidence={appraiser_data.get('confidence')}):
  Legal description: {appraiser_data.get('legal_description')}
  Lot size: {appraiser_data.get('lot_size')}
  Structure sqft: {appraiser_data.get('structure_sqft')}
  Parcel ID: {appraiser_data.get('parcel_id')}
  Year built: {appraiser_data.get('year_built')}
  Notes: {appraiser_data.get('notes')}"""
    elif appraiser_data and appraiser_data.get("error"):
        appraiser_block = f"\nCOUNTY PROPERTY APPRAISER: unavailable — {appraiser_data.get('error')}"

    aerial_block = ""
    if aerial_analysis and aerial_analysis.get("confidence") != "LOW":
        aerial_block = f"""
AERIAL IMAGE ANALYSIS (confidence={aerial_analysis.get('confidence')}):
  Lot shape: {aerial_analysis.get('lot_shape')}
  Estimated lot size: {aerial_analysis.get('estimated_lot_size')}
  Main structure footprint: {aerial_analysis.get('main_structure_footprint_sqft')} sqft
  Visible structures: {', '.join(aerial_analysis.get('visible_structures') or [])}
  Pool visible: {aerial_analysis.get('pool_visible')}
  Driveway count: {aerial_analysis.get('driveway_count')}
  Encroachments: {aerial_analysis.get('apparent_encroachments')}
  Site notes: {aerial_analysis.get('site_notes')}"""

    prompt = f"""You are extracting invoice details for a land surveying order at NexGen Surveying.

FTF ORDER DATA:
{json.dumps(ftf_order, indent=2, default=str)[:2000]}

FTF CUSTOMER DATA:
{json.dumps(ftf_customer, indent=2, default=str)[:1000]}

MATCHING EMAILS ({len(emails)} found):
{email_block or "(none found)"}
{appraiser_block}
{aerial_block}

Extract the following fields. Rate confidence:
  HIGH   = explicitly stated in data source
  MEDIUM = inferred from context
  LOW    = missing or unclear — needs human input

Return ONLY valid JSON, no markdown:
{{
  "client_name": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "client_email": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "property_address": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "property_county": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "services_requested": {{"value": ["service1", "service2"], "confidence": "HIGH|MEDIUM|LOW", "notes": "..."}},
  "special_requirements": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "lot_size": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "legal_description": {{"value": "...", "confidence": "HIGH|MEDIUM|LOW"}},
  "structure_sqft": {{"value": null, "confidence": "HIGH|MEDIUM|LOW"}},
  "property_features": {{"value": {{}}, "confidence": "HIGH|MEDIUM|LOW", "notes": "pool, shed, driveways, visible structures"}},
  "client_tier": {{"value": "residential|b2b|unknown", "confidence": "HIGH|MEDIUM|LOW"}},
  "urgency": {{"value": "normal|rush|unknown", "confidence": "HIGH|MEDIUM|LOW"}},
  "source_of_truth": "ftf_only|email_primary|appraiser|aerial|mixed",
  "gaps": ["list of information that is missing and needs human input"],
  "summary": "one sentence describing this order"
}}"""

    try:
        result_str = llm_call(
            model=CLASSIFIER_MODEL,
            system="You are an invoice data extraction assistant for a land surveying company. Return only valid JSON.",
            user=prompt,
            max_tokens=800,
        ).strip()

        if result_str.startswith("```"):
            result_str = re.sub(r"^```[a-z]*\n?", "", result_str).rstrip("`").strip()

        return json.loads(result_str)

    except Exception as exc:
        log.warning("AI packet extraction failed: %s", exc)
        return {
            "client_name":        {"value": ftf_customer.get("name") or ftf_order.get("customer_name", ""), "confidence": "MEDIUM"},
            "client_email":       {"value": ftf_order.get("customer_email", ""), "confidence": "MEDIUM"},
            "property_address":   {"value": ftf_order.get("property_address") or ftf_order.get("address", ""), "confidence": "MEDIUM"},
            "property_county":    {"value": ftf_order.get("county") or ftf_order.get("property_county", ""), "confidence": "MEDIUM"},
            "services_requested": {"value": [ftf_order.get("service_type", "Unknown")], "confidence": "LOW", "notes": "AI extraction failed"},
            "special_requirements": {"value": "", "confidence": "LOW"},
            "lot_size":           {"value": None, "confidence": "LOW"},
            "legal_description":  {"value": None, "confidence": "LOW"},
            "structure_sqft":     {"value": None, "confidence": "LOW"},
            "property_features":  {"value": {}, "confidence": "LOW", "notes": ""},
            "client_tier":        {"value": "unknown", "confidence": "LOW"},
            "urgency":            {"value": "unknown", "confidence": "LOW"},
            "source_of_truth":    "ftf_only",
            "gaps":               ["AI extraction failed — all fields need manual review"],
            "summary":            f"Order {ftf_order.get('order_id', '')} — extraction failed",
        }


def _has_minimum_viable_data(packet: dict) -> bool:
    """Return True if we have enough data to build an invoice draft.

    Minimum required:
      - client_email present (any confidence is fine; missing = block)
      - at least one service_requested that isn't completely unknown
    """
    email_val = packet.get("client_email", {}).get("value", "")
    if not email_val:
        return False

    svcs = packet.get("services_requested", {}).get("value", [])
    if not svcs or (len(svcs) == 1 and str(svcs[0]).lower() in ("unknown", "")):
        return False

    return True


def collect_for_order(order_id: str) -> dict:
    """Run full data collection for one order. Returns the assembled order packet."""
    db_row = get_order_by_id(order_id)
    if not db_row:
        raise AgentError(f"collect_for_order: order {order_id} not in processed_orders")

    property_address = db_row.get("property_address", "")
    client_name      = db_row.get("client_name", "") or db_row.get("customer_name", "")
    # MySQL fields already fetched by A1 from ng_orders — ground truth even when FTF API is down
    _db_email   = db_row.get("customer_email", "")
    _db_service = db_row.get("service_type", "")
    _db_county  = db_row.get("county", "")

    # 1 — FTF API
    try:
        ftf_order = get_order(order_id)
    except Exception as exc:
        log.warning("FTF order fetch failed order=%s: %s", order_id, exc)
        ftf_order = {}

    ftf_order.setdefault("order_id", order_id)
    # Merge MySQL state fields into ftf_order when FTF API returned nothing.
    # An order in FTF always has at minimum email + service — never block on API failure alone.
    if not ftf_order.get("customer_email"):
        ftf_order["customer_email"] = _db_email
    if not ftf_order.get("service_type"):
        ftf_order["service_type"] = _db_service
    if not ftf_order.get("county") and not ftf_order.get("property_county"):
        ftf_order["county"] = _db_county
    if not ftf_order.get("property_address") and not ftf_order.get("address"):
        ftf_order["property_address"] = property_address
    if not ftf_order.get("customer_name") and not ftf_order.get("client_name"):
        ftf_order["customer_name"] = client_name

    if not property_address:
        property_address = str(
            ftf_order.get("property_address") or
            ftf_order.get("address") or
            ftf_order.get("site_address") or ""
        )
    if not client_name:
        client_name = str(ftf_order.get("customer_name") or ftf_order.get("client_name") or "")

    customer_id = str(ftf_order.get("customer_id") or ftf_order.get("client_id") or "")
    try:
        ftf_customer = get_customer(customer_id) if customer_id else {}
    except Exception:
        ftf_customer = {}

    # 2 — Email inbox
    emails = _fetch_matching_emails(property_address, client_name, order_id)

    # 3 — County property appraiser (legal description, lot size, sqft)
    county = str(ftf_order.get("county") or ftf_order.get("property_county") or "")
    appraiser_data = _fetch_property_appraiser_data(property_address, county)
    log.info("appraiser data order=%s confidence=%s", order_id, appraiser_data.get("confidence"))

    # 4 — Google aerial image + Claude vision analysis
    aerial_analysis: dict = {}
    if property_address:
        image_b64 = _fetch_aerial_image_b64(property_address)
        if image_b64:
            aerial_analysis = _analyze_aerial_image(image_b64, property_address)
            log.info("aerial analysis order=%s confidence=%s", order_id, aerial_analysis.get("confidence"))
        else:
            log.debug("aerial image unavailable order=%s", order_id)

    # 5 — AI synthesis (all sources combined)
    packet = _ai_extract_order_packet(ftf_order, ftf_customer, emails,
                                      appraiser_data=appraiser_data,
                                      aerial_analysis=aerial_analysis)

    # 6 — Check if we have enough data to proceed
    if not _has_minimum_viable_data(packet):
        save_order_state(
            order_id,
            status="details_missing",
            data_collected_at=datetime.now(timezone.utc).isoformat(),
        )
        log_decision(
            AGENT_NAME,
            decision="details_missing",
            order_id=order_id,
            reason=(
                f"Insufficient data: email_conf={packet.get('client_email', {}).get('confidence')} "
                f"services={packet.get('services_requested', {}).get('value')} "
                f"emails_found={len(emails)}"
            ),
            input_summary=f"property={property_address[:60]} client={client_name[:40]}",
            output_summary="status → details_missing",
            model_used=CLASSIFIER_MODEL,
        )
        log.warning("details_missing order=%s emails=%d", order_id, len(emails))
        return packet

    # 7 — Save collected data
    data_sources = {
        "ftf_order":       ftf_order,
        "ftf_customer":    ftf_customer,
        "emails_found":    len(emails),
        "email_snippets":  [{"from": e["from"], "subject": e["subject"], "date": e["date"]} for e in emails],
        "appraiser_data":  appraiser_data,
        "aerial_analysis": aerial_analysis,
        "packet":          packet,
    }

    save_order_state(
        order_id,
        status="data_collected",
        invoice_draft=None,
        data_sources=json.dumps(data_sources, default=str),
        client_name=str(packet.get("client_name", {}).get("value") or client_name),
        property_address=str(packet.get("property_address", {}).get("value") or property_address),
        data_collected_at=datetime.now(timezone.utc).isoformat(),
    )

    log_decision(
        AGENT_NAME,
        decision="data_collected",
        order_id=order_id,
        reason=(
            f"emails={len(emails)} "
            f"source_of_truth={packet.get('source_of_truth')} "
            f"gaps={len(packet.get('gaps', []))}"
        ),
        input_summary=f"property={property_address[:60]} client={client_name[:40]}",
        output_summary=f"packet built confidence={_min_confidence(packet)}",
        model_used=CLASSIFIER_MODEL,
    )
    log.info("data collected order=%s emails=%d", order_id, len(emails))
    return packet


def _min_confidence(packet: dict) -> str:
    levels = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    min_level = 3
    for key, val in packet.items():
        if isinstance(val, dict) and "confidence" in val:
            min_level = min(min_level, levels.get(val["confidence"], 1))
    return {3: "HIGH", 2: "MEDIUM", 1: "LOW"}.get(min_level, "LOW")


MAX_PER_RUN = int(os.getenv("A2_MAX_PER_RUN", "5"))


def run() -> dict:
    """Process up to MAX_PER_RUN orders with status=invoice_needed per cron tick."""
    all_orders = get_orders_by_status("invoice_needed")
    orders     = all_orders[:MAX_PER_RUN]
    if len(all_orders) > MAX_PER_RUN:
        log.info("data_collector: %d invoice_needed orders, processing first %d", len(all_orders), MAX_PER_RUN)
    summary = {"processed": 0, "data_collected": 0, "details_missing": 0, "errors": 0}

    for db_row in orders:
        order_id = db_row["order_id"]
        try:
            packet = collect_for_order(order_id)
            if not _has_minimum_viable_data(packet):
                summary["details_missing"] += 1
            else:
                summary["data_collected"] += 1
        except Exception as exc:
            log.error("data collection failed order=%s: %s", order_id, exc)
            summary["errors"] += 1
        summary["processed"] += 1

    log.info("data_collector complete: %s", summary)
    return summary


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="A2 Data Collector — Invoice Pipeline")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--order-id", help="Collect for a specific order ID")
    args = parser.parse_args(argv)

    if args.order_id:
        packet = collect_for_order(args.order_id)
        print(json.dumps(packet, indent=2))
    elif args.run_now:
        summary = run()
        print(summary)


if __name__ == "__main__":
    main()
