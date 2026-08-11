from __future__ import annotations

from typing import Any

from app.database.characters_db import get_character, save_character
from app.memory.memory import create_memory
from app.relationships.relationships import change_relationship

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

    for field in ("emotion", "thought", "intention", "goal"):
        if not isinstance(action.get(field), str):
            raise ValueError(f"character_reaction.{field} non è valido.")

    extra = _extra(character)
    state = extra.get("state", {})
    if not isinstance(state, dict):
        state = {}
    state.update({
        "emotion": action["emotion"].strip(),
        "thought": action["thought"].strip(),
        "intention": action["intention"].strip(),
        "goal": action["goal"].strip(),
    })
    extra["state"] = state
    _save(character, extra)
    return state


def execute_combat_action(
    character_id: int,
    action: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Invia una combat_action al combat engine senza permettere all'AI di applicare direttamente gli effetti."""
    if not isinstance(action, dict) or action.get("type") != "combat_action":
        raise ValueError("Azione non valida per execute_combat_action.")
    if action.get("character_id") != character_id:
        raise ValueError("La combat_action appartiene a un altro personaggio.")

    # Import locale: il game engine di combattimento è il livello che decide
    # danni, costi, condizioni, morte e altri effetti reali.
    try:
        from app.combat.combat_engine import resolve_combat_action
    except ImportError as error:
        raise ValueError(
            "Il combat engine non è ancora disponibile. "
            "Creare app/combat/combat_engine.py prima di eseguire una combat_action."
        ) from error

    result = resolve_combat_action(
        character_id=character_id,
        action=dict(action),
        context=context if isinstance(context, dict) else {},
    )

    if not isinstance(result, dict):
        raise ValueError("Il combat engine deve restituire un dizionario.")

    return result


def execute_actions(
    character_id: int,
    actions: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Esegue esclusivamente azioni già validate dal game engine."""
    character = _require_character(character_id)
    if not isinstance(actions, list):
        raise ValueError("actions deve essere una lista.")
    if not actions:
        raise ValueError("Nessuna azione da eseguire.")
    if len(actions) > MAX_EXECUTABLE_ACTIONS:
        raise ValueError(f"Sono consentite al massimo {MAX_EXECUTABLE_ACTIONS} azioni.")

    executed: list[dict[str, Any]] = []
    created_memory_ids: list[int] = []
    combat_results: list[dict[str, Any]] = []
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

        elif action_type == "create_memory":
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

        elif action_type == "relationship_change":
            if action.get("character_a_id") != character_id:
                raise ValueError("character_a_id non corrisponde al personaggio reagente.")
            target_id = action["character_b_id"]
            deltas = {
                field: action[field]
                for field in ("trust", "affection", "respect", "hostility")
                if field in action
            }
            relation = change_relationship(character_id, target_id, **deltas)
            executed.append({**action, "result": relation})
            continue

        elif action_type == "world_action":
            # Le azioni del mondo vengono gestite dal relativo livello quando
            # sarà implementata la simulazione persistente del mondo.
            pass

        elif action_type == "combat_action":
            combat_result = execute_combat_action(character_id, action, context=context)
            combat_results.append(combat_result)
            executed.append({**action, "result": combat_result})
            continue

        else:
            raise ValueError(f"Tipo di azione non supportato dall'executor: {action_type!r}.")

        executed.append(dict(action))

    if not reaction_executed:
        raise ValueError("Ogni turno deve eseguire una character_reaction.")

    character = get_character(character_id) or character
    return {
        "executed_actions": executed,
        "created_memory_ids": created_memory_ids,
        "combat_results": combat_results,
        "extra": _extra(character),
    }
