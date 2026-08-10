"""Persistent factions and territorial influence for the AI RPG world."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class Faction:
    faction_id: str
    name: str
    faction_type: str = "organization"
    description: str = ""
    goals: list[str] = field(default_factory=list)
    member_ids: list[str] = field(default_factory=list)
    controlled_region_ids: list[str] = field(default_factory=list)
    controlled_location_ids: list[str] = field(default_factory=list)
    influence: dict[str, float] = field(default_factory=dict)
    relations: dict[str, float] = field(default_factory=dict)
    resources: dict[str, float] = field(default_factory=dict)
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, name: str, *, faction_type: str = "organization", description: str = "", goals: list[str] | None = None, faction_id: str | None = None, metadata: dict[str, Any] | None = None) -> "Faction":
        name = name.strip()
        if not name:
            raise ValueError("La fazione deve avere un nome.")
        return cls(faction_id or str(uuid.uuid4()), name, faction_type.strip() or "organization", description.strip(), list(goals or []), metadata=dict(metadata or {}))

    def set_relation(self, faction_id: str, value: float) -> None:
        if not -1.0 <= value <= 1.0:
            raise ValueError("La relazione deve essere compresa tra -1 e 1.")
        self.relations[faction_id] = float(value)

    def set_influence(self, area_id: str, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("L'influenza deve essere compresa tra 0 e 1.")
        self.influence[area_id] = float(value)

    def add_member(self, actor_id: str) -> None:
        if actor_id not in self.member_ids:
            self.member_ids.append(actor_id)

    def control_region(self, region_id: str) -> None:
        if region_id not in self.controlled_region_ids:
            self.controlled_region_ids.append(region_id)

    def control_location(self, location_id: str) -> None:
        if location_id not in self.controlled_location_ids:
            self.controlled_location_ids.append(location_id)

    def apply_settlement_influence(self, *, settlement_id: str, prosperity: float, stability: float, security: float, influence: float, governance: float = 0.0) -> dict[str, float]:
        """Return deterministic pressure applied by this faction to a settlement.

        Influence and governance are explicit inputs; the faction does not invent
        events. Positive governance improves stability/security, while negative
        governance represents harmful or coercive control.
        """
        influence = max(0.0, min(1.0, influence))
        governance = max(-1.0, min(1.0, governance))
        controlled = settlement_id in self.controlled_location_ids
        if controlled:
            influence = max(influence, 0.75)

        governance_effect = governance * influence
        security_delta = governance_effect * 15.0
        stability_delta = governance_effect * 12.0
        prosperity_delta = governance_effect * 8.0

        if self.faction_type.casefold() in {"criminal", "bandit", "cult"}:
            security_delta -= 10.0 * influence
            stability_delta -= 7.0 * influence
            prosperity_delta -= 4.0 * influence

        return {"security_delta": security_delta, "stability_delta": stability_delta, "prosperity_delta": prosperity_delta, "influence": influence}

    def to_dict(self) -> dict[str, Any]:
        return {"faction_id": self.faction_id, "name": self.name, "faction_type": self.faction_type, "description": self.description, "goals": list(self.goals), "member_ids": list(self.member_ids), "controlled_region_ids": list(self.controlled_region_ids), "controlled_location_ids": list(self.controlled_location_ids), "influence": dict(self.influence), "relations": dict(self.relations), "resources": dict(self.resources), "active": self.active, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Faction":
        faction = cls.create(data["name"], faction_type=data.get("faction_type", "organization"), description=data.get("description", ""), goals=data.get("goals", []), faction_id=data.get("faction_id"), metadata=data.get("metadata", {}))
        faction.member_ids = list(data.get("member_ids", []))
        faction.controlled_region_ids = list(data.get("controlled_region_ids", []))
        faction.controlled_location_ids = list(data.get("controlled_location_ids", []))
        faction.influence = {str(k): float(v) for k, v in data.get("influence", {}).items()}
        faction.relations = {str(k): float(v) for k, v in data.get("relations", {}).items()}
        faction.resources = {str(k): float(v) for k, v in data.get("resources", {}).items()}
        faction.active = bool(data.get("active", True))
        return faction


@dataclass
class FactionMap:
    factions: dict[str, Faction] = field(default_factory=dict)

    def add(self, faction: Faction) -> None:
        if faction.faction_id in self.factions:
            raise ValueError(f"La fazione '{faction.faction_id}' esiste già.")
        self.factions[faction.faction_id] = faction

    def get(self, faction_id: str) -> Faction | None:
        return self.factions.get(faction_id)

    def remove(self, faction_id: str) -> Faction | None:
        return self.factions.pop(faction_id, None)

    def active(self) -> list[Faction]:
        return [faction for faction in self.factions.values() if faction.active]

    def relation(self, first_id: str, second_id: str) -> float | None:
        faction = self.get(first_id)
        if faction is None:
            return None
        return faction.relations.get(second_id)

    def factions_controlling_region(self, region_id: str) -> list[Faction]:
        return [f for f in self.factions.values() if region_id in f.controlled_region_ids and f.active]

    def factions_controlling_location(self, location_id: str) -> list[Faction]:
        return [f for f in self.factions.values() if location_id in f.controlled_location_ids and f.active]

    def settlement_influence(self, settlement_id: str) -> list[tuple[Faction, dict[str, float]]]:
        result: list[tuple[Faction, dict[str, float]]] = []
        for faction in self.active():
            influence = faction.influence.get(settlement_id, 0.0)
            if settlement_id in faction.controlled_location_ids or influence > 0.0:
                result.append((faction, {"influence": influence}))
        return result

    def to_dict(self) -> dict[str, Any]:
        return {"factions": {key: faction.to_dict() for key, faction in self.factions.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FactionMap":
        result = cls()
        for raw in data.get("factions", {}).values():
            faction = Faction.from_dict(raw)
            result.factions[faction.faction_id] = faction
        return result
