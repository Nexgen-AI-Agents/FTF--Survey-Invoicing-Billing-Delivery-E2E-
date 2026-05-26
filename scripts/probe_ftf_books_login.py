"""
Probe FTF Books admin login and discover the AR/Unpaid export URL.

Usage:
    python scripts/probe_ftf_books_login.py

Prints:
    - Login result (success/fail)
    - Content-Type and first 200 bytes of each probed URL
    - Which URL returns xlsx content
"""

import os
import sys
import time
import httpx

ADMIN_BASE = os.getenv("FTF_BOOKS_BASE_URL", "https://stage.fieldtofinish.jobs")
LOGIN_URL  = f"{ADMIN_BASE}/admin/login"
CREDS      = {"user": os.getenv("FTF_BOOKS_USER", ""), "password": os.getenv("FTF_BOOKS_PASSWORD", "")}
HEADERS    = {"X-Requested-With": "XMLHttpRequest"}

CANDIDATE_PATHS = [
    "/admin/books/export",
    "/admin/books/ar-export",
    "/admin/books/unpaid",
    "/admin/books/unpaid-export",
    "/admin/books/report",
    "/admin/books/download",
    "/admin/books",
    "/admin/reports/ar",
    "/admin/reports/unpaid",
    "/admin/export/books",
    "/admin/export/ar",
    "/admin/invoices/export",
    "/admin/accounts-receivable/export",
    "/admin/ar/export",
    "/admin/ar/download",
    "/admin/ar",
    "/admin/finances/export",
    "/admin/finances/ar",
]

XLSX_MAGIC = b"PK\x03\x04"  # ZIP/XLSX magic bytes


def main() -> None:
    client = httpx.Client(follow_redirects=True, timeout=30.0)

    print(f"Logging in -> {LOGIN_URL}")
    r = client.post(LOGIN_URL, data=CREDS, headers=HEADERS)
    print(f"  Status:  {r.status_code}")
    print(f"  Cookies: {dict(r.cookies)}")

    if r.status_code not in (200, 302):
        print(f"  Body:    {r.text[:300]}")
        print("LOGIN FAILED — stopping.")
        sys.exit(1)

    print("  LOGIN OK\n")
    print(f"{'URL':<45}  {'Status':>6}  {'Content-Type':<35}  Notes")
    print("-" * 110)

    xlsx_hits = []
    for path in CANDIDATE_PATHS:
        url = ADMIN_BASE + path
        try:
            resp = client.get(url, headers=HEADERS, timeout=20.0)
            ct   = resp.headers.get("content-type", "")
            body = resp.content[:8]
            is_xlsx = body[:4] == XLSX_MAGIC
            note = "*** XLSX ***" if is_xlsx else ""
            if is_xlsx:
                xlsx_hits.append(url)
            print(f"{url:<45}  {resp.status_code:>6}  {ct:<35}  {note}")
        except Exception as exc:
            print(f"{url:<45}   ERROR  {exc}")
        time.sleep(0.3)

    print()
    if xlsx_hits:
        print("FOUND XLSX at:")
        for u in xlsx_hits:
            print(f"  {u}")
    else:
        print("No xlsx found at any candidate path.")
        print("Try inspecting browser network tab: log in → Books → export → copy request URL.")

    client.close()


if __name__ == "__main__":
    main()
