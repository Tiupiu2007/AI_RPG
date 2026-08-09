"""Persistent positions for actors in the AI RPG world."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActorPosition:
    """Current geographic position of an actor."""

    actor_id: str
    location_id: str
    previous_location_id: str | None = None
    is_traveling: bool = False
    destination_id: str | None = None
    route_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def begin_travel(
        self,
        destination_id: str,
        route_ids: tuple[str, ...],
    ) -> None:
        if not destination_id.strip():
            raise ValueError("La destinazione non può essere vuota.")
        if not route_ids:
            raise ValueError("Un viaggio deve avere almeno una rotta.")
        self.is_traveling = True
        self.destination_id = destination_id
        self.route_ids = tuple(route_ids)

    def arrive(self, destination_id: str) -> None:
        if not destination_id.strip():
            raise ValueError("La destinazione non può essere vuota.")
        self.previous_location_id = self.location_id
        self.location_id = destination_id
        self.is_traveling = False
        self.destination_id = None
        self.route_ids = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "location_id": self.location_id,
            "previous_location_id": self.previous_location_id,
            "is_traveling": self.is_traveling,
            "destination_id": self.destination_id,
            "route_ids": list(self.route_ids),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActorPosition":
        if not isinstance(data, dict):
            raise TypeError("La posizione dell'attore deve essere un dizionario.")
        actor_id = data.get("actor_id")
        location_id = data.get("location_id")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("ActorPosition: actor_id non valido.")
        if not isinstance(location_id, str) or not location_id.strip():
            raise ValueError("ActorPosition: location_id non valido.")
        route_ids = data.get("route_ids", [])
        return cls(
            actor_id=actor_id,
            location_id=location_id,
            previous_location_id=data.get("previous_location_id"),
            is_traveling=bool(data.get("is_traveling", False)),
            destination_id=data.get("destination_id"),
            route_ids=tuple(route_ids) if isinstance(route_ids, list) else (),
            metadata=dict(data.get("metadata", {})) if isinstance(data.get("metadata"), dict) else {},
        )
