"""Deterministic production and trade primitives for the world economy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class ProductionRule:
    rule_id: str
    name: str
    inputs: dict[str, float]
    outputs: dict[str, float]
    cycle_hours: float = 24.0

    @classmethod
    def create(cls, name: str, inputs: dict[str, float], outputs: dict[str, float], *, cycle_hours: float = 24.0, rule_id: str | None = None) -> "ProductionRule":
        if not name.strip() or cycle_hours <= 0:
            raise ValueError("Regola di produzione non valida.")
        if not inputs and not outputs:
            raise ValueError("Una produzione deve avere input o output.")
        if any(float(value) < 0 for value in {**inputs, **outputs}.values()):
            raise ValueError("Le quantità non possono essere negative.")
        return cls(rule_id or str(uuid.uuid4()), name.strip(), {k: float(v) for k, v in inputs.items()}, {k: float(v) for k, v in outputs.items()}, float(cycle_hours))

    def max_cycles(self, stock: dict[str, float]) -> int:
        if not self.inputs:
            return 0
        return max(0, min(int(stock.get(resource, 0.0) // amount) for resource, amount in self.inputs.items() if amount > 0))

    def apply(self, stock: dict[str, float], cycles: int = 1) -> dict[str, float]:
        if cycles < 0 or cycles > self.max_cycles(stock):
            raise ValueError("Numero di cicli di produzione non disponibile.")
        result = dict(stock)
        for resource, amount in self.inputs.items():
            result[resource] = result.get(resource, 0.0) - amount * cycles
        for resource, amount in self.outputs.items():
            result[resource] = result.get(resource, 0.0) + amount * cycles
        return result

    def to_dict(self) -> dict[str, Any]:
        return {"rule_id": self.rule_id, "name": self.name, "inputs": dict(self.inputs), "outputs": dict(self.outputs), "cycle_hours": self.cycle_hours}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductionRule":
        return cls.create(data["name"], data.get("inputs", {}), data.get("outputs", {}), cycle_hours=data.get("cycle_hours", 24.0), rule_id=data.get("rule_id"))


@dataclass
class TradeRoute:
    route_id: str
    origin_id: str
    destination_id: str
    goods: dict[str, float] = field(default_factory=dict)
    active: bool = True
    travel_hours: float = 0.0
    tariff: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, origin_id: str, destination_id: str, *, goods: dict[str, float] | None = None, travel_hours: float = 0.0, tariff: float = 0.0, route_id: str | None = None) -> "TradeRoute":
        if origin_id == destination_id or travel_hours < 0 or tariff < 0:
            raise ValueError("Rotta commerciale non valida.")
        return cls(route_id or str(uuid.uuid4()), origin_id, destination_id, {k: float(v) for k, v in (goods or {}).items()}, True, float(travel_hours), float(tariff))

    def to_dict(self) -> dict[str, Any]:
        return {"route_id": self.route_id, "origin_id": self.origin_id, "destination_id": self.destination_id, "goods": dict(self.goods), "active": self.active, "travel_hours": self.travel_hours, "tariff": self.tariff, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TradeRoute":
        route = cls.create(data["origin_id"], data["destination_id"], goods=data.get("goods", {}), travel_hours=data.get("travel_hours", 0.0), tariff=data.get("tariff", 0.0), route_id=data.get("route_id"))
        route.active = bool(data.get("active", True))
        route.metadata = dict(data.get("metadata", {}))
        return route


@dataclass
class TradeMap:
    production_rules: dict[str, ProductionRule] = field(default_factory=dict)
    routes: dict[str, TradeRoute] = field(default_factory=dict)

    def add_production_rule(self, rule: ProductionRule) -> None:
        if rule.rule_id in self.production_rules:
            raise ValueError("Regola di produzione già presente.")
        self.production_rules[rule.rule_id] = rule

    def add_route(self, route: TradeRoute) -> None:
        if route.route_id in self.routes:
            raise ValueError("Rotta commerciale già presente.")
        self.routes[route.route_id] = route

    def to_dict(self) -> dict[str, Any]:
        return {"production_rules": {k: v.to_dict() for k, v in self.production_rules.items()}, "routes": {k: v.to_dict() for k, v in self.routes.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TradeMap":
        result = cls()
        for raw in data.get("production_rules", {}).values():
            rule = ProductionRule.from_dict(raw)
            result.production_rules[rule.rule_id] = rule
        for raw in data.get("routes", {}).values():
            route = TradeRoute.from_dict(raw)
            result.routes[route.route_id] = route
        return result
