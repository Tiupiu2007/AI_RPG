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

    def remove_location(self, location_id: str) -> Location:
        location = self.require_location(location_id)
        if self.settlements.at_location(location_id) is not None:
            raise ValueError("Impossibile rimuovere una località che contiene un insediamento.")
        if any(route.origin_id == location_id or route.destination_id == location_id for route in self.geography.routes.values()):
            raise ValueError("Impossibile rimuovere una località collegata a una rotta.")
        if any(route.origin_id == location_id or route.destination_id == location_id for route in self.trade.routes.values()):
            raise ValueError("Impossibile rimuovere una località collegata a una rotta commerciale.")
        if any(resource.location_id == location_id for resource in self.economy.resources.values()):
            raise ValueError("Impossibile rimuovere una località con risorse registrate.")
        if any(market.location_id == location_id for market in self.economy.markets.values()):
            raise ValueError("Impossibile rimuovere una località che ospita un mercato.")
        for actor_id, position in list(self.actor_positions.items()):
            if position.location_id == location_id or position.destination_id == location_id:
                raise ValueError(f"Impossibile rimuovere una località usata dall'attore '{actor_id}'.")
        for region in self.regions.regions.values():
            if location_id in region.location_ids:
                region.location_ids.remove(location_id)
        del self.locations[location_id]
        self.update()
        return location

    def add_settlement(self, settlement) -> None:
        from .settlements import Settlement

        if not isinstance(settlement, Settlement):
            raise TypeError("È possibile aggiungere solo oggetti Settlement.")
        location = self.require_location(settlement.location_id)
        if settlement.region_id is not None and settlement.region_id not in self.regions.regions:
            raise KeyError(f"Regione dell'insediamento non trovata: {settlement.region_id}")
        self.settlements.add(settlement)
        location.attributes["settlement_type"] = settlement.settlement_type
        if settlement.region_id is not None:
            self.regions.regions[settlement.region_id].add_location(location.location_id)
        elif location.coordinates is not None:
            region = self.region_at(location.coordinates)
            if region is not None:
                region.add_location(location.location_id)
                settlement.region_id = region.region_id
        self.update()

    def settlement_at_location(self, location_id: str):
        return self.settlements.at_location(location_id)

    def population_at_location(self, location_id: str) -> int:
        settlement = self.settlement_at_location(location_id)
        return settlement.population.total if settlement is not None else 0

    def racial_population_at_location(self, location_id: str) -> dict[str, int]:
        settlement = self.settlement_at_location(location_id)
        return settlement.population.distribution() if settlement is not None else {}

    def population_in_region(self, region_id: str) -> int:
        if region_id not in self.regions.regions:
            raise KeyError(f"Regione non trovata: {region_id}")
        return sum(
            settlement.population.total
            for settlement in self.settlements.settlements.values()
            if settlement.region_id == region_id
        )

    def get_location(self, location_id: str) -> Location | None:
        return self.locations.get(location_id)

    def require_location(self, location_id: str) -> Location:
        location = self.get_location(location_id)
        if location is None:
            raise KeyError(f"Località non trovata: {location_id}")
        return location

    def get_route(self, route_id: str) -> Route | None:
        return self.geography.get_route(route_id)

    def routes_from(self, location_id: str, *, available_only: bool = True) -> list[Route]:
        return self.geography.routes_from(location_id, available_only=available_only)

    def set_actor_position(self, actor_id: str, location_id: str) -> ActorPosition:
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("actor_id non valido.")
        self.require_location(location_id)
        existing = self.actor_positions.get(actor_id)
        if existing is not None and existing.is_traveling:
            raise ValueError("Impossibile cambiare posizione a un attore mentre è in viaggio.")
        position = ActorPosition(actor_id=actor_id, location_id=location_id)
        self.actor_positions[actor_id] = position
        self.update()
        return position

    def require_actor_position(self, actor_id: str) -> ActorPosition:
        position = self.actor_positions.get(actor_id)
        if position is None:
            raise KeyError(f"Posizione dell'attore non trovata: {actor_id}")
        return position

    def begin_actor_travel(
        self,
        actor_id: str,
        destination_id: str,
        route_ids: tuple[str, ...],
    ) -> ActorPosition:
        position = self.require_actor_position(actor_id)
        self.require_location(destination_id)
        if position.is_traveling:
            raise ValueError("L'attore è già in viaggio.")
        if not route_ids:
            raise ValueError("Un viaggio deve avere almeno una rotta.")

        current_location_id = position.location_id
        for route_id in route_ids:
            route = self.get_route(route_id)
            if route is None:
                raise KeyError(f"Rotta non trovata: {route_id}")
            if not route.available:
                raise ValueError(f"La rotta '{route_id}' non è disponibile.")
            if route.origin_id != current_location_id:
                raise ValueError("Le rotte non formano un percorso continuo dalla posizione attuale.")
            current_location_id = route.destination_id

        if current_location_id != destination_id:
            raise ValueError("Il percorso non termina nella destinazione richiesta.")

        position.begin_travel(destination_id, route_ids)
        self.update()
        return position

    def arrive_actor(self, actor_id: str, destination_id: str) -> ActorPosition:
        position = self.require_actor_position(actor_id)
        self.require_location(destination_id)
        if not position.is_traveling:
            raise ValueError("L'attore non è in viaggio.")
        if position.destination_id != destination_id:
            raise ValueError("La destinazione non corrisponde al viaggio attivo.")
        position.arrive(destination_id)
        self.update()
        return position

    def biomes_between_locations(self, first_id: str, second_id: str) -> list[str | None]:
        first = self.require_location(first_id)
        second = self.require_location(second_id)
        if first.coordinates is None or second.coordinates is None:
            return []
        return self.biomes.transition_between(first.coordinates, second.coordinates)

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

        # Reject saves whose cross-object references would leave a broken world.
        for region in world.regions.regions.values():
            if region.parent_region_id is not None and region.parent_region_id not in world.regions.regions:
                raise ValueError(f"Regione '{region.region_id}' riferita a una regione genitore inesistente.")
            if any(biome_id not in world.biomes.definitions for biome_id in region.biome_ids):
                raise ValueError(f"Regione '{region.region_id}' riferita a un bioma inesistente.")
            if any(location_id not in world.locations for location_id in region.location_ids):
                raise ValueError(f"Regione '{region.region_id}' contiene località inesistenti.")

        # Region hierarchies must be acyclic.
        for region in world.regions.regions.values():
            visited: set[str] = set()
            current = region
            while current.parent_region_id is not None:
                if current.region_id in visited:
                    raise ValueError(f"La gerarchia delle regioni contiene un ciclo presso '{current.region_id}'.")
                visited.add(current.region_id)
                current = world.regions.regions[current.parent_region_id]
                if current.region_id in visited:
                    raise ValueError(f"La gerarchia delle regioni contiene un ciclo presso '{current.region_id}'.")
        for territory in world.regions.racial_territories.values():
            if territory.region_id is not None and territory.region_id not in world.regions.regions:
                raise ValueError(f"Territorio razziale '{territory.territory_id}' riferito a una regione inesistente.")
        for route in world.geography.routes.values():
            if route.origin_id not in world.locations or route.destination_id not in world.locations:
                raise ValueError(f"Rotta '{route.route_id}' riferita a una località inesistente.")
        for route in world.trade.routes.values():
            if route.origin_id not in world.locations or route.destination_id not in world.locations:
                raise ValueError(f"Rotta commerciale '{route.route_id}' riferita a una località inesistente.")
        for settlement in world.settlements.settlements.values():
            if settlement.location_id not in world.locations:
                raise ValueError(f"Insediamento '{settlement.settlement_id}' riferito a una località inesistente.")
            if settlement.region_id is not None and settlement.region_id not in world.regions.regions:
                raise ValueError(f"Insediamento '{settlement.settlement_id}' riferito a una regione inesistente.")
        for actor_id, position in world.actor_positions.items():
            if position.location_id not in world.locations:
                raise ValueError(f"L'attore '{actor_id}' ha una posizione riferita a una località inesistente.")
            if position.destination_id is not None and position.destination_id not in world.locations:
                raise ValueError(f"L'attore '{actor_id}' ha una destinazione riferita a una località inesistente.")
            if any(route_id not in world.geography.routes for route_id in position.route_ids):
                raise ValueError(f"L'attore '{actor_id}' ha un viaggio con rotte inesistenti.")
        for resource in world.economy.resources.values():
            if resource.location_id is not None and resource.location_id not in world.locations:
                raise ValueError(f"La risorsa '{resource.resource_id}' è riferita a una località inesistente.")
            if resource.region_id is not None and resource.region_id not in world.regions.regions:
                raise ValueError(f"La risorsa '{resource.resource_id}' è riferita a una regione inesistente.")
        for market in world.economy.markets.values():
            if market.location_id not in world.locations:
                raise ValueError(f"Il mercato '{market.market_id}' è riferito a una località inesistente.")

        return world


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
