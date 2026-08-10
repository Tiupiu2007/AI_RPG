"""Persistent resources, production and market state for the world."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class ResourceNode:
    resource_id: str
    resource_type: str
    amount: float
    regeneration_rate: float = 0.0
    location_id: str | None = None
    region_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, resource_type: str, amount: float, *, location_id: str | None = None, region_id: str | None = None, regeneration_rate: float = 0.0, resource_id: str | None = None, metadata: dict[str, Any] | None = None) -> "ResourceNode":
        if not resource_type.strip():
            raise ValueError("La risorsa deve avere un tipo.")
        if amount < 0 or regeneration_rate < 0:
            raise ValueError("Quantità e rigenerazione non possono essere negative.")
        return cls(resource_id or str(uuid.uuid4()), resource_type.strip(), float(amount), float(regeneration_rate), location_id, region_id, dict(metadata or {}))

    def advance(self, days: float = 1.0) -> float:
        if days < 0:
            raise ValueError("I giorni non possono essere negativi.")
        self.amount += self.regeneration_rate * days
        return self.amount

    def consume(self, amount: float) -> None:
        if amount < 0 or amount > self.amount:
            raise ValueError("Quantità di risorsa non disponibile.")
        self.amount -= amount

    def to_dict(self) -> dict[str, Any]:
        return {"resource_id": self.resource_id, "resource_type": self.resource_type, "amount": self.amount, "regeneration_rate": self.regeneration_rate, "location_id": self.location_id, "region_id": self.region_id, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResourceNode":
        return cls.create(data["resource_type"], data["amount"], location_id=data.get("location_id"), region_id=data.get("region_id"), regeneration_rate=data.get("regeneration_rate", 0), resource_id=data.get("resource_id"), metadata=data.get("metadata", {}))


@dataclass
class Market:
    market_id: str
    location_id: str
    currency: str = "gold"
    prices: dict[str, float] = field(default_factory=dict)
    supply: dict[str, float] = field(default_factory=dict)
    demand: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, location_id: str, *, currency: str = "gold", market_id: str | None = None) -> "Market":
        if not location_id.strip():
            raise ValueError("Il mercato deve appartenere a una località.")
        return cls(market_id or str(uuid.uuid4()), location_id, currency.strip() or "gold")

    def set_price(self, item: str, price: float) -> None:
        if price < 0:
            raise ValueError("Il prezzo non può essere negativo.")
        self.prices[item.strip()] = float(price)

    def set_supply(self, item: str, amount: float) -> None:
        self.supply[item.strip()] = max(0.0, float(amount))

    def set_demand(self, item: str, amount: float) -> None:
        self.demand[item.strip()] = max(0.0, float(amount))

    def update_price_from_supply_demand(self, item: str, *, base_price: float, sensitivity: float = 0.5) -> float:
        if base_price < 0 or sensitivity < 0:
            raise ValueError("Prezzo base e sensibilità non validi.")
        supply = self.supply.get(item, 0.0)
        demand = self.demand.get(item, 0.0)
        if supply <= 0:
            price = base_price * (1.0 + sensitivity)
        else:
            ratio = demand / supply
            price = base_price * max(0.1, 1.0 + sensitivity * (ratio - 1.0))
        self.prices[item] = round(price, 4)
        return self.prices[item]

    def to_dict(self) -> dict[str, Any]:
        return {"market_id": self.market_id, "location_id": self.location_id, "currency": self.currency, "prices": dict(self.prices), "supply": dict(self.supply), "demand": dict(self.demand), "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Market":
        return cls.create(data["location_id"], currency=data.get("currency", "gold"), market_id=data.get("market_id"))


@dataclass
class EconomyState:
    resources: dict[str, ResourceNode] = field(default_factory=dict)
    markets: dict[str, Market] = field(default_factory=dict)
    trade_routes: dict[str, dict[str, Any]] = field(default_factory=dict)
    currencies: dict[str, dict[str, Any]] = field(default_factory=lambda: {"gold": {"name": "Oro", "base_value": 1.0}})

    def add_resource(self, resource: ResourceNode) -> None:
        if resource.resource_id in self.resources:
            raise ValueError("Risorsa già presente.")
        self.resources[resource.resource_id] = resource

    def add_market(self, market: Market) -> None:
        if market.market_id in self.markets:
            raise ValueError("Mercato già presente.")
        self.markets[market.market_id] = market

    def resources_at_location(self, location_id: str) -> list[ResourceNode]:
        return [r for r in self.resources.values() if r.location_id == location_id]

    def resources_in_region(self, region_id: str) -> list[ResourceNode]:
        return [r for r in self.resources.values() if r.region_id == region_id]

    def market_at(self, location_id: str) -> Market | None:
        return next((m for m in self.markets.values() if m.location_id == location_id), None)

    def advance_resources(self, days: float = 1.0) -> None:
        for resource in self.resources.values():
            resource.advance(days)

    def to_dict(self) -> dict[str, Any]:
        return {"resources": {k: v.to_dict() for k, v in self.resources.items()}, "markets": {k: v.to_dict() for k, v in self.markets.items()}, "trade_routes": self.trade_routes, "currencies": self.currencies}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EconomyState":
        result = cls()
        for raw in data.get("resources", {}).values():
            item = ResourceNode.from_dict(raw)
            result.resources[item.resource_id] = item
        for raw in data.get("markets", {}).values():
            item = Market.from_dict(raw)
            item.prices = dict(raw.get("prices", {}))
            item.supply = dict(raw.get("supply", {}))
            item.demand = dict(raw.get("demand", {}))
            item.metadata = dict(raw.get("metadata", {}))
            result.markets[item.market_id] = item
        result.trade_routes = dict(data.get("trade_routes", {}))
        result.currencies = dict(data.get("currencies", result.currencies))
        return result
