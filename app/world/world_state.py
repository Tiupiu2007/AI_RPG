"""Core persistent state of the AI RPG world."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from .biomes import BiomeMap
from .economy import EconomyState
from .environment import EnvironmentEngine
from .factions import FactionMap
from .geography import Geography, Route
from .locations import Location
from .positions import ActorPosition
from .regions import Region, RegionMap, RacialTerritory
from .settlements import SettlementMap
from .settlement_conditions import SettlementConditionMap, SettlementConditions
from .time import WorldClock
from .trade import ProductionRule, TradeMap, TradeRoute


@dataclass
class WorldState:
    world_id: str
    name: str
    description: str = ""
    locations: dict[str, Location] = field(default_factory=dict)
    geography: Geography = field(default_factory=Geography)
    biomes: BiomeMap = field(default_factory=BiomeMap)
    regions: RegionMap = field(default_factory=RegionMap)
    settlements: SettlementMap = field(default_factory=SettlementMap)
    settlement_conditions: SettlementConditionMap = field(default_factory=SettlementConditionMap)
    clock: WorldClock = field(default_factory=WorldClock.create)
    environment: EnvironmentEngine = field(default_factory=EnvironmentEngine)
    factions: FactionMap = field(default_factory=FactionMap)
    economy: EconomyState = field(default_factory=EconomyState)
    trade: TradeMap = field(default_factory=TradeMap)
    actor_positions: dict[str, ActorPosition] = field(default_factory=dict)
    events: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: _utc_now())

    @classmethod
    def create(cls, name: str, description: str = "", *, world_id: str | None = None, clock: WorldClock | None = None, environment_seed: int = 0) -> "WorldState":
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Il mondo deve avere un nome.")
        return cls(world_id=world_id or str(uuid.uuid4()), name=normalized_name, description=description.strip(), clock=clock or WorldClock.create(), environment=EnvironmentEngine(seed=environment_seed))

    def update(self) -> None:
        self.updated_at = _utc_now()

    def advance_time_minutes(self, minutes: int) -> datetime:
        result = self.clock.advance_minutes(minutes)
        self.update()
        return result

    def advance_time_hours(self, hours: int) -> datetime:
        result = self.clock.advance_hours(hours)
        self.update()
        return result

    def advance_time_days(self, days: int) -> datetime:
        result = self.clock.advance_days(days)
        self.update()
        return result

    def add_location(self, location: Location) -> None:
        if not isinstance(location, Location):
            raise TypeError("È possibile aggiungere solo oggetti Location.")
        if location.location_id in self.locations:
            raise ValueError(f"La località '{location.location_id}' esiste già nel mondo.")
        self.locations[location.location_id] = location
        self.update()

    def get_location(self, location_id: str) -> Location | None:
        return self.locations.get(location_id)

    def require_location(self, location_id: str) -> Location:
        location = self.get_location(location_id)
        if location is None:
            raise KeyError(f"Località non trovata: {location_id}")
        return location

    def add_route(self, route: Route) -> None:
        if route.origin_id not in self.locations or route.destination_id not in self.locations:
            raise KeyError("La rotta deve riferirsi a località esistenti.")
        self.geography.add_route(route, locations=self.locations)
        self.update()

    def add_region(self, region: Region) -> None:
        self.regions.add_region(region)
        self.update()

    def add_racial_territory(self, territory: RacialTerritory) -> None:
        self.regions.add_territory(territory)
        self.update()

    def region_at(self, coordinates: dict[str, float]) -> Region | None:
        return self.regions.region_at(coordinates)

    def racial_concentrations_at(self, coordinates: dict[str, float]) -> dict[str, float]:
        return self.regions.racial_concentrations_at(coordinates)

    def dominant_race_at(self, coordinates: dict[str, float]) -> str | None:
        return self.regions.dominant_race_at(coordinates)

    def add_settlement_conditions(self, conditions: SettlementConditions) -> None:
        self.settlement_conditions.add(conditions)
        self.update()

    def get_settlement_conditions(self, settlement_id: str) -> SettlementConditions | None:
        return self.settlement_conditions.get(settlement_id)

    def update_settlement_conditions(self, settlement_id: str, *, unmet_needs: dict[str, float], total_requirements: dict[str, float], trade_access: float = 0.0, security_pressure: float = 0.0) -> SettlementConditions:
        conditions = self.get_settlement_conditions(settlement_id)
        if conditions is None:
            conditions = SettlementConditions(settlement_id=settlement_id)
            self.settlement_conditions.add(conditions)
        conditions.apply_daily_conditions(unmet_needs=unmet_needs, total_requirements=total_requirements, trade_access=trade_access, security_pressure=security_pressure)
        self.update()
        return conditions

    def add_production_rule(self, rule: ProductionRule) -> None:
        self.trade.add_production_rule(rule)
        self.update()

    def add_trade_route(self, route: TradeRoute) -> None:
        if route.origin_id not in self.locations or route.destination_id not in self.locations:
            raise KeyError("La rotta commerciale deve riferirsi a località esistenti.")
        self.trade.add_route(route)
        self.update()

    def production_cycles_available(self, rule_id: str, stock: dict[str, float]) -> int:
        rule = self.trade.production_rules.get(rule_id)
        if rule is None:
            raise KeyError(f"Regola di produzione non trovata: {rule_id}")
        return rule.max_cycles(stock)

    def apply_production(self, rule_id: str, stock: dict[str, float], cycles: int = 1) -> dict[str, float]:
        rule = self.trade.production_rules.get(rule_id)
        if rule is None:
            raise KeyError(f"Regola di produzione non trovata: {rule_id}")
        result = rule.apply(stock, cycles)
        self.update()
        return result

    def to_dict(self) -> dict[str, Any]:
        return {"world_id": self.world_id, "name": self.name, "description": self.description, "locations": {k: v.to_dict() for k, v in self.locations.items()}, "geography": self.geography.to_dict(), "biomes": self.biomes.to_dict(), "regions": self.regions.to_dict(), "settlements": self.settlements.to_dict(), "settlement_conditions": self.settlement_conditions.to_dict(), "clock": self.clock.to_dict(), "environment": self.environment.to_dict(), "factions": self.factions.to_dict(), "economy": self.economy.to_dict(), "trade": self.trade.to_dict(), "actor_positions": {k: v.to_dict() for k, v in self.actor_positions.items()}, "events": self.events, "conditions": self.conditions, "metadata": self.metadata, "updated_at": self.updated_at}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldState":
        if not isinstance(data, dict):
            raise TypeError("Lo stato del mondo deve essere un dizionario.")
        world = cls.create(data["name"], data.get("description", ""), world_id=data["world_id"])
        world.locations = {raw["location_id"]: Location.from_dict(raw) for raw in data.get("locations", {}).values()}
        world.geography = Geography.from_dict(data.get("geography", {}))
        world.biomes = BiomeMap.from_dict(data.get("biomes", {}))
        world.regions = RegionMap.from_dict(data.get("regions", {}))
        world.settlements = SettlementMap.from_dict(data.get("settlements", {}))
        world.settlement_conditions = SettlementConditionMap.from_dict(data.get("settlement_conditions", {}))
        world.clock = WorldClock.from_dict(data.get("clock", {}))
        world.environment = EnvironmentEngine.from_dict(data.get("environment", {}))
        world.factions = FactionMap.from_dict(data.get("factions", {}))
        world.economy = EconomyState.from_dict(data.get("economy", {}))
        world.trade = TradeMap.from_dict(data.get("trade", {}))
        world.actor_positions = {raw["actor_id"]: ActorPosition.from_dict(raw) for raw in data.get("actor_positions", {}).values()}
        world.events = dict(data.get("events", {}))
        world.conditions = dict(data.get("conditions", {}))
        world.metadata = dict(data.get("metadata", {}))
        world.updated_at = data.get("updated_at", _utc_now())
        return world


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
