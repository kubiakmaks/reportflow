from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import EnrichedOrder


def build_summary(orders: list[EnrichedOrder], rejected_count: int, missing_customers: list[str]) -> dict:
    active = [item for item in orders if item.order.status != "cancelled"]
    shipped = [item for item in orders if item.order.status == "shipped"]
    total_value = sum((item.order.amount for item in active), Decimal("0"))
    on_time_count = sum(item.on_time is True for item in shipped)

    by_region: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_status: dict[str, int] = defaultdict(int)
    for item in orders:
        by_status[item.order.status] += 1
        if item.order.status != "cancelled":
            by_region[item.region] += item.order.amount

    return {
        "kpis": {
            "valid_orders": len(orders),
            "non_cancelled_value": float(total_value),
            "on_time_shipped_rate": on_time_count / len(shipped) if shipped else None,
            "rejected_records": rejected_count,
        },
        "value_by_region": {key: float(value) for key, value in sorted(by_region.items())},
        "orders_by_status": dict(sorted(by_status.items())),
        "quality": {"missing_customer_ids": len(missing_customers)},
        "period": {
            "start": min(item.order.ordered_at for item in orders).isoformat() if orders else None,
            "end": max(item.order.ordered_at for item in orders).isoformat() if orders else None,
        },
    }
