"""Core persistent state of the AI RPG world."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from .geography import Geography, Route
from .locations import Location
from .positions import ActorPosition
from .time import WorldClock


@dataclass
class WorldState:
    """Represents the authoritative state of one game world."""

    world_id: str
    name: str
    description: str = ""
    locations: dict[str, Location] = field(default_factory=dict)
    geography: Geography = field(default_factory=Geography)
    clock: WorldClock = field(default_factory=WorldClock.create)
    actor_positions: dict[str, ActorPosition] = field(default_factory=dict)
    factions: dict[str, Any] = field(default_factory=dict)
    events: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: _utc_now())

    @classmethod
    def create(cls, name: str, description: str = "", *, world_id: str | None = None, clock: WorldClock | None = None) -> "WorldState":
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Il mondo deve avere un nome.")
        return cls(world_id=world_id or str(uuid.uuid4()), name=normalized_name, description=description.strip(), clock=clock or WorldClock.create())

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

    def remove_location(self, location_id: str) -> Location | None:
        location = self.locations.get(location_id)
        if location is None:
            return None
        if any(position.location_id == location_id or position.destination_id == location_id for position in self.actor_positions.values()):
            raise ValueError(f"La località '{location_id}' è ancora usata da un attore.")
        for route in list(self.geography.connected_routes(location_id, available_only=False)):
            self.geography.remove_route(route.route_id)
        del self.locations[location_id]
        self.update()
        return location

    def find_locations_by_name(self, name: str) -> list[Location]:
        target = name.strip().casefold()
        if not target:
            return []
        return [location for location in self.locations.values() if location.name.casefold() == target]

    def list_locations(self) -> list[Location]:
        return list(self.locations.values())

    def add_route(self, route: Route) -> None:
        if not isinstance(route, Route):
            raise TypeError("È possibile aggiungere solo oggetti Route.")
        if route.origin_id not in self.locations or route.destination_id not in self.locations:
            raise KeyError("La rotta deve riferirsi a località esistenti.")
        self.geography.add_route(route, locations=self.locations)
        self.update()

    def get_route(self, route_id: str) -> Route | None:
        return self.geography.get_route(route_id)

    def remove_route(self, route_id: str) -> Route | None:
        route = self.geography.remove_route(route_id)
        if route is not None:
            self.update()
        return route

    def routes_from(self, location_id: str, *, available_only: bool = True) -> list[Route]:
        self.require_location(location_id)
        return self.geography.routes_from(location_id, available_only=available_only)

    def routes_to(self, location_id: str, *, available_only: bool = True) -> list[Route]:
        self.require_location(location_id)
        return self.geography.routes_to(location_id, available_only=available_only)

    def set_actor_position(self, actor_id: str, location_id: str) -> ActorPosition:
        self.require_location(location_id)
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("actor_id non valido.")
        position = self.actor_positions.get(actor_id)
        if position is None:
            position = ActorPosition(actor_id=actor_id, location_id=location_id)
            self.actor_positions[actor_id] = position
        else:
            position.arrive(location_id)
        self.update()
        return position

    def get_actor_position(self, actor_id: str) -> ActorPosition | None:
        return self.actor_positions.get(actor_id)

    def require_actor_position(self, actor_id: str) -> ActorPosition:
        position = self.get_actor_position(actor_id)
        if position is None:
            raise KeyError(f"Posizione non trovata per l'attore: {actor_id}")
        return position

    def begin_actor_travel(self, actor_id: str, destination_id: str, route_ids: tuple[str, ...]) -> ActorPosition:
        self.require_location(destination_id)
        position = self.require_actor_position(actor_id)
        position.begin_travel(destination_id, route_ids)
        self.update()
        return position

    def arrive_actor(self, actor_id: str, destination_id: str) -> ActorPosition:
        self.require_location(destination_id)
        position = self.require_actor_position(actor_id)
        position.arrive(destination_id)
        self.update()
        return position

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "locations": {location_id: location.to_dict() for location_id, location in self.locations.items()},
            "geography": self.geography.to_dict(),
            "clock": self.clock.to_dict(),
            "actor_positions": {actor_id: position.to_dict() for actor_id, position in self.actor_positions.items()},
            "factions": self.factions,
            "events": self.events,
            "conditions": self.conditions,
            "metadata": self.metadata,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldState":
        if not isinstance(data, dict):
            raise TypeError("Lo stato del mondo deve essere un dizionario.")
        world_id, name = data.get("world_id"), data.get("name")
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("WorldState: world_id non valido.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("WorldState: name non valido.")

        locations: dict[str, Location] = {}
        raw_locations = data.get("locations", {})
        if isinstance(raw_locations, dict):
            for location_data in raw_locations.values():
                location = location_data if isinstance(location_data, Location) else Location.from_dict(location_data)
                locations[location.location_id] = location

        raw_geography = data.get("geography", {})
        geography = Geography.from_dict(raw_geography) if isinstance(raw_geography, dict) else Geography()
        raw_clock = data.get("clock", {})
        clock = WorldClock.from_dict(raw_clock) if isinstance(raw_clock, dict) else WorldClock.create()
        raw_positions = data.get("actor_positions", {})
        actor_positions: dict[str, ActorPosition] = {}
        if isinstance(raw_positions, dict):
            for position_data in raw_positions.values():
                position = position_data if isinstance(position_data, ActorPosition) else ActorPosition.from_dict(position_data)
                actor_positions[position.actor_id] = position

        world = cls(world_id=world_id, name=name, description=_string_or_empty(data.get("description")), locations=locations, geography=geography, clock=clock, actor_positions=actor_positions, factions=_dict_or_empty(data.get("factions")), events=_dict_or_empty(data.get("events")), conditions=_dict_or_empty(data.get("conditions")), metadata=_dict_or_empty(data.get("metadata")), updated_at=_string_or_empty(data.get("updated_at")) or _utc_now())
        world._validate_geography()
        world._validate_actor_positions()
        return world

    def _validate_geography(self) -> None:
        invalid: list[str] = []
        for route_id, route in self.geography.routes.items():
            origin = self.locations.get(route.origin_id)
            destination = self.locations.get(route.destination_id)
            if origin is None or destination is None:
                invalid.append(route_id)
                continue
            try:
                route.validate_geometry(origin, destination)
            except ValueError:
                invalid.append(route_id)
        for route_id in invalid:
            del self.geography.routes[route_id]

    def _validate_actor_positions(self) -> None:
        invalid = [actor_id for actor_id, position in self.actor_positions.items() if position.location_id not in self.locations or (position.destination_id is not None and position.destination_id not in self.locations)]
        for actor_id in invalid:
            del self.actor_positions[actor_id]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
