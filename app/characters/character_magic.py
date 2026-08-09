from dataclasses import dataclass, field
from typing import Any


DEFAULT_MAGIC_CATEGORIES = [
    "fuoco", "acqua", "aria", "terra", "ghiaccio", "fulmine",
    "luce", "oscurita", "vita", "morte", "natura", "metallo",
    "spazio", "tempo", "telecinesi", "illusione", "evocazione",
    "barriere", "potenziamento", "maledizioni", "purificazione",
    "spirituale", "mentale", "dimensionale", "sangue", "arcana",
]


@dataclass
class LearnedMagic:
    name: str
    category: str
    description: str = ""
    effect: str = ""
    level: int = 1
    mastery: float = 0.0
    cost: dict[str, float] = field(default_factory=dict)
    conditions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    source: str = ""
    variants: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "effect": self.effect,
            "level": self.level,
            "mastery": self.mastery,
            "cost": dict(self.cost),
            "conditions": list(self.conditions),
            "limitations": list(self.limitations),
            "source": self.source,
            "variants": list(self.variants),
        }


@dataclass
class MagicBook:
    learned: dict[str, list[LearnedMagic]] = field(default_factory=dict)

    def add(self, magic: LearnedMagic) -> None:
        self.learned.setdefault(magic.category, []).append(magic)

    def to_dict(self) -> dict[str, Any]:
        return {
            category: [magic.to_dict() for magic in spells]
            for category, spells in self.learned.items()
        }
