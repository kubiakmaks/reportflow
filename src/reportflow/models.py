from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


ALLOWED_STATUSES = {"paid", "shipped", "processing", "cancelled"}


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    ordered_at: date
    promised_at: date
    shipped_at: date | None
    status: str
    amount: Decimal

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "Order":
        required = ["order_id", "customer_id", "ordered_at", "promised_at", "status", "amount"]
        missing = [field for field in required if raw.get(field) in (None, "")]
        if missing:
            raise ValueError(f"missing fields: {', '.join(missing)}")

        status = str(raw["status"]).lower()
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"unsupported status: {status}")

        try:
            amount = Decimal(str(raw["amount"])).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("amount is not numeric") from exc
        if amount <= 0:
            raise ValueError("amount must be positive")

        try:
            shipped = date.fromisoformat(raw["shipped_at"]) if raw.get("shipped_at") else None
            return cls(
                order_id=str(raw["order_id"]),
                customer_id=str(raw["customer_id"]),
                ordered_at=date.fromisoformat(str(raw["ordered_at"])),
                promised_at=date.fromisoformat(str(raw["promised_at"])),
                shipped_at=shipped,
                status=status,
                amount=amount,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid ISO date") from exc


@dataclass(frozen=True)
class EnrichedOrder:
    order: Order
    customer_name: str
    segment: str
    region: str
    account_owner: str

    @property
    def on_time(self) -> bool | None:
        if self.order.shipped_at is None:
            return None
        return self.order.shipped_at <= self.order.promised_at


@dataclass(frozen=True)
class RejectedRecord:
    page: int
    record: dict[str, Any]
    reason: str
