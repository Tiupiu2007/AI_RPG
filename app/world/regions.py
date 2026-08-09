"""Large-scale geographic regions and racial concentration territories."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import math
import uuid


@dataclass
class Region:
    """A persistent geographic area larger than an individual location."""

    region_id: str
    name: str
    region_type: str = "region"
    description: str = ""
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0
    parent_region_id: str | None = None
    biome_ids: list[str] = field(default_factory=list)
    location_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, name: str, *, region_type: str = "region", description: str = "", x_min: float, x_max: float, y_min: float, y_max: float, parent_region_id: str | None = None, biome_ids: list[str] | None = None, region_id: str | None = None, metadata: dict[str, Any] | None = None) -> "Region":
        if not isinstance(name, str) or not name.strip():
            raise ValueError("La regione deve avere un nome.")
        if x_max <= x_min or y_max <= y_min:
            raise ValueError("I limiti della regione non sono validi.")
        return cls(region_id or str(uuid.uuid4()), name.strip(), region_type.strip(), description.strip(), float(x_min), float(x_max), float(y_min), float(y_max), parent_region_id, list(biome_ids or []), [], dict(metadata or {}))

    def contains(self, coordinates: dict[str, float]) -> bool:
        x, y = _xy(coordinates)
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def add_location(self, location_id: str) -> None:
        if location_id not in self.location_ids:
            self.location_ids.append(location_id)

    def to_dict(self) -> dict[str, Any]:
        return {"region_id": self.region_id, "name": self.name, "region_type": self.region_type, "description": self.description, "x_min": self.x_min, "x_max": self.x_max, "y_min": self.y_min, "y_max": self.y_max, "parent_region_id": self.parent_region_id, "biome_ids": list(self.biome_ids), "location_ids": list(self.location_ids), "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Region":
        return cls.create(data["name"], region_type=data.get("region_type", "region"), description=data.get("description", ""), x_min=data["x_min"], x_max=data["x_max"], y_min=data["y_min"], y_max=data["y_max"], parent_region_id=data.get("parent_region_id"), biome_ids=data.get("biome_ids", []), region_id=data.get("region_id"), metadata=data.get("metadata", {}))


@dataclass
class RacialTerritory:
    """A concentration zone, not an exclusive race boundary."""

    territory_id: str
    race: str
    name: str
    concentration: float = 1.0
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0
    region_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, race: str, name: str, *, concentration: float, x_min: float, x_max: float, y_min: float, y_max: float, region_id: str | None = None, territory_id: str | None = None, metadata: dict[str, Any] | None = None) -> "RacialTerritory":
        if not race.strip() or not name.strip():
            raise ValueError("Razza e territorio devono avere un nome.")
        if not 0.0 <= concentration <= 1.0:
            raise ValueError("La concentrazione deve essere compresa tra 0 e 1.")
        if x_max <= x_min or y_max <= y_min:
            raise ValueError("I limiti del territorio non sono validi.")
        return cls(territory_id or str(uuid.uuid4()), race.strip(), name.strip(), float(concentration), float(x_min), float(x_max), float(y_min), float(y_max), region_id, dict(metadata or {}))

    def contains(self, coordinates: dict[str, float]) -> bool:
        x, y = _xy(coordinates)
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def to_dict(self) -> dict[str, Any]:
        return {"territory_id": self.territory_id, "race": self.race, "name": self.name, "concentration": self.concentration, "x_min": self.x_min, "x_max": self.x_max, "y_min": self.y_min, "y_max": self.y_max, "region_id": self.region_id, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RacialTerritory":
        return cls.create(data["race"], data["name"], concentration=data.get("concentration", 1.0), x_min=data["x_min"], x_max=data["x_max"], y_min=data["y_min"], y_max=data["y_max"], region_id=data.get("region_id"), territory_id=data.get("territory_id"), metadata=data.get("metadata", {}))


@dataclass
class RegionMap:
    regions: dict[str, Region] = field(default_factory=dict)
    racial_territories: dict[str, RacialTerritory] = field(default_factory=dict)

    def add_region(self, region: Region) -> None:
        if region.region_id in self.regions:
            raise ValueError(f"La regione '{region.region_id}' esiste già.")
        self.regions[region.region_id] = region

    def add_territory(self, territory: RacialTerritory) -> None:
        if territory.territory_id in self.racial_territories:
            raise ValueError(f"Il territorio '{territory.territory_id}' esiste già.")
        if territory.region_id is not None and territory.region_id not in self.regions:
            raise KeyError("Il territorio razziale deve riferirsi a una regione esistente.")
        self.racial_territories[territory.territory_id] = territory

    def region_at(self, coordinates: dict[str, float]) -> Region | None:
        matches = [region for region in self.regions.values() if region.contains(coordinates)]
        return min(matches, key=self._area) if matches else None

    def racial_concentrations_at(self, coordinates: dict[str, float]) -> dict[str, float]:
        values: dict[str, float] = {}
        for territory in self.racial_territories.values():
            if territory.contains(coordinates):
                values[territory.race] = max(values.get(territory.race, 0.0), territory.concentration)
        return values

    def dominant_race_at(self, coordinates: dict[str, float]) -> str | None:
        concentrations = self.racial_concentrations_at(coordinates)
        return max(concentrations, key=concentrations.get) if concentrations else None

    def _area(self, region: Region) -> float:
        return (region.x_max - region.x_min) * (region.y_max - region.y_min)

    def to_dict(self) -> dict[str, Any]:
        return {"regions": {key: value.to_dict() for key, value in self.regions.items()}, "racial_territories": {key: value.to_dict() for key, value in self.racial_territories.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegionMap":
        result = cls()
        for raw in data.get("regions", {}).values():
            region = Region.from_dict(raw)
            result.regions[region.region_id] = region
        for raw in data.get("racial_territories", {}).values():
            territory = RacialTerritory.from_dict(raw)
            result.racial_territories[territory.territory_id] = territory
        return result


def _xy(coordinates: dict[str, float]) -> tuple[float, float]:
    try:
        return float(coordinates["x"]), float(coordinates["y"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Le coordinate devono contenere x e y numerici.") from error
