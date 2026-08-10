from __future__ import annotations

from typing import Any

from app.database.characters_db import get_character, save_character
from app.memory.memory import create_memory


def _extra(character: dict[str, Any]) -> dict[str, Any]:
    value = character.get("extra", {})
    return dict(value) if isinstance(value, dict) else {}


def _save(character: dict[str, Any], extra: dict[str, Any]) -> None:
    save_character(
        character["identity"],
        character.get("languages", []),
        extra_data=extra,
        character_id=int(character["id"]),
    )


def execute_character_reaction(character_id: int, action: dict[str, Any]) -> dict[str, Any]:
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")

    if action.get("type") != "character_reaction":
        raise ValueError("Azione non valida per execute_character_reaction.")
    if action.get("character_id") != character_id:
        raise ValueError("La reazione appartiene a un altro personaggio.")

    extra = _extra(character)
    state = extra.get("state", {})
    if not isinstance(state, dict):
        state = {}
    state.update({
        "emotion": action["emotion"],
        "thought": action["thought"],
        "intention": action["intention"],
        "goal": action["goal"],
    })
    extra["state"] = state
    _save(character, extra)
    return state


def execute_actions(character_id: int, actions: list[dict[str, Any]]) -> dict[str, Any]:
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")

    executed: list[dict[str, Any]] = []
    created_memory_ids: list[int] = []

    for action in actions:
        action_type = action["type"]

        if action_type == "character_reaction":
            execute_character_reaction(character_id, action)
            executed.append(action)
            continue

        character = get_character(character_id) or character
        extra = _extra(character)

        if action_type == "create_memory":
            memory_id = create_memory(
                character_id=character_id,
                content=action["content"],
                memory_type=action.get("memory_type", "evento"),
                importance=action["importance"],
                secret=action["secret"],
            )
            created_memory_ids.append(memory_id)

        elif action_type == "relationship_change":
            # Le relazioni verranno spostate in una tabella dedicata nel prossimo
            # passaggio del game engine. Per ora manteniamo la struttura esistente.
            relationships = extra.get("relationships", [])
            if not isinstance(relationships, list):
                relationships = []
            target_id = action["character_b_id"]
            relation = next(
                (item for item in relationships if isinstance(item, dict) and item.get("character_id") == target_id),
                None,
            )
            if relation is None:
                relation = {"character_id": target_id, "trust": 0, "affection": 0, "respect": 0, "hostility": 0}
                relationships.append(relation)
            for field in ("trust", "affection", "respect", "hostility"):
                if field in action:
                    relation[field] = max(-100, min(100, int(relation.get(field, 0)) + action[field]))
            extra["relationships"] = relationships
            _save(character, extra)

        elif action_type == "world_action":
            # La registrazione persistente dell'evento viene fatta dal turn controller,
            # dopo che tutte le azioni sono state validate ed eseguite.
            pass

        executed.append(action)

    character = get_character(character_id) or character
    return {
        "executed_actions": executed,
        "created_memory_ids": created_memory_ids,
        "extra": _extra(character),
    }
