"""Deterministic movement through the world's geographic routes.

Movement never invents a destination or travel duration. The pathfinder selects
an available path and this engine calculates the travel time from its routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .geography import Route
from .pathfinding import PathResult, PathfindingEngine
from .world_state import WorldState


@dataclass(frozen=True)
class MovementResult:
    """Result of a completed movement between two locations."""

    origin_id: str
    destination_id: str
    route_ids: tuple[str, ...]
    location_ids: tuple[str, ...]
    total_distance: float
    base_speed: float
    terrain_modifier: float
    difficulty_modifier: float
    travel_minutes: int
    started_at: datetime
    arrived_at: datetime

    @property
    def route_id(self) -> str | None:
        """Backward-compatible direct-route accessor."""
        return self.route_ids[0] if len(self.route_ids) == 1 else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "route_ids": list(self.route_ids),
            "location_ids": list(self.location_ids),
            "total_distance": self.total_distance,
            "base_speed": self.base_speed,
            "terrain_modifier": self.terrain_modifier,
            "difficulty_modifier": self.difficulty_modifier,
            "travel_minutes": self.travel_minutes,
            "started_at": self.started_at.isoformat(),
            "arrived_at": self.arrived_at.isoformat(),
        }


class MovementEngine:
    """Move an actor through valid paths in a WorldState."""

    def __init__(self, world: WorldState) -> None:
        self.world = world
        self.pathfinding = PathfindingEngine(world)

    def find_path(
        self,
        origin_id: str,
        destination_id: str,
        *,
        prefer: str = "distance",
    ) -> PathResult | None:
        """Find a currently available path without changing world state."""
        return self.pathfinding.find_path(
            origin_id,
            destination_id,
            prefer=prefer,
        )

    def travel(
        self,
        origin_id: str,
        destination_id: str,
        *,
        base_speed: float,
        terrain_modifier: float = 1.0,
        difficulty_modifier: float = 1.0,
        prefer: str = "distance",
    ) -> MovementResult:
        """Travel through the cheapest available path.

        ``base_speed`` is expressed in world-distance units per hour.
        Modifiers below 1 slow travel; modifiers above 1 accelerate it.
        The path itself is selected by the deterministic pathfinding engine.
        """
        if origin_id == destination_id:
            raise ValueError("Origine e destinazione devono essere diverse.")

        _positive_number(base_speed, "La velocità base")
        _positive_number(terrain_modifier, "Il modificatore del terreno")
        _positive_number(difficulty_modifier, "Il modificatore della difficoltà")

        path = self.find_path(origin_id, destination_id, prefer=prefer)
        if path is None:
            raise ValueError(
                f"Nessun percorso disponibile tra '{origin_id}' e '{destination_id}'."
            )

        routes = [self.world.get_route(route_id) for route_id in path.route_ids]
        if any(route is None for route in routes):
            raise RuntimeError("Il percorso contiene una rotta non più presente nel mondo.")

        effective_speed = (
            float(base_speed)
            * float(terrain_modifier)
            * float(difficulty_modifier)
        )

        # Each route's difficulty slows the same movement speed. Summing the
        # weighted travel times keeps the calculation deterministic and avoids
        # letting one average difficulty hide a particularly difficult segment.
        travel_hours = sum(
            route.distance * max(route.difficulty, 0.000001) / effective_speed
            for route in routes
        )
        travel_minutes = max(1, int(round(travel_hours * 60)))

        started_at = self.world.clock.current_time
        arrived_at = self.world.advance_time_minutes(travel_minutes)

        return MovementResult(
            origin_id=path.origin_id,
            destination_id=path.destination_id,
            route_ids=path.route_ids,
            location_ids=path.location_ids,
            total_distance=path.total_distance,
            base_speed=float(base_speed),
            terrain_modifier=float(terrain_modifier),
            difficulty_modifier=float(difficulty_modifier),
            travel_minutes=travel_minutes,
            started_at=started_at,
            arrived_at=arrived_at,
        )

    def available_destinations(self, origin_id: str) -> list[str]:
        """Return destinations reachable directly from a location."""
        self.world.require_location(origin_id)
        return [
            route.destination_id
            for route in self.world.routes_from(origin_id, available_only=True)
        ]


def _positive_number(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{label} deve essere un numero positivo.")
