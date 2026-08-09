# app/characters/characters.py

from dataclasses import dataclass, field
from typing import Any

from app.characters.characters_identity import CharacterIdentity
from app.characters.characters_languages import CharacterLanguage
from app.characters.character_inventory import Inventory
from app.characters.character_magic import MagicBook
from app.characters.character_money import Money


@dataclass
class Character:
    """Complete persistent character container.

    Complex sections remain separate modules so they can evolve without turning
    the character model into one large file.
    """

    identity: CharacterIdentity
    languages: list[CharacterLanguage] = field(default_factory=list)

    # Character systems already being expanded elsewhere in the project can be
    # attached without forcing empty implementation details into this class.
    inventory: Inventory = field(default_factory=Inventory)
    money: Money = field(default_factory=Money)
    magic: MagicBook = field(default_factory=MagicBook)

    # Extensible data for sections that have not yet received their dedicated
    # module (stats, personality, relationships, memories, progression, etc.).
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "languages": [
                {
                    "language_id": language.language_id,
                    "name": language.name,
                    "comprehension": language.comprehension,
                    "speaking": language.speaking,
                    "writing": language.writing,
                }
                for language in self.languages
            ],
            "inventory": self.inventory.to_dict(),
            "money": self.money.to_dict(),
            "magic": self.magic.to_dict(),
            "extra": dict(self.extra),
        }
