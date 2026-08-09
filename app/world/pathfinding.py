"""Deterministic pathfinding for the AI RPG world.

Routes form a directed graph. This module finds the cheapest currently
available route without asking the AI to invent geography.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import heapq

from .geography import Route
from .world_state import WorldState


@dataclass(frozen=True)
class PathResult:
    """A complete route through the world graph."""

    origin_id: str
    destination_id: str
    route_ids: tuple[str, ...]
    location_ids: tuple[str, ...]
    total_distance: float
    total_cost: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "route_ids": list(self.route_ids),
            "location_ids": list(self.location_ids),
            "total_distance": self.total_distance,
            "total_cost": self.total_cost,
        }


class PathfindingEngine:
    """Find paths using only the routes stored in WorldState."""

    def __init__(self, world: WorldState) -> None:
        self.world = world

    def find_path(
        self,
        origin_id: str,
        destination_id: str,
        *,
        prefer: str = "distance",
    ) -> PathResult | None:
        """Return the cheapest available path between two locations.

        ``prefer`` can be ``distance`` or ``difficulty``. The search uses
        Dijkstra's algorithm and never traverses unavailable routes.
        """
        if prefer not in {"distance", "difficulty"}:
            raise ValueError("prefer deve essere 'distance' oppure 'difficulty'.")

        self.world.require_location(origin_id)
        self.world.require_location(destination_id)

        if origin_id == destination_id:
            return PathResult(
                origin_id=origin_id,
                destination_id=destination_id,
                route_ids=(),
                location_ids=(origin_id,),
                total_distance=0.0,
                total_cost=0.0,
            )

        queue: list[tuple[float, str]] = [(0.0, origin_id)]
        costs: dict[str, float] = {origin_id: 0.0}
        previous: dict[str, tuple[str, Route]] = {}

        while queue:
            current_cost, current_id = heapq.heappop(queue)

            if current_cost > costs.get(current_id, float("inf")):
                continue
            if current_id == destination_id:
                break

            for route in self.world.routes_from(current_id, available_only=True):
                edge_cost = self._route_cost(route, prefer)
                new_cost = current_cost + edge_cost

                if new_cost < costs.get(route.destination_id, float("inf")):
                    costs[route.destination_id] = new_cost
                    previous[route.destination_id] = (current_id, route)
                    heapq.heappush(queue, (new_cost, route.destination_id))

        if destination_id not in previous:
            return None

        routes: list[Route] = []
        locations: list[str] = [destination_id]
        current = destination_id

        while current != origin_id:
            previous_location, route = previous[current]
            routes.append(route)
            current = previous_location
            locations.append(current)

        routes.reverse()
        locations.reverse()

        return PathResult(
            origin_id=origin_id,
            destination_id=destination_id,
            route_ids=tuple(route.route_id for route in routes),
            location_ids=tuple(locations),
            total_distance=sum(route.distance for route in routes),
            total_cost=costs[destination_id],
        )

    def _route_cost(self, route: Route, prefer: str) -> float:
        if prefer == "distance":
            return route.distance
        return route.distance * route.difficulty
