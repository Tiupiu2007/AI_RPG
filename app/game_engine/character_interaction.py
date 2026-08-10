from __future__ import annotations

import json
import re

from app.ai_provider import ask_character
from app.database.characters_db import get_character, save_character
from app.game_engine.action_executor import execute_actions
from app.game_engine.action_validator import validate_actions
from app.memory.context import build_continuity_facts
from app.memory.memory import create_event, get_character_memories, get_recent_events
from app.relationships.relationships import ensure_relationship, get_character_relationships


def _identity_dict(identity):
    return {"id": None, "name": identity.name, "surname": identity.surname, "nickname": identity.nickname, "age": identity.age, "birth_date": identity.birth_date, "sex": identity.sex, "race": identity.race, "physical_description": identity.physical_description, "appearance": identity.appearance}


def _player_context(extra):
    player_id = extra.get("player_id")
    player = extra.get("player")
    if not isinstance(player, dict): player = {}
    identity = {key: player.get(key) for key in ("id", "name", "surname", "nickname", "age", "birth_date", "sex", "race", "physical_description", "appearance") if key in player}
    if "id" not in identity and isinstance(player_id, int) and not isinstance(player_id, bool): identity["id"] = player_id
    return {"id": player_id if isinstance(player_id, int) and not isinstance(player_id, bool) else None, "name": player.get("name"), "identity": identity, "role": "PLAYER"}


def _safe_character_list(value):
    if not isinstance(value, list): return []
    result = []
    for item in value:
        if isinstance(item, dict):
            safe = {key: item[key] for key in ("id", "character_id", "name", "surname", "nickname", "role") if key in item}
            if safe: result.append(safe)
    return result


def _safe_relationships(value):
    if not isinstance(value, list): return []
    result = []
    for item in value:
        if isinstance(item, dict):
            safe = {key: item[key] for key in ("character_a_id", "character_b_id", "trust", "affection", "respect", "hostility", "updated_at") if key in item}
            if safe: result.append(safe)
    return result


def _character_conversation(extra):
    conversation = extra.get("conversation", []) if isinstance(extra, dict) else []
    if not isinstance(conversation, list): return []
    cleaned = []
    for item in conversation:
        if not isinstance(item, dict): continue
        role, content = item.get("role"), item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip(): cleaned.append({"role": role, "content": content.strip()})
    return cleaned[-16:]


def _explicit_memory(player_input: str, character_name: str) -> str | None:
    text = " ".join(player_input.strip().split())
    match = re.match(r"^(?:ricordati|ricorda|tienilo a mente|tienilo presente)\s*(?:che\s*)?(.+)$", text, re.IGNORECASE)
    if not match: return None
    fact = match.group(1).strip(" .!?\t\n")
    return f"Il PLAYER ha chiesto a {character_name} di ricordare: {fact}" if fact else None


def _player_reference_hint(player_input: str) -> str:
    """Aggiunge al prompt AI una risoluzione deterministica delle forme in prima persona.

    Serve a impedire che il modello trasformi frasi del PLAYER come
    "Sai dove sono nato?" in domande sulla nascita del CURRENT_CHARACTER.
    Il testo originale non viene modificato nel log o nella memoria: l'hint
    viene usato esclusivamente come istruzione interna per il modello.
    """
    text = " ".join(player_input.strip().split()).lower()
    first_person_markers = (
        " io ", "sono nato", "sono nata", "sono cresciuto", "sono cresciuta",
        "ero ", "avevo ", "ho ", "vivevo ", "abitavo ", "venivo ",
        "mi chiamo", "mio ", "mia ", "miei ", "mie ", "me ", "mi ",
    )
    padded = f" {text} "
    if not any(marker in padded for marker in first_person_markers):
        return player_input

    return (
        f"{player_input}\n\n"
        "[ENGINE — RISOLUZIONE DEI RIFERIMENTI]\n"
        "Le forme in prima persona presenti nel messaggio appartengono al PLAYER, non al CURRENT_CHARACTER. "
        "In particolare, espressioni come 'sono nato', 'sono nata', 'sono cresciuto', 'vivevo', 'ero', "
        "'avevo', 'ho fatto', 'mio', 'mia', 'miei' e 'mie' si riferiscono al PLAYER. "
        "Quindi una domanda come 'Sai dove sono nato?' significa 'Sai dove è nato il PLAYER?'. "
        "NON interpretarla come una domanda sulla nascita del CURRENT_CHARACTER. "
        "Cerca la risposta nelle informazioni che il PLAYER ha comunicato a questo personaggio. "
        "Non trasferire mai un fatto del PLAYER all'identità del CURRENT_CHARACTER."
    )


def _persistent_relationships(character_id: int, character_ids: list[int]) -> list[dict]:
    """Rende disponibili al modello solo relazioni persistenti del personaggio corrente."""
    for target_id in character_ids:
        if target_id == character_id or not isinstance(target_id, int) or isinstance(target_id, bool): continue
        if get_character(target_id) is None: continue
        ensure_relationship(character_id, target_id)
    return _safe_relationships(get_character_relationships(character_id))


