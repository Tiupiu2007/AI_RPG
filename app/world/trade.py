"""Deterministic production and trade primitives for the world economy."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
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
        normalized_cycle_hours = float(cycle_hours)
        quantities = [float(value) for value in (*inputs.values(), *outputs.values())]
        if not name.strip() or not isfinite(normalized_cycle_hours) or normalized_cycle_hours <= 0:
            raise ValueError("Regola di produzione non valida.")
        if not inputs and not outputs:
            raise ValueError("Una produzione deve avere input o output.")
        if any(not isfinite(value) or value < 0 for value in quantities):
            raise ValueError("Le quantità devono essere finite e non negative.")
        if any(not isinstance(key, str) or not key.strip() for key in (*inputs.keys(), *outputs.keys())):
            raise ValueError("Le risorse in input e output devono avere un nome.")
        return cls(rule_id or str(uuid.uuid4()), name.strip(), {k: float(v) for k, v in inputs.items()}, {k: float(v) for k, v in outputs.items()}, normalized_cycle_hours)

    def max_cycles(self, stock: dict[str, float]) -> int:
        if not isinstance(stock, dict):
            raise TypeError("Le scorte devono essere un dizionario.")
        for resource, raw_amount in stock.items():
            if not isinstance(resource, str) or not resource.strip():
                raise ValueError("I nomi delle risorse in magazzino non possono essere vuoti.")
            try:
                amount = float(raw_amount)
            except (TypeError, ValueError) as error:
                raise ValueError("Le scorte devono essere numeriche, finite e non negative.") from error
            if not isfinite(amount) or amount < 0:
                raise ValueError("Le scorte devono essere numeriche, finite e non negative.")
        consuming_inputs = {
            resource: amount
            for resource, amount in self.inputs.items()
            if amount > 0
        }
        if not consuming_inputs:
            # A recipe without positive inputs must not generate free resources.
            return 0
        return max(
            0,
            min(int(stock.get(resource, 0.0) // amount) for resource, amount in consuming_inputs.items()),
        )

    def apply(self, stock: dict[str, float], cycles: int = 1) -> dict[str, float]:
        if isinstance(cycles, bool) or not isinstance(cycles, int) or cycles < 0 or cycles > self.max_cycles(stock):
            raise ValueError("Numero di cicli di produzione non disponibile.")
        result = dict(stock)
        for resource, amount in self.inputs.items():
            result[resource] = result.get(resource, 0.0) - amount * cycles
        for resource, amount in self.outputs.items():
            result[resource] = result.get(resource, 0.0) + amount * cycles
        if any(not isfinite(float(value)) or float(value) < 0 for value in result.values()):
            raise ValueError("Le scorte risultanti dalla produzione devono essere finite e non negative.")
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
        normalized_travel_hours = float(travel_hours)
        normalized_tariff = float(tariff)
        normalized_goods = {k: float(v) for k, v in (goods or {}).items()}
        if (
            not isinstance(origin_id, str) or not origin_id.strip()
            or not isinstance(destination_id, str) or not destination_id.strip()
            or origin_id == destination_id
            or not isfinite(normalized_travel_hours) or normalized_travel_hours < 0
            or not isfinite(normalized_tariff) or normalized_tariff < 0
        ):
            raise ValueError("Rotta commerciale non valida.")
        if any(not isinstance(key, str) or not key.strip() for key in normalized_goods):
            raise ValueError("I beni della rotta devono avere un nome.")
        if any(not isfinite(value) or value < 0 for value in normalized_goods.values()):
            raise ValueError("Le quantità trasportate devono essere finite e non negative.")
        return cls(route_id or str(uuid.uuid4()), origin_id, destination_id, normalized_goods, True, normalized_travel_hours, normalized_tariff)

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
