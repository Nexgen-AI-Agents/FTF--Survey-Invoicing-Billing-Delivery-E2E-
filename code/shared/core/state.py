import datetime

from core.db import save_order_state


def mark_classified(order_id: str, service_type: str, customer_email: str) -> None:
    save_order_state(
        order_id,
        status="classified",
        service_type=service_type,
        customer_email=customer_email,
        classified_at=datetime.datetime.utcnow(),
    )


def mark_flagged(order_id: str, reason: str) -> None:
    save_order_state(
        order_id,
        status="flagged",
        flag_reason=reason,
        flagged_at=datetime.datetime.utcnow(),
    )


def mark_priced(order_id: str, amount: float, is_flood_zone: bool) -> None:
    save_order_state(
        order_id,
        status="priced",
        estimate_amount=amount,
        is_flood_zone=is_flood_zone,
        priced_at=datetime.datetime.utcnow(),
    )


def mark_sent(order_id: str) -> None:
    save_order_state(
        order_id,
        status="sent",
        sent_at=datetime.datetime.utcnow(),
    )
