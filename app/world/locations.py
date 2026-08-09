"""Flexible world locations.

A location stores only the information that is actually known or relevant.
Missing optional details are intentionally left absent instead of being
invented by the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class Location:
    """A place that exists in the authoritative World State."""

    location_id: str
    name: str
    location_type: str
    description: str = ""

    # Geographic position is optional until geography is established.
    coordinates: dict[str, float] | None = None

    # Flexible fields allow villages and capitals to contain different data.
    attributes: dict[str, Any] = field(default_factory=dict)

    # References to other world entities are stored by ID.
    faction_ids: list[str] = field(default_factory=list)
    character_ids: list[str] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)

    # Information discovered by the player/character is tracked separately
    # from objective location data. The knowledge system will refine this later.
    discovered_by: set[str] = field(default_factory=set)

    @classmethod
    def create(
        cls,
        name: str,
        location_type: str,
        description: str = "",
        *,
        location_id: str | None = None,
        coordinates: dict[str, float] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> "Location":
        """Create a location without requiring optional world details."""
        normalized_name = name.strip()
        normalized_type = location_type.strip()

        if not normalized_name:
            raise ValueError("La località deve avere un nome.")
        if not normalized_type:
            raise ValueError("La località deve avere un tipo.")

        normalized_coordinates = _normalize_coordinates(coordinates)

        return cls(
            location_id=location_id or str(uuid.uuid4()),
            name=normalized_name,
            location_type=normalized_type,
            description=description.strip(),
            coordinates=normalized_coordinates,
            attributes=dict(attributes or {}),
        )

    def update(self, **changes: Any) -> None:
        """Apply explicit changes without inventing missing information."""
        allowed = {
            "name",
            "location_type",
            "description",
            "coordinates",
            "attributes",
        }

        for key, value in changes.items():
            if key not in allowed:
                raise ValueError(f"Campo località non modificabile: {key}")

            if key == "name":
                value = str(value).strip()
                if not value:
                    raise ValueError("La località deve avere un nome.")
            elif key == "location_type":
                value = str(value).strip()
                if not value:
                    raise ValueError("La località deve avere un tipo.")
            elif key == "description":
                value = str(value).strip()
            elif key == "coordinates":
                value = _normalize_coordinates(value)
            elif key == "attributes":
                if not isinstance(value, dict):
                    raise TypeError("Gli attributi della località devono essere un dizionario.")
                value = dict(value)

            setattr(self, key, value)

    def add_faction(self, faction_id: str) -> None:
        _append_unique(self.faction_ids, faction_id)

    def add_character(self, character_id: str) -> None:
        _append_unique(self.character_ids, character_id)

    def add_event(self, event_id: str) -> None:
        _append_unique(self.event_ids, event_id)

    def mark_discovered_by(self, knowledge_holder_id: str) -> None:
        if not isinstance(knowledge_holder_id, str) or not knowledge_holder_id.strip():
            raise ValueError("Il soggetto della scoperta non è valido.")
        self.discovered_by.add(knowledge_holder_id)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-friendly location data."""
        return {
            "location_id": self.location_id,
            "name": self.name,
            "location_type": self.location_type,
            "description": self.description,
            "coordinates": self.coordinates,
            "attributes": self.attributes,
            "faction_ids": list(self.faction_ids),
            "character_ids": list(self.character_ids),
            "event_ids": list(self.event_ids),
            "discovered_by": sorted(self.discovered_by),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Location":
        """Rebuild a location from serialized data."""
        if not isinstance(data, dict):
            raise TypeError("La località deve essere un dizionario.")

        location_id = data.get("location_id")
        name = data.get("name")
        location_type = data.get("location_type")

        if not isinstance(location_id, str) or not location_id.strip():
            raise ValueError("Location: location_id non valido.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Location: name non valido.")
        if not isinstance(location_type, str) or not location_type.strip():
            raise ValueError("Location: location_type non valido.")

        return cls(
            location_id=location_id,
            name=name,
            location_type=location_type,
            description=data.get("description", "") if isinstance(data.get("description", ""), str) else "",
            coordinates=_normalize_coordinates(data.get("coordinates")),
            attributes=dict(data.get("attributes", {})) if isinstance(data.get("attributes"), dict) else {},
            faction_ids=_string_list(data.get("faction_ids")),
            character_ids=_string_list(data.get("character_ids")),
            event_ids=_string_list(data.get("event_ids")),
            discovered_by=set(_string_list(data.get("discovered_by"))),
        )


def _append_unique(values: list[str], value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("L'identificativo non è valido.")
    if value not in values:
        values.append(value)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _normalize_coordinates(value: Any) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("Le coordinate devono essere un dizionario.")

    result: dict[str, float] = {}
    for key, coordinate in value.items():
        if not isinstance(key, str):
            raise TypeError("Le chiavi delle coordinate devono essere stringhe.")
        if not isinstance(coordinate, (int, float)) or isinstance(coordinate, bool):
            raise TypeError(f"Coordinata non numerica: {key}")
        result[key] = float(coordinate)

    return result
