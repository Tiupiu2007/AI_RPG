import json

from app.ai_provider import ask_character
from app.database.characters_db import get_character


def _identity_dict(identity):
    return {
        "id": None,
        "name": identity.name,
        "surname": identity.surname,
        "nickname": identity.nickname,
        "age": identity.age,
        "birth_date": identity.birth_date,
        "sex": identity.sex,
        "race": identity.race,
        "physical_description": identity.physical_description,
        "appearance": identity.appearance,
    }


def build_character_context(character_id, recent_conversation=None):
    character_data = get_character(character_id)
    if character_data is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")

    identity = _identity_dict(character_data["identity"])
    identity["id"] = character_id
    extra = character_data.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}

    state = extra.get("state", {})
    if not isinstance(state, dict):
        state = {}

    memories = extra.get("memories", [])
    if not isinstance(memories, list):
        memories = []

    relationships = extra.get("relationships", [])
    if not isinstance(relationships, list):
        relationships = []

    recent_events = extra.get("recent_events", [])
    if not isinstance(recent_events, list):
        recent_events = []

    if not isinstance(recent_conversation, list):
        recent_conversation = []

    character = {
        **identity,
        "psychology": extra.get("psychology", {}),
        "personality": extra.get("personality", {}),
        "statistics": extra.get("statistics", {}),
        "abilities": extra.get("abilities", []),
        "skills": extra.get("skills", []),
        "conditions": extra.get("conditions", {}),
        "inventory": extra.get("inventory", {}),
        "magic": extra.get("magic", {}),
    }

    return {
        "character": character,
        "state": state,
        "memories": memories,
        "relationships": relationships,
        "characters_present": extra.get("characters_present", []),
        "scene": {
            "player": extra.get("player"),
            "reacting_character_id": character_id,
            "player_id": extra.get("player_id"),
            "involved_characters": extra.get("involved_characters", []),
        },
        "recent_conversation": recent_conversation[-16:],
        "recent_events": recent_events[-16:],
    }


def process_character_turn(character_id, player_input, recent_conversation=None):
    context = build_character_context(character_id, recent_conversation)
    raw_result = ask_character(context, player_input)

    try:
        result = json.loads(raw_result)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("Il game engine ha ricevuto una risposta AI non valida.") from error

    if not isinstance(result, dict):
        raise ValueError("La risposta del game engine deve essere un oggetto JSON.")

    actions = result.get("actions", [])
    if not isinstance(actions, list):
        raise ValueError("Le azioni del game engine non sono valide.")

    reaction = next(
        (
            action for action in actions
            if isinstance(action, dict)
            and action.get("type") == "character_reaction"
            and action.get("character_id") == character_id
        ),
        None,
    )

    if reaction is None:
        raise ValueError("Il game engine non ha prodotto una character_reaction valida.")

    return {
        "narration": str(result.get("narration", "")).strip(),
        "character_reaction": reaction,
        "actions": actions,
    }
