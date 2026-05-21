import httpx
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


def get_orders(limit: int = 500) -> list[dict]:
    try:
        r = httpx.get(
            f"{FTF_API_BASE_URL}/orders",
            headers=_headers(),
            params={"limit": limit},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        body = r.json()
        # API returns {"count": N, "data": [...]} — extract the list
        return body.get("data", body) if isinstance(body, dict) else body
    except httpx.HTTPStatusError as exc:
        raise AgentError(f"get_orders HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise AgentError("get_orders failed") from exc


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
