"""Deterministic demographic and settlement development rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DemographicState:
    settlement_id: str
    population: int
    carrying_capacity: int = 1000
    birth_rate: float = 0.012
    death_rate: float = 0.008
    migration_rate: float = 0.002
    development_level: float = 0.0

    def simulate_year(self, *, health: float, happiness: float, prosperity: float, security: float) -> int:
        if self.population < 0 or self.carrying_capacity < 1:
            raise ValueError("Stato demografico non valido.")
        quality = max(0.0, min(1.0, (health + happiness + prosperity + security) / 400.0))
        pressure = max(0.0, min(1.0, self.population / self.carrying_capacity))
        births = self.population * self.birth_rate * (0.5 + quality * 0.5)
        deaths = self.population * self.death_rate * (1.5 - quality * 0.5)
        migration = self.population * self.migration_rate * (quality - 0.5)
        growth = births - deaths + migration
        if pressure > 1.0:
            growth -= self.population * min(0.05, (pressure - 1.0) * 0.05)
        self.population = max(0, int(round(self.population + growth)))
        self.development_level = max(0.0, min(100.0, self.development_level + (quality - 0.5) * 4.0))
        return self.population

    def to_dict(self) -> dict[str, Any]:
        return {"settlement_id": self.settlement_id, "population": self.population, "carrying_capacity": self.carrying_capacity, "birth_rate": self.birth_rate, "death_rate": self.death_rate, "migration_rate": self.migration_rate, "development_level": self.development_level}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DemographicState":
        return cls(settlement_id=data["settlement_id"], population=int(data.get("population", 0)), carrying_capacity=int(data.get("carrying_capacity", 1000)), birth_rate=float(data.get("birth_rate", 0.012)), death_rate=float(data.get("death_rate", 0.008)), migration_rate=float(data.get("migration_rate", 0.002)), development_level=float(data.get("development_level", 0.0)))
