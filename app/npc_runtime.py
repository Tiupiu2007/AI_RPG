from __future__ import annotations

from typing import Any

from app.database.characters_db import get_character, save_character
from app.characters.character_from_description import generate_character_from_description
from app.characters.characters_languages import get_race_languages
from app.characters.characters_profile import generate_character_profile, profile_to_dict
from app.world.runtime import ensure_world, add_character_to_location


def create_npc_from_description(player_id: int, description: str, *, role: str = "npc") -> dict:
    player = get_character(player_id)
    if player is None:
        raise ValueError("Player non trovato.")
    extra = player.get("extra", {}) if isinstance(player.get("extra", {}), dict) else {}
    identity = generate_character_from_description(description)
    profile = profile_to_dict(generate_character_profile({
        "name": identity.name, "surname": identity.surname, "nickname": identity.nickname,
        "age": identity.age, "birth_date": identity.birth_date, "sex": identity.sex,
        "race": identity.race, "physical_description": identity.physical_description,
        "appearance": identity.appearance,
    }))
    from server import generate_statistics
    stats = generate_statistics(identity.race)
    max_health = 70 + stats["constitution"]
    max_stamina = 70 + stats["constitution"] // 2 + stats["agility"] // 2
    max_mana = 50 + stats["intelligence"] // 2 + stats["willpower"] // 2
    npc_extra = {
        "character_role": role,
        "npc": True,
        "statistics": stats,
        "abilities": [],
        "skills": [],
        "conditions": {
            "health": max_health, "max_health": max_health,
            "stamina": max_stamina, "max_stamina": max_stamina,
            "mana": max_mana, "max_mana": max_mana, "status": "Normale",
        },
        "inventory": {},
        "magic": {},
        "psychology": {k: v for k, v in profile.items() if k in {"mental_state","emotional_stability","fears","desires","values","traumas"}},
        "personality": {k: v for k, v in profile.items() if k in {"personality_description","traits","strengths","flaws","habits","social_behavior"}},
        "npc_state": {"emotion": "", "thought": "", "intention": "", "goal": ""},
    }
    npc_id = save_character(identity, get_race_languages(identity.race), extra_data=npc_extra)
    world = ensure_world(extra)
    location_id = extra.get("game_state", {}).get("location")
    add_character_to_location(extra, npc_id, location_id)
    present = extra.get("characters_present", [])
    if not isinstance(present, list):
        present = []
    if npc_id not in [x.get("id") for x in present if isinstance(x, dict)]:
        present.append({"id": npc_id, "role": role})
    extra["characters_present"] = present
    save_character(player["identity"], player["languages"], extra_data=extra, character_id=player_id)
    return {"id": npc_id, "name": identity.name, "surname": identity.surname, "description": description, "role": role}
