"""Geographic primitives for the AI RPG world."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
import math
import uuid

if TYPE_CHECKING:
    from .locations import Location


@dataclass
class Route:
    """A traversable connection between two locations."""

    route_id: str
    origin_id: str
    destination_id: str
    distance: float
    terrain: str = ""
    path_type: str = ""
    difficulty: float = 1.0
    conditions: dict[str, Any] = field(default_factory=dict)
    obstacles: list[str] = field(default_factory=list)
    available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, origin_id: str, destination_id: str, distance: float, *, terrain: str = "", path_type: str = "", difficulty: float = 1.0, conditions: dict[str, Any] | None = None, obstacles: list[str] | None = None, available: bool = True, route_id: str | None = None, metadata: dict[str, Any] | None = None) -> "Route":
        if not _valid_id(origin_id) or not _valid_id(destination_id):
            raise ValueError("Origine e destinazione devono avere ID validi.")
        if origin_id == destination_id:
            raise ValueError("Una rotta non può collegare una località a se stessa.")
        if not _positive(distance) or not _positive(difficulty):
            raise ValueError("Distanza e difficoltà devono essere positive.")
        return cls(route_id or str(uuid.uuid4()), origin_id, destination_id, float(distance), terrain.strip(), path_type.strip(), float(difficulty), dict(conditions or {}), list(obstacles or []), bool(available), dict(metadata or {}))

    def validate_geometry(self, origin: "Location", destination: "Location", *, tolerance: float = 0.01) -> None:
        """Validate that the route distance is geometrically plausible.

        Coordinates are authoritative for position, while route distance remains
        authoritative for actual travel. A route may therefore be longer than
        the straight-line distance because of terrain, roads, mountains, rivers,
        or obstacles, but it cannot be shorter than it geometrically could be.
        """
        if origin.coordinates is None or destination.coordinates is None:
            return
        straight_distance = distance_between_coordinates(origin.coordinates, destination.coordinates)
        if self.distance + tolerance < straight_distance:
            raise ValueError(
                f"La rotta '{self.route_id}' è più corta della distanza geografica "
                f"tra '{origin.name}' e '{destination.name}'."
            )

    def set_available(self, available: bool) -> None:
        self.available = bool(available)

    def to_dict(self) -> dict[str, Any]:
        return {"route_id": self.route_id, "origin_id": self.origin_id, "destination_id": self.destination_id, "distance": self.distance, "terrain": self.terrain, "path_type": self.path_type, "difficulty": self.difficulty, "conditions": self.conditions, "obstacles": list(self.obstacles), "available": self.available, "metadata": self.metadata}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Route":
        if not isinstance(data, dict):
            raise TypeError("La rotta deve essere un dizionario.")
        return cls.create(data.get("origin_id", ""), data.get("destination_id", ""), data.get("distance", 0), terrain=data.get("terrain", ""), path_type=data.get("path_type", ""), difficulty=data.get("difficulty", 1), conditions=data.get("conditions", {}), obstacles=data.get("obstacles", []), available=data.get("available", True), route_id=data.get("route_id"), metadata=data.get("metadata", {}))


@dataclass
class Geography:
    """Geographic relationships belonging to one WorldState."""

    routes: dict[str, Route] = field(default_factory=dict)

    def add_route(self, route: Route, *, locations: dict[str, "Location"] | None = None) -> None:
        if not isinstance(route, Route):
            raise TypeError("È possibile aggiungere solo oggetti Route.")
        if route.route_id in self.routes:
            raise ValueError(f"La rotta '{route.route_id}' esiste già.")
        if self.has_route(route.origin_id, route.destination_id):
            raise ValueError("Esiste già una rotta tra queste due località.")
        if locations is not None:
            origin = locations.get(route.origin_id)
            destination = locations.get(route.destination_id)
            if origin is None or destination is None:
                raise KeyError("La rotta deve riferirsi a località esistenti.")
            route.validate_geometry(origin, destination)
        self.routes[route.route_id] = route

    def get_route(self, route_id: str) -> Route | None:
        return self.routes.get(route_id)

    def remove_route(self, route_id: str) -> Route | None:
        return self.routes.pop(route_id, None)

    def routes_from(self, location_id: str, *, available_only: bool = True) -> list[Route]:
        return [r for r in self.routes.values() if r.origin_id == location_id and (r.available or not available_only)]

    def routes_to(self, location_id: str, *, available_only: bool = True) -> list[Route]:
        return [r for r in self.routes.values() if r.destination_id == location_id and (r.available or not available_only)]

    def connected_routes(self, location_id: str, *, available_only: bool = True) -> list[Route]:
        return [r for r in self.routes.values() if location_id in (r.origin_id, r.destination_id) and (r.available or not available_only)]

    def has_route(self, origin_id: str, destination_id: str) -> bool:
        return any(r.origin_id == origin_id and r.destination_id == destination_id for r in self.routes.values())

    def distance_between(self, origin_id: str, destination_id: str) -> float | None:
        for route in self.routes.values():
            if route.origin_id == origin_id and route.destination_id == destination_id and route.available:
                return route.distance
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"routes": {route_id: route.to_dict() for route_id, route in self.routes.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Geography":
        if not isinstance(data, dict):
            raise TypeError("La geografia deve essere un dizionario.")
        geography = cls()
        raw_routes = data.get("routes", {})
        if isinstance(raw_routes, dict):
            for route_data in raw_routes.values():
                if isinstance(route_data, dict):
                    route = Route.from_dict(route_data)
                    geography.routes[route.route_id] = route
        return geography


def distance_between_coordinates(first: dict[str, float], second: dict[str, float]) -> float:
    x1, y1 = _xy(first)
    x2, y2 = _xy(second)
    return math.hypot(x2 - x1, y2 - y1)


def _xy(coordinates: dict[str, float]) -> tuple[float, float]:
    if not isinstance(coordinates, dict):
        raise TypeError("Le coordinate devono essere un dizionario.")
    try:
        return float(coordinates["x"]), float(coordinates["y"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Le coordinate devono contenere x e y numerici.") from error


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
