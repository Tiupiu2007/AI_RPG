from __future__ import annotations

import json
import uuid
from typing import Any

from app.ai_provider import ask_ollama
from app.database.characters_db import get_character, save_character
from app.characters.characters_identity import CharacterIdentity
from app.characters.characters_languages import get_race_languages
from app.characters.characters_profile import generate_character_profile, profile_to_dict
from app.world.runtime import ensure_world, save_world, add_character_to_location
from app.world.locations import Location


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def get_player_character():
    from app.database.characters_db import get_all_identities, get_character
    for item in get_all_identities():
        character = get_character(item["id"])
        if character and isinstance(character.get("extra"), dict) and character["extra"].get("player_character"):
            return character
    return None


def _generated_player_extra(identity: CharacterIdentity, profile: dict) -> dict:
    from server import generate_statistics
    stats = generate_statistics(identity.race)
    max_health = 70 + stats["constitution"]
    max_stamina = 70 + stats["constitution"] // 2 + stats["agility"] // 2
    max_mana = 50 + stats["intelligence"] // 2 + stats["willpower"] // 2
    return {
        "player_character": True,
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
        "story_chat": [],
        "world_canon": [],
        "campaign": None,
    }


def create_player_from_description(description: str) -> dict:
    from app.characters.character_from_description import generate_character_from_description
    description = str(description or "").strip()
    if not description:
        raise ValueError("Descrivi il personaggio oppure chiedi all'IA di generarlo.")
    if get_player_character() is not None:
        raise ValueError("Esiste già un personaggio giocatore.")
    identity = generate_character_from_description(description)
    profile = profile_to_dict(generate_character_profile({
        "name": identity.name, "surname": identity.surname, "nickname": identity.nickname,
        "age": identity.age, "birth_date": identity.birth_date, "sex": identity.sex,
        "race": identity.race, "physical_description": identity.physical_description,
        "appearance": identity.appearance,
    }))
    extra = _generated_player_extra(identity, profile)
    player_id = save_character(identity, get_race_languages(identity.race), extra_data=extra)
    return get_character(player_id)


def generate_player(description: str = "") -> dict:
    from app.characters.characters_races import get_available_races
    from app.characters.characters_identity import generate_identity
    if get_player_character() is not None:
        raise ValueError("Esiste già un personaggio giocatore.")
    description = str(description or "").strip()
    if description:
        return create_player_from_description(description)
    races = get_available_races()
    if not races:
        raise ValueError("Non sono presenti razze disponibili.")
    import random
    weights = [max(0.0, float(r.rarity)) for r in races]
    identity = generate_identity(random.choices(races, weights=weights if any(weights) else None, k=1)[0].name)
    profile = profile_to_dict(generate_character_profile({
        "name": identity.name, "surname": identity.surname, "nickname": identity.nickname,
        "age": identity.age, "birth_date": identity.birth_date, "sex": identity.sex,
        "race": identity.race, "physical_description": identity.physical_description,
        "appearance": identity.appearance,
    }))
    extra = _generated_player_extra(identity, profile)
    player_id = save_character(identity, get_race_languages(identity.race), extra_data=extra)
    return get_character(player_id)


def _seed_prompt(player: dict, request: str) -> str:
    return f"""
Sei il generatore della situazione iniziale di un RPG narrativo persistente.

Il giocatore possiede già questo personaggio:
{_json({
    "id": player["id"],
    "name": player["identity"].name,
    "age": player["identity"].age,
    "race": player["identity"].race,
    "appearance": player["identity"].appearance,
    "personality": player.get("extra", {}).get("personality", {}),
})}

Richiesta di partenza del giocatore:
{request or "(nessuna: inventa tu una situazione iniziale coerente e concreta)"}

Genera SOLO una BASE DI PARTENZA, non una storia completa.
Il mondo deve essere sufficientemente definito da permettere il primo turno, ma il resto
deve rimanere aperto alla scoperta. Non creare un protagonista speciale senza motivo.
Non creare profezie o misteri automaticamente. Non decidere azioni, pensieri o emozioni del PLAYER.

Restituisci JSON:
{{
  "world_name": "nome",
  "world_description": "breve descrizione delle regole/ambientazione già stabilite",
  "genre": "string",
  "tone": "string",
  "rules": ["regole concrete del mondo"],
  "starting_location": {{
    "name": "nome",
    "type": "città/strada/stanza/ecc",
    "description": "ciò che è realmente presente all'inizio"
  }},
  "player_situation": "situazione concreta in cui si trova il PLAYER all'inizio",
  "initial_npcs": [
    {{
      "description": "identità e ruolo di una persona già presente, solo se serve",
      "importance": "minor|major"
    }}
  ],
  "canon_facts": ["fatti persistenti già stabiliti"]
}}
Limita gli NPC iniziali a quelli realmente necessari per la scena.
""".strip()