def build_character_context(character_id, recent_conversation=None):
    character_data = get_character(character_id)
    if character_data is None: raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    identity = _identity_dict(character_data["identity"])
    identity["id"] = character_id
    extra = character_data.get("extra", {})
    if not isinstance(extra, dict): extra = {}

    def list_value(key):
        value = extra.get(key, [])
        return value if isinstance(value, list) else []

    memories = [m for m in get_character_memories(character_id, limit=20, include_secrets=True) if isinstance(m, dict) and m.get("character_id") == character_id]
    events = [e for e in get_recent_events(character_id, limit=20) if isinstance(e, dict) and e.get("character_id") == character_id]
    present = _safe_character_list(extra.get("characters_present", []))
    involved = _safe_character_list(extra.get("involved_characters", []))
    related_ids = []
    for item in present + involved:
        target = item.get("id", item.get("character_id"))
        if isinstance(target, int) and not isinstance(target, bool): related_ids.append(target)
    relationships = _persistent_relationships(character_id, related_ids)

    return {
        "context_scope": {"character_id": character_id, "memory_scope": f"ONLY_CHARACTER_{character_id}", "event_scope": f"ONLY_CHARACTER_{character_id}", "conversation_scope": f"ONLY_CHARACTER_{character_id}"},
        "roles": {"player": _player_context(extra), "current_character": {"id": character_id, "name": identity.get("name"), "surname": identity.get("surname"), "role": "CURRENT_CHARACTER"}},
        "character": {**identity, "psychology": extra.get("psychology", {}), "personality": extra.get("personality", {}), "statistics": extra.get("statistics", {}), "abilities": extra.get("abilities", []), "skills": extra.get("skills", []), "conditions": extra.get("conditions", {}), "inventory": extra.get("inventory", {}), "magic": extra.get("magic", {})},
        "state": extra.get("state", {}) if isinstance(extra.get("state", {}), dict) else {},
        "memories": memories,
        "relationships": relationships,
        "characters_present": present,
        "scene": {"player": _player_context(extra), "reacting_character_id": character_id, "player_id": extra.get("player_id"), "involved_characters": involved, "available_location_ids": list_value("available_location_ids")},
        "recent_conversation": _character_conversation(extra),
        "recent_events": events,
        "continuity_facts": build_continuity_facts(memories, events, character_id),
    }


def _save_extra(character, extra):
    save_character(character["identity"], character["languages"], extra_data=extra, character_id=character["id"])


def get_character_conversation(character_id):
    character = get_character(character_id)
    if character is None: raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    return _character_conversation(character.get("extra", {}))


def clear_character_conversation(character_id):
    character = get_character(character_id)
    if character is None: raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    extra = character.get("extra", {})
    if not isinstance(extra, dict): extra = {}
    extra["conversation"] = []
    _save_extra(character, extra)


def process_character_turn(character_id, player_input, recent_conversation=None):
    if not isinstance(character_id, int) or isinstance(character_id, bool): raise ValueError("È richiesto l'ID di un personaggio reale.")
    if not isinstance(player_input, str) or not player_input.strip(): raise ValueError("Il messaggio non può essere vuoto.")
    character = get_character(character_id)
    if character is None: raise ValueError(f"Personaggio con ID {character_id} non trovato.")

    conversation = get_character_conversation(character_id)
    context = build_character_context(character_id)
    if context.get("context_scope", {}).get("character_id") != character_id: raise ValueError("Contesto personaggio incoerente.")
    if any(m.get("character_id") != character_id for m in context.get("memories", [])): raise ValueError("Il contesto contiene una memoria appartenente a un altro personaggio.")
    if any(e.get("character_id") != character_id for e in context.get("recent_events", [])): raise ValueError("Il contesto contiene un evento appartenente a un altro personaggio.")

    original_player_input = player_input.strip()
    ai_player_input = _player_reference_hint(original_player_input)
    raw_result = ask_character(context, ai_player_input)
    try: result = json.loads(raw_result)
    except (TypeError, json.JSONDecodeError) as error: raise ValueError("Il game engine ha ricevuto una risposta AI non valida. " f"Risposta ricevuta: {str(raw_result)[:500]}") from error
    if not isinstance(result, dict): raise ValueError("La risposta del game engine deve essere un oggetto JSON. " f"Risposta ricevuta: {str(raw_result)[:500]}")
    narration, actions = result.get("narration"), result.get("actions")
    if not isinstance(narration, str) or not narration.strip(): raise ValueError("La risposta AI non contiene una narration valida. " f"Risposta ricevuta: {str(raw_result)[:1000]}")
    if not isinstance(actions, list): raise ValueError("Le azioni del game engine non sono valide. " f"Risposta ricevuta: {str(raw_result)[:1000]}")

    explicit_memory = _explicit_memory(original_player_input, character["identity"].name)
    if explicit_memory and not any(isinstance(a, dict) and a.get("type") == "create_memory" and a.get("character_id") == character_id for a in actions):
        actions.append({"type": "create_memory", "character_id": character_id, "content": explicit_memory, "memory_type": "fatto_personale", "importance": 8, "secret": False})

    validated_actions = validate_actions(actions, context)
    reaction = next(a for a in validated_actions if a["type"] == "character_reaction")
    execution = execute_actions(character_id, validated_actions)
    event_id = create_event(character_id, "character_interaction", {"player": original_player_input, "character": narration.strip(), "actions": validated_actions})

    character = get_character(character_id)
    if character is None: raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    extra = character.get("extra", {})
    if not isinstance(extra, dict): extra = {}
    conversation = conversation + [{"role": "user", "content": original_player_input}, {"role": "assistant", "content": narration.strip()}]
    extra["conversation"] = conversation[-100:]
    _save_extra(character, extra)
    created_memory_ids = execution.get("created_memory_ids", [])
    if not isinstance(created_memory_ids, list): created_memory_ids = []
    return {"narration": narration.strip(), "character_reaction": reaction, "actions": validated_actions, "executed_actions": execution.get("executed_actions", []), "created_memory_ids": created_memory_ids, "event_id": event_id, "conversation": conversation[-16:]}
