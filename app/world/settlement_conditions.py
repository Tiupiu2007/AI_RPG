"""Deterministic condition model for world settlements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


@dataclass
class SettlementConditions:
    settlement_id: str
    prosperity: float = 50.0
    stability: float = 50.0
    security: float = 50.0
    health: float = 50.0
    happiness: float = 50.0
    development: float = 0.0
    food_pressure: float = 0.0
    resource_pressure: float = 0.0

    def normalize(self) -> None:
        self.prosperity = _clamp(self.prosperity)
        self.stability = _clamp(self.stability)
        self.security = _clamp(self.security)
        self.health = _clamp(self.health)
        self.happiness = _clamp(self.happiness)
        self.development = _clamp(self.development)
        self.food_pressure = _clamp(self.food_pressure)
        self.resource_pressure = _clamp(self.resource_pressure)

    def apply_daily_conditions(self, *, unmet_needs: dict[str, float], total_requirements: dict[str, float], trade_access: float = 0.0, security_pressure: float = 0.0) -> None:
        unmet_ratio = 0.0
        if total_requirements:
            unmet_ratio = min(1.0, sum(unmet_needs.values()) / max(sum(total_requirements.values()), 1e-9))
        food_unmet = unmet_needs.get("food", unmet_needs.get("cibo", 0.0))
        food_req = total_requirements.get("food", total_requirements.get("cibo", 0.0))
        food_ratio = min(1.0, food_unmet / max(food_req, 1e-9)) if food_req else 0.0

        self.food_pressure = _clamp(food_ratio * 100.0)
        self.resource_pressure = _clamp(unmet_ratio * 100.0)

        self.health += 3.0 * (1.0 - unmet_ratio) - 7.0 * food_ratio
        self.happiness += 2.0 * (trade_access / 100.0) - 5.0 * unmet_ratio - 2.0 * security_pressure / 100.0
        self.security -= security_pressure * 0.03
        self.prosperity += 2.0 * (trade_access / 100.0) - 4.0 * unmet_ratio
        self.stability += 1.5 * (self.happiness - 50.0) / 50.0 - 3.0 * unmet_ratio - 1.5 * security_pressure / 100.0
        self.development += max(-1.0, min(1.0, (self.prosperity - 50.0) / 50.0)) * 0.5
        self.normalize()

    def apply_security_state(self, *, security: float, crime: float, unrest: float) -> None:
        """Feed the security subsystem back into settlement conditions."""
        security = _clamp(security)
        crime = _clamp(crime)
        unrest = _clamp(unrest)

        self.security = security
        self.happiness += (security - 50.0) * 0.08 - (crime - 20.0) * 0.04 - unrest * 0.03
        self.stability += (security - 50.0) * 0.05 - unrest * 0.04
        self.prosperity += (security - 50.0) * 0.025 - crime * 0.015
        self.normalize()

    def overall(self) -> float:
        return _clamp(self.prosperity * 0.20 + self.stability * 0.20 + self.security * 0.15 + self.health * 0.20 + self.happiness * 0.15 + self.development * 0.10)

    def to_dict(self) -> dict[str, Any]:
        return {"settlement_id": self.settlement_id, "prosperity": self.prosperity, "stability": self.stability, "security": self.security, "health": self.health, "happiness": self.happiness, "development": self.development, "food_pressure": self.food_pressure, "resource_pressure": self.resource_pressure}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SettlementConditions":
        result = cls(settlement_id=data["settlement_id"], prosperity=data.get("prosperity", 50), stability=data.get("stability", 50), security=data.get("security", 50), health=data.get("health", 50), happiness=data.get("happiness", 50), development=data.get("development", 0), food_pressure=data.get("food_pressure", 0), resource_pressure=data.get("resource_pressure", 0))
        result.normalize()
        return result


@dataclass
class SettlementConditionMap:
    settlements: dict[str, SettlementConditions] = None

    def __post_init__(self) -> None:
        if self.settlements is None:
            self.settlements = {}

    def add(self, conditions: SettlementConditions) -> None:
        if conditions.settlement_id in self.settlements:
            raise ValueError("Condizioni dell'insediamento già presenti.")
        conditions.normalize()
        self.settlements[conditions.settlement_id] = conditions

    def get(self, settlement_id: str) -> SettlementConditions | None:
        return self.settlements.get(settlement_id)

    def to_dict(self) -> dict[str, Any]:
        return {"settlements": {k: v.to_dict() for k, v in self.settlements.items()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SettlementConditionMap":
        result = cls()
        for raw in data.get("settlements", {}).values():
            condition = SettlementConditions.from_dict(raw)
            result.settlements[condition.settlement_id] = condition
        return result
