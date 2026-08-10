from __future__ import annotations

from typing import Any


ALLOWED_ACTIONS = {
    "character_reaction",
    "create_memory",
    "relationship_change",
    "world_action",
}

WORLD_ACTIONS = {"speak", "approach", "move"}
RELATIONSHIP_FIELDS = ("trust", "affection", "respect", "hostility")


def _ids_from(value: Any) -> set[int]:
    if not isinstance(value, list):
        return set()
    result: set[int] = set()
    for item in value:
        if isinstance(item, int) and not isinstance(item, bool):
            result.add(item)
        elif isinstance(item, dict):
            for key in ("id", "character_id", "character_a_id", "character_b_id"):
                candidate = item.get(key)
                if isinstance(candidate, int) and not isinstance(candidate, bool):
                    result.add(candidate)
    return result


def _present_character_ids(context: dict[str, Any]) -> set[int]:
    character = context.get("character", {})
    current_id = character.get("id") if isinstance(character, dict) else None
    ids = {current_id} if isinstance(current_id, int) and not isinstance(current_id, bool) else set()
    ids |= _ids_from(context.get("characters_present", []))
    scene = context.get("scene", {})
    if isinstance(scene, dict):
        ids |= _ids_from(scene.get("involved_characters", []))
    return ids


def _relationship_ids(context: dict[str, Any]) -> set[int]:
    return _ids_from(context.get("relationships", []))


def _available_location_ids(context: dict[str, Any]) -> set[int]:
    scene = context.get("scene", {})
    if not isinstance(scene, dict):
        return set()
    for key in ("available_location_ids", "reachable_location_ids"):
        ids = _ids_from(scene.get(key, []))
        if ids:
            return ids
    return set()


def _require_int(action: dict[str, Any], field: str) -> int:
    value = action.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} deve essere un intero.")
    return value


def _validate_character_reaction(action: dict[str, Any], character_id: int) -> None:
    if _require_int(action, "character_id") != character_id:
        raise ValueError("character_reaction appartiene a un personaggio diverso.")
    for field in ("emotion", "thought", "intention", "goal"):
        if not isinstance(action.get(field), str):
            raise ValueError(f"character_reaction.{field} non è valido.")


def _validate_memory(action: dict[str, Any], character_id: int) -> None:
    if _require_int(action, "character_id") != character_id:
        raise ValueError("create_memory può salvare solamente memorie del personaggio reagente.")
    content = action.get("content")
    if not isinstance(content, str) or not content.strip() or len(content) > 500:
        raise ValueError("La memoria deve contenere testo da 1 a 500 caratteri.")
    importance = action.get("importance")
    if not isinstance(importance, int) or isinstance(importance, bool) or not 1 <= importance <= 10:
        raise ValueError("importance deve essere un intero compreso tra 1 e 10.")
    if action.get("secret") not in (True, False):
        raise ValueError("secret deve essere booleano.")
    if "memory_type" in action and not isinstance(action["memory_type"], str):
        raise ValueError("memory_type non è valido.")


def _validate_relationship(action: dict[str, Any], character_id: int, context: dict[str, Any]) -> None:
    if _require_int(action, "character_a_id") != character_id:
        raise ValueError("character_a_id deve essere il personaggio reagente.")
    target_id = _require_int(action, "character_b_id")
    if target_id == character_id:
        raise ValueError("Un personaggio non può modificare la relazione con se stesso.")
    if target_id not in _relationship_ids(context):
        raise ValueError(f"La relazione con character_id={target_id} non esiste nel contesto.")

    supplied = False
    for field in RELATIONSHIP_FIELDS:
        if field not in action:
            continue
        supplied = True
        value = action[field]
        if not isinstance(value, int) or isinstance(value, bool) or not -30 <= value <= 30:
            raise ValueError(f"{field} deve essere una variazione intera tra -30 e 30.")
    if not supplied:
        raise ValueError("relationship_change deve contenere almeno una variazione.")


def _validate_world_action(action: dict[str, Any], character_id: int, context: dict[str, Any]) -> None:
    if _require_int(action, "character_id") != character_id:
        raise ValueError("world_action può essere eseguita solamente dal personaggio reagente.")

    action_name = action.get("action")
    if action_name not in WORLD_ACTIONS:
        raise ValueError(f"world_action non consentita: {action_name!r}.")

    present_ids = _present_character_ids(context)
    if action_name in {"speak", "approach"}:
        target_id = _require_int(action, "target_id")
        if target_id not in present_ids:
            raise ValueError(f"target_id={target_id} non è presente nella scena.")

    if action_name == "speak":
        dialogue = action.get("dialogue")
        if not isinstance(dialogue, str) or not dialogue.strip():
            raise ValueError("speak richiede un dialogue non vuoto.")
        if len(dialogue) > 1000:
            raise ValueError("dialogue troppo lungo.")

    if action_name == "move":
        location_id = _require_int(action, "location_id")
        available = _available_location_ids(context)
        if not available:
            raise ValueError("move rifiutata: il contesto non espone destinazioni raggiungibili.")
        if location_id not in available:
            raise ValueError(f"location_id={location_id} non è una destinazione raggiungibile nella scena.")


def validate_actions(actions: list[Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        raise ValueError("actions deve essere una lista.")
    if not isinstance(context, dict):
        raise ValueError("Il contesto del game engine deve essere un dizionario.")

    character = context.get("character")
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene il personaggio reagente.")
    character_id = character.get("id")
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("Il personaggio reagente non ha un ID valido.")

    validated: list[dict[str, Any]] = []
    reaction_count = 0
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("Ogni action deve essere un oggetto JSON.")
        action_type = action.get("type")
        if action_type not in ALLOWED_ACTIONS:
            raise ValueError(f"Tipo di azione non consentito: {action_type!r}.")

        if action_type == "character_reaction":
            reaction_count += 1
            _validate_character_reaction(action, character_id)
        elif action_type == "create_memory":
            _validate_memory(action, character_id)
        elif action_type == "relationship_change":
            _validate_relationship(action, character_id, context)
        elif action_type == "world_action":
            _validate_world_action(action, character_id, context)

        validated.append(dict(action))

    if reaction_count != 1:
        raise ValueError("Deve esistere esattamente una character_reaction valida.")

    return validated
