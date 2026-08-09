"""Geography primitives for the AI RPG world.

Coordinates describe where locations physically are. Routes describe how they
can actually be reached. This module does not calculate travel time yet; that
belongs to the future movement/time systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import math
import uuid


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
    def create(
        cls,
        origin_id: str,
        destination_id: str,
        distance: float,
        *,
        terrain: str = "",
        path_type: str = "",
        difficulty: float = 1.0,
        conditions: dict[str, Any] | None = None,
        obstacles: list[str] | None = None,
        available: bool = True,
        route_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Route":
        if not _valid_id(origin_id) or not _valid_id(destination_id):
            raise ValueError("Origine e destinazione devono avere ID validi.")
        if origin_id == destination_id:
            raise ValueError("Una rotta non può collegare una località a se stessa.")
        if not isinstance(distance, (int, float)) or isinstance(distance, bool) or distance <= 0:
            raise ValueError("La distanza deve essere un numero positivo.")
        if not isinstance(difficulty, (int, float)) or isinstance(difficulty, bool) or difficulty <= 0:
            raise ValueError("La difficoltà deve essere un numero positivo.")

        return cls(
            route_id=route_id or str(uuid.uuid4()),
            origin_id=origin_id,
            destination_id=destination_id,
            distance=float(distance),
            terrain=terrain.strip(),
            path_type=path_type.strip(),
            difficulty=float(difficulty),
            conditions=dict(conditions or {}),
            obstacles=list(obstacles or []),
            available=bool(available),
            metadata=dict(metadata or {}),
        )

    def set_available(self, available: bool) -> None:
        self.available = bool(available)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "distance": self.distance,
            "terrain": self.terrain,
            "path_type": self.path_type,
            "difficulty": self.difficulty,
            "conditions": self.conditions,
            "obstacles": list(self.obstacles),
            "available": self.available,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Route":
        if not isinstance(data, dict):
            raise TypeError("La rotta deve essere un dizionario.")
        return cls.create(
            origin_id=data.get("origin_id", ""),
            destination_id=data.get("destination_id", ""),
            distance=data.get("distance", 0),
            terrain=data.get("terrain", ""),
            path_type=data.get("path_type", ""),
            difficulty=data.get("difficulty", 1),
            conditions=data.get("conditions", {}),
            obstacles=data.get("obstacles", []),
            available=data.get("available", True),
            route_id=data.get("route_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Geography:
    """Geographic relationships belonging to one WorldState."""

    routes: dict[str, Route] = field(default_factory=dict)

    def add_route(self, route: Route) -> None:
        if not isinstance(route, Route):
            raise TypeError("È possibile aggiungere solo oggetti Route.")
        if route.route_id in self.routes:
            raise ValueError(f"La rotta '{route.route_id}' esiste già.")
        if self.has_route(route.origin_id, route.destination_id):
            raise ValueError("Esiste già una rotta tra queste due località.")
        self.routes[route.route_id] = route

    def get_route(self, route_id: str) -> Route | None:
        return self.routes.get(route_id)

    def remove_route(self, route_id: str) -> Route | None:
        return self.routes.pop(route_id, None)

    def routes_from(self, location_id: str, *, available_only: bool = True) -> list[Route]:
        return [
            route
            for route in self.routes.values()
            if route.origin_id == location_id
            and (route.available or not available_only)
        ]

    def routes_to(self, location_id: str, *, available_only: bool = True) -> list[Route]:
        return [
            route
            for route in self.routes.values()
            if route.destination_id == location_id
            and (route.available or not available_only)
        ]

    def connected_routes(
        self,
        location_id: str,
        *,
        available_only: bool = True,
    ) -> list[Route]:
        """Return routes touching a location in either direction."""
        return [
            route
            for route in self.routes.values()
            if location_id in (route.origin_id, route.destination_id)
            and (route.available or not available_only)
        ]

    def has_route(self, origin_id: str, destination_id: str) -> bool:
        return any(
            route.origin_id == origin_id
            and route.destination_id == destination_id
            for route in self.routes.values()
        )

    def distance_between(self, origin_id: str, destination_id: str) -> float | None:
        """Return route distance, without inventing a path when none exists."""
        for route in self.routes.values():
            if (
                route.origin_id == origin_id
                and route.destination_id == destination_id
                and route.available
            ):
                return route.distance
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "routes": {
                route_id: route.to_dict()
                for route_id, route in self.routes.items()
            }
        }

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


def distance_between_coordinates(
    first: dict[str, float],
    second: dict[str, float],
) -> float:
    """Calculate straight-line distance between two coordinate points.

    This is a geometric helper only. Actual travel distance must come from
    routes because terrain and obstacles can make it different from the
    straight-line distance.
    """
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
