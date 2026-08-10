import json

from app.ai_provider import ask_character
from app.database.characters_db import get_character, save_character
from app.game_engine.action_executor import execute_actions
from app.game_engine.action_validator import validate_actions
from app.memory.context import build_continuity_facts
from app.memory.memory import create_event, get_character_memories, get_recent_events


def _identity_dict(identity):
    return {
        "id": None, "name": identity.name, "surname": identity.surname,
        "nickname": identity.nickname, "age": identity.age,
        "birth_date": identity.birth_date, "sex": identity.sex, "race": identity.race,
        "physical_description": identity.physical_description, "appearance": identity.appearance,
    }


def _player_context(extra):
    player_id = extra.get("player_id")
    player = extra.get("player")
    if not isinstance(player, dict):
        player = {}
    return {
        "id": player_id if isinstance(player_id, int) else None,
        "name": player.get("name"),
        "identity": player,
        "role": "PLAYER",
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

    def list_value(key):
        value = extra.get(key, [])
        return value if isinstance(value, list) else []

    stored_conversation = list_value("conversation")
    if not stored_conversation and isinstance(recent_conversation, list):
        stored_conversation = recent_conversation

    memories = get_character_memories(character_id, limit=40, include_secrets=True)
    events = get_recent_events(character_id, limit=40)
    continuity_facts = build_continuity_facts(memories, events)

    return {
        "roles": {
            "player": _player_context(extra),
            "current_character": {
                "id": character_id,
                "name": identity.get("name"),
                "surname": identity.get("surname"),
                "role": "CURRENT_CHARACTER",
            },
        },
        "character": {
            **identity,
            "psychology": extra.get("psychology", {}),
            "personality": extra.get("personality", {}),
            "statistics": extra.get("statistics", {}),
            "abilities": extra.get("abilities", []),
            "skills": extra.get("skills", []),
            "conditions": extra.get("conditions", {}),
            "inventory": extra.get("inventory", {}),
            "magic": extra.get("magic", {}),
        },
        "state": extra.get("state", {}) if isinstance(extra.get("state", {}), dict) else {},
        "memories": memories,
        "relationships": list_value("relationships"),
        "characters_present": list_value("characters_present"),
        "scene": {
            "player": _player_context(extra),
            "reacting_character_id": character_id,
            "player_id": extra.get("player_id"),
            "involved_characters": list_value("involved_characters"),
            "available_location_ids": list_value("available_location_ids"),
        },
        "recent_conversation": stored_conversation[-16:],
        "recent_events": events,
        "continuity_facts": continuity_facts,
    }


def _save_extra(character, extra):
    save_character(
        character["identity"], character["languages"],
        extra_data=extra, character_id=character["id"],
    )


def get_character_conversation(character_id):
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    extra = character.get("extra", {})
    conversation = extra.get("conversation", []) if isinstance(extra, dict) else []
    return conversation if isinstance(conversation, list) else []


def clear_character_conversation(character_id):
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    extra = character.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    extra["conversation"] = []
    _save_extra(character, extra)


def process_character_turn(character_id, player_input, recent_conversation=None):
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("È richiesto l'ID di un personaggio reale.")
    if not isinstance(player_input, str) or not player_input.strip():
        raise ValueError("Il messaggio non può essere vuoto.")

    if get_character(character_id) is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")

    conversation = get_character_conversation(character_id)
    if not conversation and isinstance(recent_conversation, list):
        conversation = recent_conversation[-16:]

    context = build_character_context(character_id, conversation)
    raw_result = ask_character(context, player_input.strip())
    try:
        result = json.loads(raw_result)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("Il game engine ha ricevuto una risposta AI non valida.") from error

    if not isinstance(result, dict):
        raise ValueError("La risposta del game engine deve essere un oggetto JSON.")

    narration = result.get("narration")
    actions = result.get("actions")
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError("La risposta AI non contiene una narration valida.")
    if not isinstance(actions, list):
        raise ValueError("Le azioni del game engine non sono valide.")

    validated_actions = validate_actions(actions, context)
    reaction = next(a for a in validated_actions if a["type"] == "character_reaction")
    execution = execute_actions(character_id, validated_actions)

    event_id = create_event(
        character_id,
        "character_interaction",
        {
            "player": player_input.strip(),
            "character": narration.strip(),
            "actions": validated_actions,
        },
    )

    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    extra = character.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    conversation = conversation + [
        {"role": "user", "content": player_input.strip()},
        {"role": "assistant", "content": narration.strip()},
    ]
    extra["conversation"] = conversation[-100:]
    _save_extra(character, extra)

    return {
        "narration": narration.strip(),
        "character_reaction": reaction,
        "actions": validated_actions,
        "executed_actions": execution["executed_actions"],
        "created_memory_ids": execution.get("created_memory_ids", []),
        "event_id": event_id,
        "conversation": conversation[-16:],
    }
