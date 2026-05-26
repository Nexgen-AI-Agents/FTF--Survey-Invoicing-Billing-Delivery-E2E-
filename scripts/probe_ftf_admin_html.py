"""
Fetch admin home HTML and search for Books/AR/invoice/unpaid path patterns.
Also checks JS files for route definitions.

Usage:
    python scripts/probe_ftf_admin_html.py
"""

import re
import sys
import httpx

import os as _os
ADMIN_BASE = _os.getenv("FTF_BOOKS_BASE_URL", "https://stage.fieldtofinish.jobs")
LOGIN_URL  = f"{ADMIN_BASE}/admin/login"
CREDS      = {"user": _os.getenv("FTF_BOOKS_USER", ""), "password": _os.getenv("FTF_BOOKS_PASSWORD", "")}
AJAX       = {"X-Requested-With": "XMLHttpRequest"}

KEYWORDS = re.compile(
    r"(book|ar[_\-/]|unpaid|invoice|account.receiv|receiv|billing|finance|export|download|report)",
    re.IGNORECASE,
)

ROUTE_RE = re.compile(r"['\"/]admin/[a-z0-9_\-/]+['\"/]", re.IGNORECASE)


def main() -> None:
    client = httpx.Client(follow_redirects=True, timeout=30.0)

    r = client.post(LOGIN_URL, data=CREDS, headers=AJAX)
    if r.status_code not in (200, 302):
        print(f"Login failed: {r.status_code}")
        sys.exit(1)
    print("Login OK\n")

    home = client.get(f"{ADMIN_BASE}/admin/")
    html = home.text

    # Search for keyword lines
    print("=== Lines containing Books/AR/invoice keywords ===")
    for i, line in enumerate(html.splitlines(), 1):
        if KEYWORDS.search(line):
            print(f"  L{i:4}: {line.strip()[:120]}")

    # Extract all /admin/... route-like strings
    routes = set(ROUTE_RE.findall(html))
    admin_routes = sorted(
        r.strip("\"'/") for r in routes
        if "admin/" in r and "static" not in r and "css" not in r
    )
    print(f"\n=== /admin/* route strings in HTML ({len(admin_routes)}) ===")
    for rt in admin_routes:
        print(f"  {rt}")

    # Check script src tags for JS files that may have routes
    script_srcs = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
    print(f"\n=== Script tags ({len(script_srcs)}) ===")
    for src in script_srcs:
        url = src if src.startswith("http") else ADMIN_BASE + src
        print(f"  {url}")
        try:
            js = client.get(url, timeout=10.0)
            if js.status_code == 200:
                js_routes = set(ROUTE_RE.findall(js.text))
                filtered = sorted(
                    r.strip("\"'/") for r in js_routes
                    if "admin/" in r and "static" not in r
                )
                for rt in filtered:
                    print(f"    -> {rt}")
                # Also keyword search
                for line in js.text.splitlines():
                    if KEYWORDS.search(line):
                        print(f"    KW: {line.strip()[:120]}")
        except Exception as e:
            print(f"    ERROR: {e}")

    client.close()


if __name__ == "__main__":
    main()
