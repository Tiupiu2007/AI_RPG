"""Core persistent state of the AI RPG world.

This module contains only world-state orchestration. Concrete world entities
such as locations remain implemented in their own modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from .locations import Location


@dataclass
class WorldState:
    """Represents the authoritative state of one game world."""

    world_id: str
    name: str
    description: str = ""
    locations: dict[str, Location] = field(default_factory=dict)
    factions: dict[str, Any] = field(default_factory=dict)
    events: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: _utc_now())

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        *,
        world_id: str | None = None,
    ) -> "WorldState":
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Il mondo deve avere un nome.")

        return cls(
            world_id=world_id or str(uuid.uuid4()),
            name=normalized_name,
            description=description.strip(),
        )

    def update(self) -> None:
        """Mark the world as changed."""
        self.updated_at = _utc_now()

    # ---------------------------------------------------------
    # LOCATIONS
    # ---------------------------------------------------------

    def add_location(self, location: Location) -> None:
        """Add a location to the authoritative world state."""
        if not isinstance(location, Location):
            raise TypeError("È possibile aggiungere solo oggetti Location.")
        if location.location_id in self.locations:
            raise ValueError(
                f"La località '{location.location_id}' esiste già nel mondo."
            )

        self.locations[location.location_id] = location
        self.update()

    def get_location(self, location_id: str) -> Location | None:
        """Return a location by ID, or None when it does not exist."""
        return self.locations.get(location_id)

    def require_location(self, location_id: str) -> Location:
        """Return a location or raise when it does not exist."""
        location = self.get_location(location_id)
        if location is None:
            raise KeyError(f"Località non trovata: {location_id}")
        return location

    def remove_location(self, location_id: str) -> Location | None:
        """Remove a location and return it, if present."""
        location = self.locations.pop(location_id, None)
        if location is not None:
            self.update()
        return location

    def find_locations_by_name(self, name: str) -> list[Location]:
        """Find locations by exact case-insensitive name."""
        target = name.strip().casefold()
        if not target:
            return []

        return [
            location
            for location in self.locations.values()
            if location.name.casefold() == target
        ]

    def list_locations(self) -> list[Location]:
        """Return all locations currently present in the world."""
        return list(self.locations.values())

    # ---------------------------------------------------------
    # SERIALIZATION
    # ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the world."""
        return {
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "locations": {
                location_id: location.to_dict()
                for location_id, location in self.locations.items()
            },
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

        locations: dict[str, Location] = {}
        raw_locations = data.get("locations", {})

        if isinstance(raw_locations, dict):
            for location_id, location_data in raw_locations.items():
                if isinstance(location_data, Location):
                    location = location_data
                elif isinstance(location_data, dict):
                    location = Location.from_dict(location_data)
                else:
                    raise TypeError(
                        f"Dati non validi per la località '{location_id}'."
                    )

                locations[location.location_id] = location

        return cls(
            world_id=world_id,
            name=name,
            description=_string_or_empty(data.get("description")),
            locations=locations,
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
