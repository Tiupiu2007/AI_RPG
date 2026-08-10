import json

from app.ai_provider import ask_character
from app.database.characters_db import get_character, save_character
from app.game_engine.action_executor import execute_actions
from app.game_engine.action_validator import validate_actions
from app.memory.context import build_continuity_facts
from app.memory.memory import create_event, get_character_memories, get_recent_events


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


def _player_context(extra):
    """Espone al modello solo l'identità del PLAYER, mai il suo contenitore extra."""
    player_id = extra.get("player_id")
    player = extra.get("player")
    if not isinstance(player, dict):
        player = {}
    identity = {
        key: player.get(key)
        for key in (
            "id", "name", "surname", "nickname", "age", "birth_date",
            "sex", "race", "physical_description", "appearance",
        )
        if key in player
    }
    if "id" not in identity and isinstance(player_id, int) and not isinstance(player_id, bool):
        identity["id"] = player_id
    return {
        "id": player_id if isinstance(player_id, int) and not isinstance(player_id, bool) else None,
        "name": player.get("name"),
        "identity": identity,
        "role": "PLAYER",
    }


def _safe_character_list(value):
    """Riduce gli altri personaggi a metadati pubblici, impedendo leakage di memoria."""
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        safe = {}
        for key in ("id", "character_id", "name", "surname", "nickname", "role"):
            if key in item:
                safe[key] = item[key]
        if safe:
            result.append(safe)
    return result


def _safe_relationships(value):
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        safe = {
            key: item[key]
            for key in ("character_id", "trust", "affection", "respect", "hostility")
            if key in item
        }
        if safe:
            result.append(safe)
    return result


def _character_conversation(extra):
    """Restituisce esclusivamente la cronologia salvata sul personaggio corrente."""
    conversation = extra.get("conversation", []) if isinstance(extra, dict) else []
    if not isinstance(conversation, list):
        return []
    cleaned = []
    for item in conversation:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"}:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        cleaned.append({"role": role, "content": content.strip()})
    return cleaned[-16:]


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

    stored_conversation = _character_conversation(extra)

    memories = [
        memory for memory in get_character_memories(character_id, limit=20, include_secrets=True)
        if isinstance(memory, dict) and memory.get("character_id") == character_id
    ]
    events = [
        event for event in get_recent_events(character_id, limit=20)
        if isinstance(event, dict) and event.get("character_id") == character_id
    ]
    continuity_facts = build_continuity_facts(memories, events, character_id=character_id)

    return {
        "context_scope": {
            "character_id": character_id,
            "memory_scope": f"ONLY_CHARACTER_{character_id}",
            "event_scope": f"ONLY_CHARACTER_{character_id}",
            "conversation_scope": f"ONLY_CHARACTER_{character_id}",
        },
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
        "relationships": _safe_relationships(extra.get("relationships", [])),
        "characters_present": _safe_character_list(extra.get("characters_present", [])),
        "scene": {
            "player": _player_context(extra),
            "reacting_character_id": character_id,
            "player_id": extra.get("player_id"),
            "involved_characters": _safe_character_list(extra.get("involved_characters", [])),
            "available_location_ids": list_value("available_location_ids"),
        },
        "recent_conversation": stored_conversation,
        "recent_events": events,
        "continuity_facts": continuity_facts,
    }


def _save_extra(character, extra):
    save_character(
        character["identity"],
        character["languages"],
        extra_data=extra,
        character_id=character["id"],
    )


def get_character_conversation(character_id):
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    return _character_conversation(character.get("extra", {}))


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

    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")

    # La cronologia del frontend non è autorevole e non viene mai usata per il prompt.
    # Rimane nel parametro solo per compatibilità con vecchie versioni dell'API.
    conversation = get_character_conversation(character_id)
    context = build_character_context(character_id)

    scope = context.get("context_scope", {})
    if scope.get("character_id") != character_id:
        raise ValueError("Contesto personaggio incoerente.")
    if any(memory.get("character_id") != character_id for memory in context.get("memories", [])):
        raise ValueError("Il contesto contiene una memoria appartenente a un altro personaggio.")
    if any(event.get("character_id") != character_id for event in context.get("recent_events", [])):
        raise ValueError("Il contesto contiene un evento appartenente a un altro personaggio.")

    raw_result = ask_character(context, player_input.strip())
    try:
        result = json.loads(raw_result)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(
            "Il game engine ha ricevuto una risposta AI non valida. "
            f"Risposta ricevuta: {str(raw_result)[:500]}"
        ) from error

    if not isinstance(result, dict):
        raise ValueError(
            "La risposta del game engine deve essere un oggetto JSON. "
            f"Risposta ricevuta: {str(raw_result)[:500]}"
        )

    narration = result.get("narration")
    actions = result.get("actions")
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError(
            "La risposta AI non contiene una narration valida. "
            f"Risposta ricevuta: {str(raw_result)[:1000]}"
        )
    if not isinstance(actions, list):
        raise ValueError(
            "Le azioni del game engine non sono valide. "
            f"Risposta ricevuta: {str(raw_result)[:1000]}"
        )

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

    created_memory_ids = execution.get("created_memory_ids", [])
    if not isinstance(created_memory_ids, list):
        created_memory_ids = []

    return {
        "narration": narration.strip(),
        "character_reaction": reaction,
        "actions": validated_actions,
        "executed_actions": execution.get("executed_actions", []),
        "created_memory_ids": created_memory_ids,
        "event_id": event_id,
        "conversation": conversation[-16:],
    }
