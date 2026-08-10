"""Aggregated population data for settlements and regions.

Individual NPCs are intentionally not generated here. The world stores
population statistically and creates concrete characters only when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class PopulationGroup:
    group_id: str
    race: str
    count: int
    share: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, race: str, count: int, *, share: float | None = None, group_id: str | None = None, attributes: dict[str, Any] | None = None) -> "PopulationGroup":
        race = race.strip()
        if not race:
            raise ValueError("La razza deve avere un nome.")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("La popolazione deve essere un intero >= 0.")
        if share is not None and not 0.0 <= share <= 1.0:
            raise ValueError("La percentuale deve essere compresa tra 0 e 1.")
        return cls(group_id or str(uuid.uuid4()), race, count, share, dict(attributes or {}))

    def to_dict(self) -> dict[str, Any]:
        return {"group_id": self.group_id, "race": self.race, "count": self.count, "share": self.share, "attributes": dict(self.attributes)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PopulationGroup":
        return cls.create(data["race"], data["count"], share=data.get("share"), group_id=data.get("group_id"), attributes=data.get("attributes", {}))


@dataclass
class Population:
    total: int = 0
    groups: dict[str, PopulationGroup] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.recalculate_total()

    def add_group(self, group: PopulationGroup) -> None:
        if group.group_id in self.groups:
            raise ValueError(f"Il gruppo di popolazione '{group.group_id}' esiste già.")
        self.groups[group.group_id] = group
        self.recalculate_total()

    def set_race_count(self, race: str, count: int) -> PopulationGroup:
        race = race.strip()
        if not race:
            raise ValueError("La razza deve avere un nome.")
        existing = next((group for group in self.groups.values() if group.race.casefold() == race.casefold()), None)
        if existing is None:
            existing = PopulationGroup.create(race, count)
            self.groups[existing.group_id] = existing
        else:
            if count < 0:
                raise ValueError("La popolazione non può essere negativa.")
            existing.count = count
        self.recalculate_total()
        return existing

    def get_race_count(self, race: str) -> int:
        return sum(group.count for group in self.groups.values() if group.race.casefold() == race.strip().casefold())

    def distribution(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for group in self.groups.values():
            result[group.race] = result.get(group.race, 0) + group.count
        return result

    def recalculate_total(self) -> None:
        self.total = sum(group.count for group in self.groups.values())
        if self.total:
            for group in self.groups.values():
                group.share = group.count / self.total
        else:
            for group in self.groups.values():
                group.share = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"total": self.total, "groups": {key: value.to_dict() for key, value in self.groups.items()}, "attributes": dict(self.attributes)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Population":
        population = cls(attributes=dict(data.get("attributes", {})))
        for raw in data.get("groups", {}).values():
            group = PopulationGroup.from_dict(raw)
            population.groups[group.group_id] = group
        population.recalculate_total()
        return population
