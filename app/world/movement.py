"""Deterministic movement through the world's geographic routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .pathfinding import PathResult, PathfindingEngine
from .world_state import WorldState


@dataclass(frozen=True)
class MovementResult:
    actor_id: str
    origin_id: str
    destination_id: str
    route_ids: tuple[str, ...]
    location_ids: tuple[str, ...]
    biome_sequence: tuple[str | None, ...]
    total_distance: float
    base_speed: float
    terrain_modifier: float
    difficulty_modifier: float
    travel_minutes: int
    started_at: datetime
    arrived_at: datetime

    @property
    def route_id(self) -> str | None:
        return self.route_ids[0] if len(self.route_ids) == 1 else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "route_ids": list(self.route_ids),
            "location_ids": list(self.location_ids),
            "biome_sequence": list(self.biome_sequence),
            "total_distance": self.total_distance,
            "base_speed": self.base_speed,
            "terrain_modifier": self.terrain_modifier,
            "difficulty_modifier": self.difficulty_modifier,
            "travel_minutes": self.travel_minutes,
            "started_at": self.started_at.isoformat(),
            "arrived_at": self.arrived_at.isoformat(),
        }


class MovementEngine:
    """Move actors through valid paths and persist their final position."""

    def __init__(self, world: WorldState) -> None:
        self.world = world
        self.pathfinding = PathfindingEngine(world)

    def find_path(self, origin_id: str, destination_id: str, *, prefer: str = "distance") -> PathResult | None:
        return self.pathfinding.find_path(origin_id, destination_id, prefer=prefer)

    def travel(
        self,
        actor_id: str,
        destination_id: str,
        *,
        base_speed: float,
        terrain_modifier: float = 1.0,
        difficulty_modifier: float = 1.0,
        prefer: str = "distance",
    ) -> MovementResult:
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("actor_id non valido.")
        if not isinstance(destination_id, str) or not destination_id.strip():
            raise ValueError("destination_id non valido.")
        _positive_number(base_speed, "La velocità base")
        _positive_number(terrain_modifier, "Il modificatore del terreno")
        _positive_number(difficulty_modifier, "Il modificatore della difficoltà")

        position = self.world.require_actor_position(actor_id)
        origin_id = position.location_id
        if origin_id == destination_id:
            raise ValueError("L'attore si trova già nella destinazione.")
        if position.is_traveling:
            raise ValueError("L'attore è già in viaggio.")

        path = self.find_path(origin_id, destination_id, prefer=prefer)
        if path is None:
            raise ValueError(f"Nessun percorso disponibile tra '{origin_id}' e '{destination_id}'.")

        routes = [self.world.get_route(route_id) for route_id in path.route_ids]
        if any(route is None for route in routes):
            raise RuntimeError("Il percorso contiene una rotta non più presente nel mondo.")

        biome_sequence = self._path_biomes(path)
        effective_speed = float(base_speed) * float(terrain_modifier) * float(difficulty_modifier)
        travel_hours = sum(route.distance * max(route.difficulty, 0.000001) / effective_speed for route in routes)
        travel_minutes = max(1, int(round(travel_hours * 60)))

        started_at = self.world.clock.current_time
        self.world.begin_actor_travel(actor_id, destination_id, path.route_ids)
        arrived_at = self.world.advance_time_minutes(travel_minutes)
        self.world.arrive_actor(actor_id, destination_id)

        return MovementResult(
            actor_id=actor_id,
            origin_id=origin_id,
            destination_id=destination_id,
            route_ids=path.route_ids,
            location_ids=path.location_ids,
            biome_sequence=tuple(biome_sequence),
            total_distance=path.total_distance,
            base_speed=float(base_speed),
            terrain_modifier=float(terrain_modifier),
            difficulty_modifier=float(difficulty_modifier),
            travel_minutes=travel_minutes,
            started_at=started_at,
            arrived_at=arrived_at,
        )

    def _path_biomes(self, path: PathResult) -> list[str | None]:
        result: list[str | None] = []
        for first_id, second_id in zip(path.location_ids, path.location_ids[1:]):
            transition = self.world.biomes_between_locations(first_id, second_id)
            for biome in transition:
                if not result or result[-1] != biome:
                    result.append(biome)
        return result

    def available_destinations(self, actor_id: str) -> list[str]:
        position = self.world.require_actor_position(actor_id)
        return [route.destination_id for route in self.world.routes_from(position.location_id, available_only=True)]


def _positive_number(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{label} deve essere un numero positivo.")
