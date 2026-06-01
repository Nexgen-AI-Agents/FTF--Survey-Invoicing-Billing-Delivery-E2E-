import httpx
from datetime import date
from typing import Optional

from config.settings import FTF_API_BASE_URL, FTF_API_KEY
from core.exceptions import AgentError, PricingError
from core.logger import get_logger

logger = get_logger(__name__)

_TIMEOUT = 30.0


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {FTF_API_KEY}",
        "Content-Type": "application/json",
    }


def health_check() -> bool:
    try:
        r = httpx.get(f"{FTF_API_BASE_URL}/health", headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        return True
    except Exception as exc:
        logger.error("FTF health check failed: %s", exc)
        return False


def get_orders(
    limit: int = 500,
    status: Optional[str] = None,
    max_results: Optional[int] = None,
    extra_params: Optional[dict] = None,
) -> list[dict]:
    """Fetch orders via paginated calls.

    Args:
        limit:       Page size — API hard-caps at 500.
        status:      Optional server-side status filter.
        max_results: Stop after collecting this many results (prevents runaway
                     pagination on a 275 K-order dataset). None = fetch all.
        extra_params: Any additional query params to pass through (e.g. date_from,
                     customer_type) — ignored by the API if unsupported.

    Returns:
        Flat list of order dicts (up to max_results if specified).
    """
    all_orders: list[dict] = []
    offset = 0

    while True:
        params: dict = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if extra_params:
            params.update(extra_params)

        try:
            r = httpx.get(
                f"{FTF_API_BASE_URL}/orders",
                headers=_headers(),
                params=params,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            body = r.json()
        except httpx.HTTPStatusError as exc:
            raise AgentError(f"get_orders HTTP {exc.response.status_code}") from exc
        except Exception as exc:
            raise AgentError("get_orders failed") from exc

        # API envelope: {"count": N, "data": [...], "limit": N, "offset": N, "total": N}
        if isinstance(body, dict):
            page = body.get("data", [])
            total = body.get("total", 0)
        else:
            return body  # type: ignore[return-value]

        if offset == 0 and total == 0:
            logger.warning("get_orders: API returned total=0 — no orders or API misconfigured")

        logger.info("fetched page offset=%s count=%s total=%s", offset, len(page), total)
        all_orders.extend(page)

        if max_results and len(all_orders) >= max_results:
            return all_orders[:max_results]

        offset += limit
        if offset >= total or not page:
            break

    return all_orders


def get_order(order_id: str) -> dict:
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/orders/{order_id}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        raise AgentError(f"get_order({order_id}) HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise AgentError(f"get_order({order_id}) failed") from exc


def get_customer(customer_id: str) -> dict:
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/customers/{customer_id}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        raise AgentError(f"get_customer({customer_id}) HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise AgentError(f"get_customer({customer_id}) failed") from exc


def get_pricing(service: str, tier: str = "individual") -> dict:
    """Fetch price for one service. tier is 'individual' (default) or 'b2b'."""
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/pricing",
            headers=_headers(),
            params={"service": service, "tier": tier},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        raise PricingError("get_pricing failed") from exc


def get_pricing_overrides() -> dict:
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/pricing/overrides", headers=_headers(), timeout=_TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        raise PricingError("get_pricing_overrides failed") from exc


def get_invoice_needed_orders(max_results: int = 1000) -> list[dict]:
    """Return all orders that have the 'order needs an invoice' flag set.

    Uses the filter_by_flag=invoice_needed API param — maps to the $ indicator
    visible in the FTF Track Flow UI (stage.fieldtofinish.jobs).
    """
    return get_orders(extra_params={"filter_by_flag": "invoice_needed"}, max_results=max_results)


def get_invoice(invoice_id: str) -> dict:
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/invoices/{invoice_id}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        raise AgentError(f"get_invoice({invoice_id}) HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise AgentError(f"get_invoice({invoice_id}) failed") from exc


def create_invoice(order_id: str, amount: float, services: list[dict]) -> dict:
    payload = {"order_id": order_id, "amount": amount, "services": services}
    try:
        r = httpx.post(
            f"{FTF_API_BASE_URL}/invoices",
            headers=_headers(),
            json=payload,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        raise AgentError(f"create_invoice HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise AgentError("create_invoice failed") from exc


def send_invoice(invoice_id: str) -> bool:
    try:
        r = httpx.post(
            f"{FTF_API_BASE_URL}/invoices/{invoice_id}/send",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except Exception as exc:
        raise AgentError(f"send_invoice({invoice_id}) failed") from exc


def send_reminder(order_id: str, message: str) -> bool:
    payload = {"order_id": order_id, "message": message}
    try:
        r = httpx.post(
            f"{FTF_API_BASE_URL}/reminders",
            headers=_headers(),
            json=payload,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except Exception as exc:
        raise AgentError(f"send_reminder({order_id}) failed") from exc


def get_b2b_orders_for_month(month: date) -> list[dict]:
    """Return all B2B orders whose order_date falls within the given calendar month.

    Passes date_from / date_to / customer_type as query params — the FTF API
    may or may not honour them, so results are always filtered client-side too.
    max_results=5000 prevents runaway pagination on a 275 K-order dataset while
    still covering any realistic single-month B2B volume.
    """
    from datetime import datetime as _dt
    import calendar

    month_start          = month.replace(day=1)
    last_day             = calendar.monthrange(month.year, month.month)[1]
    month_end_inclusive  = month.replace(day=last_day)

    extra = {
        "customer_type": "b2b",
        "date_from":     month_start.isoformat(),
        "date_to":       month_end_inclusive.isoformat(),
    }
    all_orders = get_orders(limit=500, extra_params=extra, max_results=5000)

    result = []
    for order in all_orders:
        if str(order.get("customer_type", "")).lower() != "b2b":
            continue

        raw_date = order.get("order_date") or order.get("service_date") or order.get("created_at")
        order_date = None
        if isinstance(raw_date, date) and not isinstance(raw_date, _dt):
            order_date = raw_date
        elif isinstance(raw_date, _dt):
            order_date = raw_date.date()
        elif isinstance(raw_date, str):
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
                try:
                    order_date = _dt.strptime(raw_date[:10], fmt[:10]).date()
                    break
                except ValueError:
                    pass

        if order_date and month_start <= order_date <= month_end_inclusive:
            result.append(order)

    logger.info("get_b2b_orders_for_month: %d B2B orders for %s", len(result), month)
    return result


def mark_estimate_sent(order_id: str) -> bool:
    try:
        r = httpx.patch(
            f"{FTF_API_BASE_URL}/orders/{order_id}",
            headers=_headers(),
            json={"estimate_sent": True},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except Exception as exc:
        raise AgentError(f"mark_estimate_sent({order_id}) failed") from exc


def create_order(payload: dict) -> dict:
    """Attempt to create an order via POST /orders.

    FTF does not expose a public order-creation endpoint — orders originate from
    the FTF CRM and cannot be injected via the AI API.  This function tries the
    endpoint anyway (in case it becomes available) and raises AgentError if it
    gets a 404 or 405, which is the expected production behaviour.

    For QA / testing: use scripts/qa_orders.py which injects directly into
    processed_orders at status='classified', bypassing the FTF API dependency.
    """
    try:
        r = httpx.post(
            f"{FTF_API_BASE_URL}/orders",
            headers=_headers(),
            json=payload,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        raise AgentError(
            f"create_order HTTP {exc.response.status_code} — "
            "FTF does not support order creation via AI API; use qa_orders.py for testing"
        ) from exc
    except Exception as exc:
        raise AgentError("create_order failed") from exc
