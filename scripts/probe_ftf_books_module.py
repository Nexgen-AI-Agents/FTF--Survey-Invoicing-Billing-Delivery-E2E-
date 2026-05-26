"""
Probe /books/ module to find the AR/Unpaid export URL.

Usage:
    python scripts/probe_ftf_books_module.py
"""

import re
import sys
import httpx

import os as _os
BASE = _os.getenv("FTF_BOOKS_BASE_URL", "https://stage.fieldtofinish.jobs")
LOGIN_URL = f"{BASE}/admin/login"
CREDS = {"user": _os.getenv("FTF_BOOKS_USER", ""), "password": _os.getenv("FTF_BOOKS_PASSWORD", "")}
AJAX = {"X-Requested-With": "XMLHttpRequest"}
XLSX_MAGIC = b"PK\x03\x04"

BOOKS_PATHS = [
    "/books/",
    "/books",
    "/books/unpaid",
    "/books/ar",
    "/books/export",
    "/books/unpaid-export",
    "/books/ar-export",
    "/books/download",
    "/books/report",
    "/books/invoices",
    "/books/invoices/unpaid",
    "/books/invoices/export",
    "/books/accounts-receivable",
]

KEYWORDS = re.compile(
    r"(unpaid|invoice|ar[_\-/]|export|download|report|book|account.receiv|receiv)",
    re.IGNORECASE,
)
ROUTE_RE = re.compile(r'["\'/](books/[a-z0-9_\-/]+)["\'/]', re.IGNORECASE)


def main() -> None:
    client = httpx.Client(follow_redirects=True, timeout=30.0)

    r = client.post(LOGIN_URL, data=CREDS, headers=AJAX)
    if r.status_code not in (200, 302):
        print(f"Login failed: {r.status_code}")
        sys.exit(1)
    print("Login OK\n")

    # Probe all books paths
    print(f"{'URL':<50}  Status  {'Content-Type':<35}")
    print("-" * 90)
    html_pages = []
    for path in BOOKS_PATHS:
        url = BASE + path
        resp = client.get(url)
        ct = resp.headers.get("content-type", "")
        body = resp.content[:4]
        note = "*** XLSX ***" if body == XLSX_MAGIC else ""
        print(f"{url:<50}  {resp.status_code:>6}  {ct:<35}  {note}")
        if resp.status_code == 200 and "html" in ct:
            html_pages.append((path, resp.text))

    # Crawl HTML pages for links and keywords
    for path, html in html_pages:
        print(f"\n=== Links on {path} ===")
        for i, line in enumerate(html.splitlines(), 1):
            if KEYWORDS.search(line):
                print(f"  L{i:4}: {line.strip()[:120]}")
        routes = ROUTE_RE.findall(html)
        for rt in sorted(set(routes)):
            print(f"  ROUTE: /{rt}")

    client.close()


if __name__ == "__main__":
    main()
