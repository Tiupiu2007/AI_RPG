"""Deterministic security and crime model for settlements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


@dataclass
class SecurityState:
    settlement_id: str
    security: float = 50.0
    crime: float = 20.0
    law_enforcement: float = 50.0
    corruption: float = 10.0
    unrest: float = 0.0
    incidents: int = 0
    modifiers: dict[str, float] = field(default_factory=dict)

    def normalize(self) -> None:
        self.security = _clamp(self.security)
        self.crime = _clamp(self.crime)
        self.law_enforcement = _clamp(self.law_enforcement)
        self.corruption = _clamp(self.corruption)
        self.unrest = _clamp(self.unrest)
        self.incidents = max(0, int(self.incidents))

    def simulate_day(self, *, prosperity: float = 50.0, stability: float = 50.0, population_pressure: float = 0.0, external_threat: float = 0.0) -> dict[str, float | int]:
        poverty_pressure = max(0.0, 50.0 - prosperity) / 50.0
        instability_pressure = max(0.0, 50.0 - stability) / 50.0
        pressure = _clamp(population_pressure) / 100.0
        threat = _clamp(external_threat) / 100.0
        effective_enforcement = max(0.0, (self.law_enforcement - self.corruption) / 100.0)

        self.crime += poverty_pressure * 1.5 + instability_pressure * 1.2 + pressure * 0.8 + threat * 0.5 - effective_enforcement * 1.8
        self.crime += self.modifiers.get("crime", 0.0)
        self.unrest += instability_pressure * 1.5 + self.crime / 100.0 - effective_enforcement * 1.0
        self.unrest += self.modifiers.get("unrest", 0.0)

        self.security += effective_enforcement * 2.0 - self.crime * 0.025 - self.unrest * 0.02 - threat * 1.5
        self.security += self.modifiers.get("security", 0.0)

        incident_probability = max(0.0, min(0.95, self.crime / 100.0 * 0.12 + self.unrest / 100.0 * 0.08 + threat * 0.05))
        self.incidents += int(incident_probability > 0.08)
        self.normalize()
        return {"security": self.security, "crime": self.crime, "law_enforcement": self.law_enforcement, "corruption": self.corruption, "unrest": self.unrest, "incidents": self.incidents}

    def apply_incident(self, severity: float = 10.0) -> None:
        severity = _clamp(severity)
        self.incidents += 1
        self.security -= severity * 0.15
        self.unrest += severity * 0.20
        self.crime += severity * 0.05
        self.normalize()

    def to_dict(self) -> dict[str, Any]:
        return {"settlement_id": self.settlement_id, "security": self.security, "crime": self.crime, "law_enforcement": self.law_enforcement, "corruption": self.corruption, "unrest": self.unrest, "incidents": self.incidents, "modifiers": dict(self.modifiers)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SecurityState":
        result = cls(settlement_id=data["settlement_id"], security=data.get("security", 50), crime=data.get("crime", 20), law_enforcement=data.get("law_enforcement", 50), corruption=data.get("corruption", 10), unrest=data.get("unrest", 0), incidents=data.get("incidents", 0), modifiers=data.get("modifiers", {}))
        result.normalize()
        return result


@dataclass
class SecurityMap:
    settlements: dict[str, SecurityState] = field(default_factory=dict)

    def add(self, state: SecurityState) -> None:
        if state.settlement_id in self.settlements:
            raise ValueError("Stato di sicurezza già presente.")
        state.normalize()
        self.settlements[state.settlement_id] = state

    def get(self, settlement_id: str) -> SecurityState | None:
        return self.settlements.get(settlement_id)

    def to_dict(self) -> dict[str, Any]:
        return {"settlements": {k: v.to_dict() for k, v in self.settlements.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SecurityMap":
        result = cls()
        for raw in data.get("settlements", {}).values():
            state = SecurityState.from_dict(raw)
            result.settlements[state.settlement_id] = state
        return result
