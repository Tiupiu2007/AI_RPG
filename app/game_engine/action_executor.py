from __future__ import annotations

from typing import Any

from app.database.characters_db import get_character, save_character
from app.memory.memory import create_memory


MAX_EXECUTABLE_ACTIONS = 5


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


def _require_character(character_id: int) -> dict[str, Any]:
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("character_id non valido.")
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    return character


def execute_character_reaction(character_id: int, action: dict[str, Any]) -> dict[str, Any]:
    character = _require_character(character_id)

    if not isinstance(action, dict) or action.get("type") != "character_reaction":
        raise ValueError("Azione non valida per execute_character_reaction.")
    if action.get("character_id") != character_id:
        raise ValueError("La reazione appartiene a un altro personaggio.")

    required = ("emotion", "thought", "intention", "goal")
    for field in required:
        if not isinstance(action.get(field), str):
            raise ValueError(f"character_reaction.{field} non è valido.")

    extra = _extra(character)
    state = extra.get("state", {})
    if not isinstance(state, dict):
        state = {}

    # Lo stato interno è separato dalla narrazione: il modello non modifica
    # direttamente statistiche, salute o altri valori di gioco.
    state.update({
        "emotion": action["emotion"].strip(),
        "thought": action["thought"].strip(),
        "intention": action["intention"].strip(),
        "goal": action["goal"].strip(),
    })
    extra["state"] = state
    _save(character, extra)
    return state


def _execute_relationship_change(
    character_id: int,
    character: dict[str, Any],
    action: dict[str, Any],
) -> None:
    if action.get("character_a_id") != character_id:
        raise ValueError("character_a_id non corrisponde al personaggio reagente.")

    target_id = action.get("character_b_id")
    if not isinstance(target_id, int) or isinstance(target_id, bool):
        raise ValueError("character_b_id non valido.")

    extra = _extra(character)
    relationships = extra.get("relationships", [])
    if not isinstance(relationships, list):
        relationships = []

    relation = next(
        (
            item for item in relationships
            if isinstance(item, dict) and item.get("character_id") == target_id
        ),
        None,
    )
    if relation is None:
        raise ValueError(
            f"La relazione con character_id={target_id} non esiste nel personaggio."
        )

    for field in ("trust", "affection", "respect", "hostility"):
        if field not in action:
            continue
        delta = action[field]
        if not isinstance(delta, int) or isinstance(delta, bool):
            raise ValueError(f"{field} deve essere un intero.")
        relation[field] = max(
            -100,
            min(100, int(relation.get(field, 0)) + delta),
        )

    extra["relationships"] = relationships
    _save(character, extra)


def execute_actions(character_id: int, actions: list[dict[str, Any]]) -> dict[str, Any]:
    """Esegue esclusivamente azioni già validate dal game engine.

    La funzione rimane difensiva perché può essere chiamata anche da altri
    punti del backend. Non modifica statistiche o dati arbitrari provenienti
    direttamente dal modello.
    """
    character = _require_character(character_id)

    if not isinstance(actions, list):
        raise ValueError("actions deve essere una lista.")
    if not actions:
        raise ValueError("Nessuna azione da eseguire.")
    if len(actions) > MAX_EXECUTABLE_ACTIONS:
        raise ValueError(f"Sono consentite al massimo {MAX_EXECUTABLE_ACTIONS} azioni.")

    executed: list[dict[str, Any]] = []
    created_memory_ids: list[int] = []
    reaction_executed = False
    memory_executed = False

    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("Ogni action deve essere un oggetto JSON.")

        action_type = action.get("type")

        if action_type == "character_reaction":
            if reaction_executed:
                raise ValueError("Non è possibile eseguire due character_reaction nello stesso turno.")
            execute_character_reaction(character_id, action)
            reaction_executed = True
            executed.append(dict(action))
            continue

        if action_type == "create_memory":
            if memory_executed:
                raise ValueError("Non è possibile eseguire due create_memory nello stesso turno.")
            memory_id = create_memory(
                character_id=character_id,
                content=action["content"],
                memory_type=action.get("memory_type", "evento"),
                importance=action["importance"],
                secret=action["secret"],
            )
            created_memory_ids.append(memory_id)
            memory_executed = True
            executed.append(dict(action))
            continue

        if action_type == "relationship_change":
            character = get_character(character_id) or character
            _execute_relationship_change(character_id, character, action)
            executed.append(dict(action))
            continue

        if action_type == "world_action":
            # L'azione è intenzionalmente registrata come eseguita ma non
            # altera direttamente il mondo finché non esiste un world manager
            # dedicato. Il turn controller conserva l'evento completo.
            executed.append(dict(action))
            continue

        raise ValueError(f"Tipo di azione non supportato dall'executor: {action_type!r}.")

    if not reaction_executed:
        raise ValueError("Ogni turno deve eseguire una character_reaction.")

    character = get_character(character_id) or character
    return {
        "executed_actions": executed,
        "created_memory_ids": created_memory_ids,
        "extra": _extra(character),
    }
