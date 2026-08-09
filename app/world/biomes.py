"""Biomes and geographic continuity rules for the world."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BiomeDefinition:
    """Definition of a biome without forcing every location to use it."""

    biome_id: str
    name: str
    climate: str = ""
    terrain: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class BiomeRegion:
    """A persistent region assigning a biome to an area of the world."""

    region_id: str
    biome_id: str
    center: dict[str, float]
    radius: float
    transition_radius: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)

    def contains(self, coordinates: dict[str, float]) -> bool:
        return _distance(self.center, coordinates) <= self.radius

    def transition_strength(self, coordinates: dict[str, float]) -> float:
        distance = _distance(self.center, coordinates)
        if distance <= self.radius:
            return 1.0
        if self.transition_radius <= 0 or distance >= self.radius + self.transition_radius:
            return 0.0
        return 1.0 - ((distance - self.radius) / self.transition_radius)

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "biome_id": self.biome_id,
            "center": dict(self.center),
            "radius": self.radius,
            "transition_radius": self.transition_radius,
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BiomeRegion":
        if not isinstance(data, dict):
            raise TypeError("La regione del bioma deve essere un dizionario.")
        return cls(
            region_id=str(data.get("region_id", "")),
            biome_id=str(data.get("biome_id", "")),
            center=_coordinates(data.get("center")),
            radius=_positive(data.get("radius"), "radius"),
            transition_radius=float(data.get("transition_radius", 0)),
            attributes=dict(data.get("attributes", {})) if isinstance(data.get("attributes"), dict) else {},
        )


@dataclass
class BiomeMap:
    """Persistent biome registry used by WorldState."""

    definitions: dict[str, BiomeDefinition] = field(default_factory=dict)
    regions: dict[str, BiomeRegion] = field(default_factory=dict)

    def add_definition(self, biome: BiomeDefinition) -> None:
        if biome.biome_id in self.definitions:
            raise ValueError(f"Il bioma '{biome.biome_id}' esiste già.")
        self.definitions[biome.biome_id] = biome

    def add_region(self, region: BiomeRegion) -> None:
        if region.region_id in self.regions:
            raise ValueError(f"La regione '{region.region_id}' esiste già.")
        if region.biome_id not in self.definitions:
            raise KeyError(f"Bioma non definito: {region.biome_id}")
        self.regions[region.region_id] = region

    def biome_at(self, coordinates: dict[str, float]) -> str | None:
        candidates = [
            region for region in self.regions.values()
            if region.contains(coordinates)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda region: _distance(region.center, coordinates))
        return candidates[0].biome_id

    def transition_between(self, first: dict[str, float], second: dict[str, float], *, steps: int = 10) -> list[str | None]:
        """Sample a route and return the biome encountered at each point."""
        if steps < 2:
            raise ValueError("steps deve essere almeno 2.")
        result: list[str | None] = []
        for index in range(steps):
            factor = index / (steps - 1)
            point = {
                "x": float(first["x"]) + (float(second["x"]) - float(first["x"])) * factor,
                "y": float(first["y"]) + (float(second["y"]) - float(first["y"])) * factor,
            }
            result.append(self.biome_at(point))
        return _compress(result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "definitions": {
                key: {
                    "biome_id": value.biome_id,
                    "name": value.name,
                    "climate": value.climate,
                    "terrain": value.terrain,
                    "attributes": dict(value.attributes),
                }
                for key, value in self.definitions.items()
            },
            "regions": {key: value.to_dict() for key, value in self.regions.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BiomeMap":
        result = cls()
        for raw in (data.get("definitions", {}) if isinstance(data, dict) else {}).values():
            if isinstance(raw, dict):
                biome = BiomeDefinition(
                    biome_id=str(raw.get("biome_id", "")),
                    name=str(raw.get("name", "")),
                    climate=str(raw.get("climate", "")),
                    terrain=str(raw.get("terrain", "")),
                    attributes=dict(raw.get("attributes", {})) if isinstance(raw.get("attributes"), dict) else {},
                )
                result.definitions[biome.biome_id] = biome
        for raw in (data.get("regions", {}) if isinstance(data, dict) else {}).values():
            if isinstance(raw, dict):
                region = BiomeRegion.from_dict(raw)
                if region.biome_id in result.definitions:
                    result.regions[region.region_id] = region
        return result


def _distance(first: dict[str, float], second: dict[str, float]) -> float:
    return ((float(first["x"]) - float(second["x"])) ** 2 + (float(first["y"]) - float(second["y"])) ** 2) ** 0.5


def _coordinates(value: Any) -> dict[str, float]:
    if not isinstance(value, dict) or "x" not in value or "y" not in value:
        raise ValueError("Una regione deve avere coordinate x e y.")
    return {"x": float(value["x"]), "y": float(value["y"])}


def _positive(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} deve essere positivo.")
    return float(value)


def _compress(values: list[str | None]) -> list[str | None]:
    result: list[str | None] = []
    for value in values:
        if not result or result[-1] != value:
            result.append(value)
    return result
