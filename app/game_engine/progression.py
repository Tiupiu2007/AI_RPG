from __future__ import annotations

from app.database.characters_db import get_character, save_character

ACTION_STAT = {
    "attack": "strength",
    "defend": "constitution",
    "move": "agility",
    "inspect": "perception",
    "interact": "intelligence",
    "talk": "charisma",
    "cast_magic": "willpower",
}


def apply_progression(character_id: int, action_type: str, successful: bool) -> dict:
    """Progressione minima e autorevole condivisa da PLAYER e NPC."""
    character = get_character(character_id)
    if character is None:
        return {}
    extra = character.get("extra", {}) if isinstance(character.get("extra", {}), dict) else {}
    progression = extra.get("progression", {}) if isinstance(extra.get("progression", {}), dict) else {}
    xp = int(progression.get("experience", 0) or 0)
    if successful:
        xp += 1
    progression["experience"] = xp
    progression.setdefault("practice", {})
    stat = ACTION_STAT.get(action_type)
    gained = None
    if successful and stat:
        practice = int(progression["practice"].get(stat, 0) or 0) + 1
        progression["practice"][stat] = practice
        if practice >= 10:
            progression["practice"][stat] = 0
            stats = extra.get("statistics", {}) if isinstance(extra.get("statistics", {}), dict) else {}
            if stat in stats:
                old = int(stats[stat])
                stats[stat] = min(100, old + 1)
                extra["statistics"] = stats
                gained = {"stat": stat, "from": old, "to": stats[stat]}
    extra["progression"] = progression
    save_character(character["identity"], character["languages"], extra_data=extra, character_id=character_id)
    return {"experience": xp, "stat_gain": gained}
