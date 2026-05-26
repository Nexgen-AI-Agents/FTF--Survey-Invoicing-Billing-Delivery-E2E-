"""
After login, fetch admin home and books-related pages to discover the AR export URL.
Prints all href links found on each page.

Usage:
    python scripts/probe_ftf_admin_nav.py
"""

import re
import sys
import httpx

import os as _os
ADMIN_BASE = _os.getenv("FTF_BOOKS_BASE_URL", "https://stage.fieldtofinish.jobs")
LOGIN_URL  = f"{ADMIN_BASE}/admin/login"
CREDS      = {"user": _os.getenv("FTF_BOOKS_USER", ""), "password": _os.getenv("FTF_BOOKS_PASSWORD", "")}
AJAX       = {"X-Requested-With": "XMLHttpRequest"}

# Pages to crawl for nav links
CRAWL_PAGES = [
    "/admin",
    "/admin/",
    "/admin/dashboard",
    "/admin/home",
    "/admin/index",
]

# After we find books/AR link, try these sub-paths
BOOKS_GUESSES = [
    "/admin/finances",
    "/admin/finances/unpaid",
    "/admin/billing",
    "/admin/billing/unpaid",
    "/admin/billing/ar",
    "/admin/orders",
    "/admin/orders/unpaid",
    "/admin/orders/ar",
]

XLSX_MAGIC = b"PK\x03\x04"


def extract_links(html: str) -> list[str]:
    return re.findall(r'href=["\']([^"\']+)["\']', html)


def main() -> None:
    client = httpx.Client(follow_redirects=True, timeout=30.0)

    r = client.post(LOGIN_URL, data=CREDS, headers=AJAX)
    if r.status_code not in (200, 302):
        print(f"Login failed: {r.status_code}")
        sys.exit(1)
    print(f"Login OK  (session cookie len={len(str(r.cookies))})\n")

    # Crawl admin pages for links
    all_hrefs: set[str] = set()
    for path in CRAWL_PAGES:
        url = ADMIN_BASE + path
        resp = client.get(url)
        ct = resp.headers.get("content-type", "")
        print(f"  {resp.status_code}  {url}  [{ct[:50]}]")
        if "html" in ct:
            links = extract_links(resp.text)
            for lnk in links:
                if lnk.startswith("/admin"):
                    all_hrefs.add(lnk)
            if links:
                print(f"    {len(links)} links found")

    print(f"\nAll /admin/* hrefs from home pages ({len(all_hrefs)}):")
    for h in sorted(all_hrefs):
        print(f"  {h}")

    # Probe books/billing guesses
    print("\nProbing books/billing paths:")
    for path in BOOKS_GUESSES:
        url = ADMIN_BASE + path
        resp = client.get(url)
        ct = resp.headers.get("content-type", "")
        body = resp.content[:4]
        note = "XLSX" if body == XLSX_MAGIC else ""
        print(f"  {resp.status_code}  {url}  {ct[:50]}  {note}")
        if resp.status_code == 200 and "html" in ct:
            sub_links = [h for h in extract_links(resp.text) if "/admin" in h]
            for sl in sorted(set(sub_links)):
                print(f"    -> {sl}")

    client.close()


if __name__ == "__main__":
    main()
