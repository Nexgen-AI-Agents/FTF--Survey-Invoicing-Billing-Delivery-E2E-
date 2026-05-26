"""
Probe staging FTF for AR data — two paths:
  1. REST API  (Bearer token)  — check if /invoices or similar returns unpaid data
  2. Books session login       — get excel.js, find download_excel() URL

Usage:
    python scripts/probe_stage_ar.py
"""

import re
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

import httpx
from config.settings import FTF_API_BASE_URL, FTF_API_KEY

STAGE_BASE   = os.getenv("FTF_BOOKS_BASE_URL", "https://stage.fieldtofinish.jobs")
BOOKS_BASE   = STAGE_BASE
BOOKS_LOGIN  = f"{STAGE_BASE}/admin/login"
BOOKS_CREDS  = {"user": os.getenv("FTF_BOOKS_USER", ""), "password": os.getenv("FTF_BOOKS_PASSWORD", "")}
AJAX         = {"X-Requested-With": "XMLHttpRequest"}
XLSX_MAGIC   = b"PK\x03\x04"

API_HEADERS = {
    "Authorization": f"Bearer {FTF_API_KEY}",
    "Content-Type": "application/json",
}

# REST API endpoints to probe for AR data
API_AR_PATHS = [
    "/invoices",
    "/invoices/unpaid",
    "/invoices?status=unpaid",
    "/invoices?paid=false",
    "/books",
    "/books/unpaid",
    "/ar",
    "/ar/unpaid",
    "/payments/unpaid",
    "/payments",
]


def probe_api(client: httpx.Client) -> None:
    print("=" * 60)
    print(f"API BASE: {FTF_API_BASE_URL}")
    print("=" * 60)
    for path in API_AR_PATHS:
        url = FTF_API_BASE_URL + path if path.startswith("/") else f"{FTF_API_BASE_URL}/{path}"
        try:
            r = client.get(url, headers=API_HEADERS, timeout=15.0)
            ct = r.headers.get("content-type", "")
            snippet = r.text[:120].replace("\n", " ") if "json" in ct or "text" in ct else f"[binary {len(r.content)}B]"
            print(f"  {r.status_code}  {path:<35}  {snippet}")
        except Exception as e:
            print(f"  ERR  {path:<35}  {e}")


def probe_books(client: httpx.Client) -> None:
    print("\n" + "=" * 60)
    print(f"BOOKS LOGIN: {BOOKS_LOGIN}")
    print("=" * 60)
    r = client.post(BOOKS_LOGIN, data=BOOKS_CREDS, headers=AJAX)
    print(f"  Login status: {r.status_code}")
    if r.status_code not in (200, 302):
        print(f"  Login failed — body: {r.text[:200]}")
        return
    print("  Login OK")

    # Fetch /books/ to see if it works on staging
    books_home = client.get(f"{BOOKS_BASE}/books/")
    print(f"  /books/ status: {books_home.status_code}")

    # Fetch excel.js
    excel_js = client.get(f"{BOOKS_BASE}/books/static/js/excel.js")
    print(f"  excel.js status: {excel_js.status_code}  len={len(excel_js.text)}")
    if excel_js.status_code == 200:
        print("\n  --- excel.js contents ---")
        print(excel_js.text[:3000])

    # Probe download paths
    download_paths = [
        "/books/download",
        "/books/download_excel",
        "/books/download/excel",
        "/books/export",
        "/books/export/excel",
        "/books/export_excel",
        "/books/unpaid/download",
        "/books/unpaid/export",
    ]
    print("\n  Download path probes:")
    for path in download_paths:
        url = BOOKS_BASE + path
        r2 = client.get(url)
        ct = r2.headers.get("content-type", "")
        note = "*** XLSX ***" if r2.content[:4] == XLSX_MAGIC else ""
        print(f"    {r2.status_code}  {path:<35}  {ct[:40]}  {note}")

    # Try POST to download
    print("\n  POST download probes (filter=unpaid):")
    post_paths = [
        "/books/download",
        "/books/export",
        "/books/download_excel",
    ]
    for path in post_paths:
        url = BOOKS_BASE + path
        r3 = client.post(url, data={"filter": "unpaid", "all_data": "1"})
        ct = r3.headers.get("content-type", "")
        note = "*** XLSX ***" if r3.content[:4] == XLSX_MAGIC else ""
        print(f"    {r3.status_code}  POST {path:<30}  {ct[:40]}  {note}")


def main() -> None:
    client = httpx.Client(follow_redirects=True, timeout=30.0)
    probe_api(client)
    probe_books(client)
    client.close()


if __name__ == "__main__":
    main()
