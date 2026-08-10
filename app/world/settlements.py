"""Settlements built on top of locations and aggregated population."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from .population import Population
from .demography import DemographicState


SETTLEMENT_TYPES = {"camp", "outpost", "hamlet", "village", "town", "city", "capital", "fortress", "ruin"}

# Population thresholds are deliberately broad: population alone never forces
# a promotion when the settlement is a fortress, capital, or ruin.
SETTLEMENT_TIERS = {
    "camp": (0, 49),
    "outpost": (50, 199),
    "hamlet": (200, 499),
    "village": (500, 1999),
    "town": (2000, 9999),
    "city": (10000, 49999),
    "capital": (50000, None),
}


def _population_tier(population: int) -> str:
    for settlement_type, (minimum, maximum) in SETTLEMENT_TIERS.items():
        if population >= minimum and (maximum is None or population <= maximum):
            return settlement_type
    return "capital"


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

    def update_settlement_type(self, *, prosperity: float, stability: float, security: float) -> str:
        """Update ordinary settlement tiers from population and conditions.

        Special types (capital, fortress, ruin) are never overwritten here.
        A settlement needs both enough population and acceptable conditions to
        grow. Severe conditions can cause an ordinary settlement to decline.
        """
        if self.settlement_type in {"capital", "fortress", "ruin"}:
            return self.settlement_type

        population = int(getattr(self.population, "total", 0))
        target = _population_tier(population)
        quality = (prosperity + stability + security) / 3.0

        current_min = SETTLEMENT_TIERS.get(self.settlement_type, (0, None))[0]
        target_min = SETTLEMENT_TIERS.get(target, (0, None))[0]

        if quality >= 55.0 and target_min > current_min:
            self.settlement_type = target
        elif quality < 25.0 and target_min < current_min:
            self.settlement_type = target
        elif quality < 15.0 and population < current_min:
            self.settlement_type = target

        return self.settlement_type

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
            population = settlement.apply_demographic_year(health=conditions.health, happiness=conditions.happiness, prosperity=conditions.prosperity, security=conditions.security)
            settlement.update_settlement_type(prosperity=conditions.prosperity, stability=conditions.stability, security=conditions.security)
            results[settlement.settlement_id] = population
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