def create_story(player_id: int, request: str = "", generate: bool = True) -> dict:
    player = get_character(player_id)
    if player is None:
        raise ValueError("Personaggio giocatore non trovato.")
    extra = player.get("extra", {})
    if not isinstance(extra, dict) or not extra.get("player_character"):
        raise ValueError("Il personaggio indicato non è il protagonista del giocatore.")

    prompt = str(request or "").strip()
    if generate and not prompt:
        prompt = "(genera una situazione iniziale originale e plausibile)"
    raw = ask_ollama(
        """Sei un world-builder per un RPG persistente. Restituisci esclusivamente JSON valido.
La base iniziale deve essere concreta, coerente e aperta. Non completare l'intera storia.
Non inventare azioni o pensieri del giocatore.""",
        _seed_prompt(player, prompt),
    )
    try:
        seed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("L'IA non ha generato una base di storia valida.") from error
    if not isinstance(seed, dict):
        raise ValueError("La base della storia deve essere un oggetto JSON.")

    # Il mondo della campagna appartiene al personaggio giocatore e viene riutilizzato da tutti i turni successivi.
    world = ensure_world(extra)
    world.name = str(seed.get("world_name") or world.name).strip() or world.name
    world.description = str(seed.get("world_description") or "").strip()

    starting = seed.get("starting_location") if isinstance(seed.get("starting_location"), dict) else {}
    location = Location.create(
        str(starting.get("name") or "Luogo di partenza"),
        str(starting.get("type") or "luogo"),
        str(starting.get("description") or seed.get("player_situation") or ""),
        location_id=f"start-{uuid.uuid4().hex[:12]}",
    )
    world.locations[location.location_id] = location
    extra["world_id"] = world.world_id
    extra["world_name"] = world.name
    extra["world_description"] = world.description
    extra["game_state"] = {
        "location": location.location_id,
        "flags": {},
        "active_effects": {},
        "turn": 0,
    }
    location.add_character(str(player_id))
    save_world(extra)
    extra["characters_present"] = []
    extra["involved_characters"] = []
    extra["world_canon"] = [str(x).strip() for x in seed.get("canon_facts", []) if isinstance(x, str) and x.strip()][:100]
    extra["campaign"] = {
        "id": uuid.uuid4().hex,
        "request": prompt,
        "genre": seed.get("genre", ""),
        "tone": seed.get("tone", ""),
        "rules": seed.get("rules", []) if isinstance(seed.get("rules"), list) else [],
        "opening": str(seed.get("player_situation") or "").strip(),
        "started": True,
    }
    extra["story_chat"] = [{"role": "assistant", "content": extra["campaign"]["opening"]}] if extra["campaign"]["opening"] else []
    extra["quests"] = []
    extra.pop("combat_state", None)
    save_character(player["identity"], player["languages"], extra_data=extra, character_id=player_id)
    # Initial NPCs are generated lazily by the narrative system. The seed only records
    # the descriptions that justify their existence; no NPC is created unnecessarily.
    pending = [
        item for item in seed.get("initial_npcs", [])
        if isinstance(item, dict) and isinstance(item.get("description"), str) and item["description"].strip()
    ][:6]
    extra["pending_npcs"] = []
    save_character(player["identity"], player["languages"], extra_data=extra, character_id=player_id)

    from app.npc_runtime import create_npc_from_description
    created_npcs = []
    for item in pending:
        try:
            created_npcs.append(create_npc_from_description(player_id, item["description"], role=item.get("role", "npc")))
        except Exception:
            continue

    return {"player_id": player_id, "campaign": extra["campaign"], "world": {"id": world.world_id, "name": world.name, "description": world.description}, "starting_location": location.to_dict(), "opening": extra["campaign"]["opening"], "canon_facts": extra["world_canon"], "npcs": created_npcs}


def get_story_setup(player_id: int) -> dict:
    player = get_character(player_id)
    if player is None:
        raise ValueError("Personaggio non trovato.")
    extra = player.get("extra", {}) if isinstance(player.get("extra", {}), dict) else {}
    return {
        "has_story": bool(isinstance(extra.get("campaign"), dict) and extra["campaign"].get("started")),
        "campaign": extra.get("campaign"),
        "player": {
            "id": player_id,
            "name": player["identity"].name,
            "race": player["identity"].race,
            "age": player["identity"].age,
        },
    }
