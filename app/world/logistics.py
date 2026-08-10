"""Deterministic logistics for supplying settlement resource needs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class SupplyOrder:
    order_id: str
    origin_id: str
    destination_id: str
    resource: str
    amount: float
    travel_hours: float = 0.0
    tariff: float = 0.0
    status: str = "planned"
    remaining_hours: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, origin_id: str, destination_id: str, resource: str, amount: float, *, travel_hours: float = 0.0, tariff: float = 0.0, order_id: str | None = None) -> "SupplyOrder":
        if origin_id == destination_id or not resource.strip() or amount <= 0 or travel_hours < 0 or tariff < 0:
            raise ValueError("Ordine di rifornimento non valido.")
        return cls(order_id or str(uuid.uuid4()), origin_id, destination_id, resource.strip(), float(amount), float(travel_hours), float(tariff), "planned", float(travel_hours))

    def advance(self, hours: float) -> bool:
        if hours < 0:
            raise ValueError("Il tempo non può essere negativo.")
        if self.status in {"delivered", "cancelled"}:
            return self.status == "delivered"
        self.remaining_hours = max(0.0, self.remaining_hours - hours)
        if self.remaining_hours == 0:
            self.status = "delivered"
            return True
        self.status = "in_transit"
        return False

    def cancel(self) -> None:
        if self.status != "delivered":
            self.status = "cancelled"

    def to_dict(self) -> dict[str, Any]:
        return {"order_id": self.order_id, "origin_id": self.origin_id, "destination_id": self.destination_id, "resource": self.resource, "amount": self.amount, "travel_hours": self.travel_hours, "tariff": self.tariff, "status": self.status, "remaining_hours": self.remaining_hours, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SupplyOrder":
        return cls(order_id=data["order_id"], origin_id=data["origin_id"], destination_id=data["destination_id"], resource=data["resource"], amount=float(data["amount"]), travel_hours=float(data.get("travel_hours", 0)), tariff=float(data.get("tariff", 0)), status=data.get("status", "planned"), remaining_hours=float(data.get("remaining_hours", data.get("travel_hours", 0))), metadata=dict(data.get("metadata", {})))


@dataclass
class LogisticsState:
    orders: dict[str, SupplyOrder] = field(default_factory=dict)

    def add_order(self, order: SupplyOrder) -> None:
        if order.order_id in self.orders:
            raise ValueError("Ordine già presente.")
        self.orders[order.order_id] = order

    def advance(self, hours: float) -> list[SupplyOrder]:
        delivered: list[SupplyOrder] = []
        for order in self.orders.values():
            was_delivered = order.status == "delivered"
            if order.advance(hours) and not was_delivered:
                delivered.append(order)
        return delivered

    def active_orders(self) -> list[SupplyOrder]:
        return [order for order in self.orders.values() if order.status not in {"delivered", "cancelled"}]

    def to_dict(self) -> dict[str, Any]:
        return {"orders": {k: v.to_dict() for k, v in self.orders.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogisticsState":
        result = cls()
        for raw in data.get("orders", {}).values():
            order = SupplyOrder.from_dict(raw)
            result.orders[order.order_id] = order
        return result
