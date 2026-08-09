"""Deterministic movement through the world's geographic routes.

Movement never invents a destination or travel duration. The caller must
provide an existing route and the engine derives elapsed time from route data
and movement speed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .geography import Route
from .world_state import WorldState


@dataclass(frozen=True)
class MovementResult:
    """Result of a completed movement between two locations."""

    origin_id: str
    destination_id: str
    route_id: str
    distance: float
    base_speed: float
    terrain_modifier: float
    difficulty_modifier: float
    travel_minutes: int
    started_at: datetime
    arrived_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "route_id": self.route_id,
            "distance": self.distance,
            "base_speed": self.base_speed,
            "terrain_modifier": self.terrain_modifier,
            "difficulty_modifier": self.difficulty_modifier,
            "travel_minutes": self.travel_minutes,
            "started_at": self.started_at.isoformat(),
            "arrived_at": self.arrived_at.isoformat(),
        }


class MovementEngine:
    """Moves an actor through valid routes in a WorldState."""

    def __init__(self, world: WorldState) -> None:
        self.world = world

    def travel(
        self,
        origin_id: str,
        destination_id: str,
        *,
        base_speed: float,
        terrain_modifier: float = 1.0,
        difficulty_modifier: float = 1.0,
    ) -> MovementResult:
        """Travel along a direct available route.

        ``base_speed`` is expressed in world-distance units per hour.
        Modifiers below 1 slow travel; modifiers above 1 accelerate it.
        """
        if origin_id == destination_id:
            raise ValueError("Origine e destinazione devono essere diverse.")

        self.world.require_location(origin_id)
        self.world.require_location(destination_id)

        route = self._find_route(origin_id, destination_id)
        if route is None:
            raise ValueError(
                f"Nessun percorso disponibile tra '{origin_id}' e '{destination_id}'."
            )

        _positive_number(base_speed, "La velocità base")
        _positive_number(terrain_modifier, "Il modificatore del terreno")
        _positive_number(difficulty_modifier, "Il modificatore della difficoltà")

        effective_speed = (
            float(base_speed)
            * float(terrain_modifier)
            / max(float(route.difficulty), 0.000001)
            * float(difficulty_modifier)
        )

        if effective_speed <= 0:
            raise ValueError("La velocità effettiva deve essere positiva.")

        travel_hours = route.distance / effective_speed
        travel_minutes = max(1, int(round(travel_hours * 60)))

        started_at = self.world.clock.current_time
        arrived_at = self.world.advance_time_minutes(travel_minutes)

        return MovementResult(
            origin_id=route.origin_id,
            destination_id=route.destination_id,
            route_id=route.route_id,
            distance=route.distance,
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

    def _find_route(self, origin_id: str, destination_id: str) -> Route | None:
        for route in self.world.routes_from(origin_id, available_only=True):
            if route.destination_id == destination_id:
                return route
        return None


def _positive_number(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{label} deve essere un numero positivo.")
