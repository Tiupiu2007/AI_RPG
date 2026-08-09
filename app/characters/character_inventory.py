from dataclasses import dataclass, field
from typing import Any


@dataclass
class Armor:
    name: str
    slot: str = ""
    material: str = ""
    condition: float = 100.0
    protection: dict[str, float] = field(default_factory=dict)
    special_properties: list[str] = field(default_factory=list)
    defects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "slot": self.slot,
            "material": self.material,
            "condition": self.condition,
            "protection": dict(self.protection),
            "special_properties": list(self.special_properties),
            "defects": list(self.defects),
        }


@dataclass
class Weapon:
    name: str
    weapon_type: str = ""
    condition: float = 100.0
    damage: dict[str, float] = field(default_factory=dict)
    special_properties: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "weapon_type": self.weapon_type,
            "condition": self.condition,
            "damage": dict(self.damage),
            "special_properties": list(self.special_properties),
        }


@dataclass
class Item:
    name: str
    quantity: int = 1
    category: str = "object"
    weight: float | None = None
    condition: float | None = None
    value: int | float | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "category": self.category,
            "weight": self.weight,
            "condition": self.condition,
            "value": self.value,
            "properties": dict(self.properties),
        }


@dataclass
class Inventory:
    armor: list[Armor] = field(default_factory=list)
    weapons: list[Weapon] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    special_items: list[Item] = field(default_factory=list)
    materials: list[Item] = field(default_factory=list)
    equipped_armor: dict[str, str] = field(default_factory=dict)
    equipped_weapon: str | None = None
    storage: list[Item] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "armor": [item.to_dict() for item in self.armor],
            "weapons": [item.to_dict() for item in self.weapons],
            "items": [item.to_dict() for item in self.items],
            "special_items": [item.to_dict() for item in self.special_items],
            "materials": [item.to_dict() for item in self.materials],
            "equipped_armor": dict(self.equipped_armor),
            "equipped_weapon": self.equipped_weapon,
            "storage": [item.to_dict() for item in self.storage],
        }
