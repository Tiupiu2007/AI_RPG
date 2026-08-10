"""Settlements built on top of locations and aggregated population."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from .population import Population
from .demography import DemographicState


SETTLEMENT_TYPES = {"camp", "outpost", "village", "hamlet", "town", "city", "capital", "fortress", "ruin"}


@dataclass
class Settlement:
    settlement_id: str
    location_id: str
    name: str
    settlement_type: str
    population: Population = field(default_factory=Population)
    region_id: str | None = None
    description: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    generated_character_ids: list[str] = field(default_factory=list)
    demography: DemographicState | None = None

    @classmethod
    def create(cls, name: str, location_id: str, settlement_type: str, *, population: Population | None = None, region_id: str | None = None, description: str = "", settlement_id: str | None = None, attributes: dict[str, Any] | None = None) -> "Settlement":
        name = name.strip()
        settlement_type = settlement_type.strip().casefold()
        if not name or not location_id.strip():
            raise ValueError("Nome e località dell'insediamento sono obbligatori.")
        if settlement_type not in SETTLEMENT_TYPES:
            raise ValueError(f"Tipo di insediamento non supportato: {settlement_type}")
        result = cls(settlement_id or str(uuid.uuid4()), location_id.strip(), name, settlement_type, population or Population(), region_id, description.strip(), dict(attributes or {}), [], None)
        result.sync_demography()
        return result

    def sync_demography(self) -> DemographicState:
        current_population = int(getattr(self.population, "total", 0))
        if self.demography is None:
            capacity = int(self.attributes.get("carrying_capacity", max(1000, current_population * 2)))
            self.demography = DemographicState(settlement_id=self.settlement_id, population=current_population, carrying_capacity=max(1, capacity))
        else:
            self.demography.population = current_population
        return self.demography

    def apply_demographic_year(self, *, health: float, happiness: float, prosperity: float, security: float) -> int:
        demography = self.sync_demography()
        new_population = demography.simulate_year(health=health, happiness=happiness, prosperity=prosperity, security=security)
        self.population.total = new_population
        return new_population

    def add_generated_character(self, character_id: str) -> None:
        if not character_id.strip():
            raise ValueError("character_id non valido.")
        if character_id not in self.generated_character_ids:
            self.generated_character_ids.append(character_id)

    def to_dict(self) -> dict[str, Any]:
        return {"settlement_id": self.settlement_id, "location_id": self.location_id, "name": self.name, "settlement_type": self.settlement_type, "population": self.population.to_dict(), "region_id": self.region_id, "description": self.description, "attributes": dict(self.attributes), "generated_character_ids": list(self.generated_character_ids), "demography": self.demography.to_dict() if self.demography else None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settlement":
        settlement = cls.create(data["name"], data["location_id"], data["settlement_type"], population=Population.from_dict(data.get("population", {})), region_id=data.get("region_id"), description=data.get("description", ""), settlement_id=data.get("settlement_id"), attributes=data.get("attributes", {}))
        settlement.generated_character_ids = [value for value in data.get("generated_character_ids", []) if isinstance(value, str)]
        if data.get("demography"):
            settlement.demography = DemographicState.from_dict(data["demography"])
        settlement.sync_demography()
        return settlement


@dataclass
class SettlementMap:
    settlements: dict[str, Settlement] = field(default_factory=dict)

    def add(self, settlement: Settlement) -> None:
        if settlement.settlement_id in self.settlements:
            raise ValueError(f"L'insediamento '{settlement.settlement_id}' esiste già.")
        if any(existing.location_id == settlement.location_id for existing in self.settlements.values()):
            raise ValueError("Una località può avere un solo insediamento principale.")
        self.settlements[settlement.settlement_id] = settlement

    def get(self, settlement_id: str) -> Settlement | None:
        return self.settlements.get(settlement_id)

    def at_location(self, location_id: str) -> Settlement | None:
        return next((item for item in self.settlements.values() if item.location_id == location_id), None)

    def in_region(self, region_id: str) -> list[Settlement]:
        return [item for item in self.settlements.values() if item.region_id == region_id]

    def simulate_year(self, *, condition_provider) -> dict[str, int]:
        results: dict[str, int] = {}
        for settlement in self.settlements.values():
            conditions = condition_provider(settlement.settlement_id)
            if conditions is None:
                continue
            results[settlement.settlement_id] = settlement.apply_demographic_year(health=conditions.health, happiness=conditions.happiness, prosperity=conditions.prosperity, security=conditions.security)
        return results

    def to_dict(self) -> dict[str, Any]:
        return {"settlements": {key: value.to_dict() for key, value in self.settlements.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SettlementMap":
        result = cls()
        for raw in data.get("settlements", {}).values():
            settlement = Settlement.from_dict(raw)
            result.settlements[settlement.settlement_id] = settlement
        return result
