"""Deterministic settlement consumption and resource-needs model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class ResourceNeed:
    need_id: str
    resource: str
    amount_per_capita_per_day: float
    priority: int = 1
    essential: bool = False

    @classmethod
    def create(cls, resource: str, amount_per_capita_per_day: float, *, priority: int = 1, essential: bool = False, need_id: str | None = None) -> "ResourceNeed":
        resource = resource.strip()
        if not resource or amount_per_capita_per_day < 0 or priority < 1:
            raise ValueError("Fabbisogno non valido.")
        return cls(need_id or str(uuid.uuid4()), resource, float(amount_per_capita_per_day), int(priority), bool(essential))

    def daily_amount(self, population: int) -> float:
        if population < 0:
            raise ValueError("La popolazione non può essere negativa.")
        return self.amount_per_capita_per_day * population

    def to_dict(self) -> dict[str, Any]:
        return {"need_id": self.need_id, "resource": self.resource, "amount_per_capita_per_day": self.amount_per_capita_per_day, "priority": self.priority, "essential": self.essential}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResourceNeed":
        return cls.create(data["resource"], data.get("amount_per_capita_per_day", 0), priority=data.get("priority", 1), essential=data.get("essential", False), need_id=data.get("need_id"))


@dataclass
class SettlementConsumption:
    settlement_id: str
    population: int = 0
    needs: dict[str, ResourceNeed] = field(default_factory=dict)
    stock: dict[str, float] = field(default_factory=dict)
    unmet_needs: dict[str, float] = field(default_factory=dict)

    def add_need(self, need: ResourceNeed) -> None:
        if need.need_id in self.needs:
            raise ValueError("Fabbisogno già presente.")
        self.needs[need.need_id] = need

    def daily_requirements(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for need in self.needs.values():
            result[need.resource] = result.get(need.resource, 0.0) + need.daily_amount(self.population)
        return result

    def consume_day(self) -> dict[str, float]:
        remaining = dict(self.stock)
        consumed: dict[str, float] = {}
        unmet: dict[str, float] = {}
        requirements = sorted(self.needs.values(), key=lambda need: (-need.priority, not need.essential))
        for need in requirements:
            amount = need.daily_amount(self.population)
            available = max(0.0, remaining.get(need.resource, 0.0))
            used = min(available, amount)
            remaining[need.resource] = available - used
            consumed[need.resource] = consumed.get(need.resource, 0.0) + used
            if used < amount:
                unmet[need.resource] = unmet.get(need.resource, 0.0) + (amount - used)
        self.stock = remaining
        self.unmet_needs = unmet
        return consumed

    def supply(self, resource: str, amount: float) -> None:
        if amount < 0:
            raise ValueError("La quantità non può essere negativa.")
        self.stock[resource] = self.stock.get(resource, 0.0) + amount

    def to_dict(self) -> dict[str, Any]:
        return {"settlement_id": self.settlement_id, "population": self.population, "needs": {k: v.to_dict() for k, v in self.needs.items()}, "stock": dict(self.stock), "unmet_needs": dict(self.unmet_needs)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SettlementConsumption":
        result = cls(settlement_id=data["settlement_id"], population=int(data.get("population", 0)), stock={k: float(v) for k, v in data.get("stock", {}).items()}, unmet_needs={k: float(v) for k, v in data.get("unmet_needs", {}).items()})
        for raw in data.get("needs", {}).values():
            need = ResourceNeed.from_dict(raw)
            result.needs[need.need_id] = need
        return result


@dataclass
class ConsumptionMap:
    settlements: dict[str, SettlementConsumption] = field(default_factory=dict)

    def add(self, consumption: SettlementConsumption) -> None:
        if consumption.settlement_id in self.settlements:
            raise ValueError("Consumo dell'insediamento già presente.")
        self.settlements[consumption.settlement_id] = consumption

    def consume_all(self) -> dict[str, dict[str, float]]:
        return {settlement_id: consumption.consume_day() for settlement_id, consumption in self.settlements.items()}

    def to_dict(self) -> dict[str, Any]:
        return {"settlements": {k: v.to_dict() for k, v in self.settlements.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConsumptionMap":
        result = cls()
        for raw in data.get("settlements", {}).values():
            consumption = SettlementConsumption.from_dict(raw)
            result.settlements[consumption.settlement_id] = consumption
        return result
