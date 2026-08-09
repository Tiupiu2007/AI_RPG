# app/characters/characters.py

from dataclasses import dataclass, field

from app.characters.characters_identity import CharacterIdentity
from app.characters.characters_languages import CharacterLanguage


# =========================================================
# CHARACTER
# =========================================================

@dataclass
class Character:

    # =====================================================
    # IDENTITÀ
    # =====================================================

    identity: CharacterIdentity

    # =====================================================
    # LINGUE
    # =====================================================

    languages: list[CharacterLanguage] = field(
        default_factory=list
    )

    # =====================================================
    # FUTURE SECTIONS
    # =====================================================
    #
    # In futuro verranno aggiunte:
    #
    # statistics
    # derived_statistics
    # abilities
    # skills
    # conditions
    # psychology
    # personality
    # relationships
    # memories
    # etc.
    #
    # Ogni sezione verrà aggiunta
    # separatamente.