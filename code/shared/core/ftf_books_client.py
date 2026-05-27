import io
from datetime import date, datetime, timezone
from typing import Optional

import httpx
import openpyxl

from config.settings import FTF_BOOKS_BASE_URL, FTF_BOOKS_USER, FTF_BOOKS_PASSWORD
from core.exceptions import AgentError
from core.logger import get_logger

logger = get_logger(__name__)

_LOGIN_PATH  = "/admin/login"
_BOOKS_PATH  = "/books/get_data_excel?show_all=1"
_TIMEOUT     = 60


def _parse_excel(raw: bytes) -> list[dict]:
    """Parse the FTF Books AR Excel into a list of invoice dicts."""
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [str(h).strip().lower().replace(" ", "_") if h is not None else "" for h in rows[0]]

    def _col(row, name):
        try:
            return row[headers.index(name)]
        except (ValueError, IndexError):
            return None

    today = date.today()
    invoices = []
    for row in rows[1:]:
        order_id = _col(row, "order_id") or _col(row, "order_number")
        if not order_id:
            continue
        order_id = str(order_id).strip()

        raw_email = _col(row, "customer_email") or _col(row, "email") or ""
        customer_email = str(raw_email).strip().lower()

        raw_amount = _col(row, "invoice_amount") or _col(row, "amount") or 0
        try:
            invoice_amount = float(raw_amount)
        except (TypeError, ValueError):
            invoice_amount = 0.0

        raw_date = _col(row, "invoice_date") or _col(row, "due_date")
        invoice_date: Optional[date] = None
        if isinstance(raw_date, datetime):
            invoice_date = raw_date.date()
        elif isinstance(raw_date, date):
            invoice_date = raw_date
        elif isinstance(raw_date, str):
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
                try:
                    invoice_date = datetime.strptime(raw_date, fmt).date()
                    break
                except ValueError:
                    pass

        days_overdue = (today - invoice_date).days if invoice_date else 0

        invoices.append({
            "order_id": order_id,
            "customer_email": customer_email,
            "invoice_amount": invoice_amount,
            "invoice_date": invoice_date,
            "days_overdue": days_overdue,
        })

    return invoices


def get_unpaid_invoices() -> list[dict]:
    """Login to FTF Books and return all unpaid invoices as parsed dicts."""
    if not FTF_BOOKS_USER or not FTF_BOOKS_PASSWORD:
        raise AgentError("FTF_BOOKS_USER and FTF_BOOKS_PASSWORD must be set")

    with httpx.Client(base_url=FTF_BOOKS_BASE_URL, timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = client.post(
            _LOGIN_PATH,
            data={"email": FTF_BOOKS_USER, "password": FTF_BOOKS_PASSWORD},
        )
        if resp.status_code not in (200, 302):
            raise AgentError(f"FTF Books login failed: HTTP {resp.status_code}")

        resp2 = client.get(_BOOKS_PATH)
        if resp2.status_code != 200:
            raise AgentError(f"FTF Books Excel download failed: HTTP {resp2.status_code}")

        invoices = _parse_excel(resp2.content)
        logger.info("ftf_books_client: parsed %d unpaid invoices", len(invoices))
        return invoices
