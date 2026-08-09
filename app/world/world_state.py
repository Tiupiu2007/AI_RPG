"""Core persistent state of the AI RPG world.

This module intentionally contains only the world-state container. Geography,
locations, time, factions, events and other systems will be implemented in
separate modules and attached to this state later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class WorldState:
    """Represents the authoritative state of one game world.

    The class deliberately does not impose a rigid schema on future world
    entities. Each subsystem can add its own structured data while the world
    state remains the authoritative container.
    """

    world_id: str
    name: str
    description: str = ""

    # Future world subsystems populate these collections.
    locations: dict[str, Any] = field(default_factory=dict)
    factions: dict[str, Any] = field(default_factory=dict)
    events: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ISO-8601 UTC timestamp of the last state change.
    updated_at: str = field(default_factory=lambda: _utc_now())

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        *,
        world_id: str | None = None,
    ) -> "WorldState":
        """Create a new world state in memory."""
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Il mondo deve avere un nome.")

        return cls(
            world_id=world_id or str(uuid.uuid4()),
            name=normalized_name,
            description=description.strip(),
        )

    def update(self) -> None:
        """Mark the world as changed.

        Persistence is intentionally handled by a future repository/storage
        layer rather than by this model itself.
        """
        self.updated_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation of the world state."""
        return {
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "locations": self.locations,
            "factions": self.factions,
            "events": self.events,
            "conditions": self.conditions,
            "metadata": self.metadata,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldState":
        """Rebuild a world state from serialized data."""
        if not isinstance(data, dict):
            raise TypeError("Lo stato del mondo deve essere un dizionario.")

        world_id = data.get("world_id")
        name = data.get("name")

        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("WorldState: world_id non valido.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("WorldState: name non valido.")

        return cls(
            world_id=world_id,
            name=name,
            description=_string_or_empty(data.get("description")),
            locations=_dict_or_empty(data.get("locations")),
            factions=_dict_or_empty(data.get("factions")),
            events=_dict_or_empty(data.get("events")),
            conditions=_dict_or_empty(data.get("conditions")),
            metadata=_dict_or_empty(data.get("metadata")),
            updated_at=_string_or_empty(data.get("updated_at")) or _utc_now(),
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
