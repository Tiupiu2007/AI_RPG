"""Compatibility wrapper.

The character-turn controller lives in app.game_engine.character_interaction.
This module remains temporarily available so older imports do not break.
"""

from app.game_engine.character_interaction import (
    build_character_context,
    clear_character_conversation,
    get_character_conversation,
    process_character_turn,
)

__all__ = [
    "build_character_context",
    "clear_character_conversation",
    "get_character_conversation",
    "process_character_turn",
]
