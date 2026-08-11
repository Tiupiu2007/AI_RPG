from __future__ import annotations

from typing import Any


ALLOWED_ACTIONS = {
    "character_reaction",
    "create_memory",
    "relationship_change",
    "world_action",
    "combat_action",
}
WORLD_ACTIONS = {"speak", "approach", "move"}
COMBAT_ACTIONS = {"attack", "defend", "use_ability", "use_item", "flee", "wait"}
RELATIONSHIP_FIELDS = ("trust", "affection", "respect", "hostility")
MAX_ACTIONS_PER_TURN = 5
MAX_MEMORY_ACTIONS_PER_TURN = 1
MAX_COMBAT_ACTIONS_PER_TURN = 1
MAX_ACTION_TEXT_LENGTH = 500

# L'IA non può mai assegnare direttamente questi valori. Il combat engine
# calcolerà danni, costi, condizioni, morte e vincitore.
COMBAT_FORBIDDEN_FIELDS = {
    "damage", "healing", "health", "hp", "max_health", "stamina",
    "max_stamina", "mana", "max_mana", "status", "condition",
    "conditions", "dead", "alive", "winner", "loser",
}


def _ids_from(value: Any) -> set[int]:
    if not isinstance(value, list):
        return set()
    result: set[int] = set()
    for item in value:
        if isinstance(item, int) and not isinstance(item, bool):
            result.add(item)
        elif isinstance(item, dict):
            for key in (
                "id", "character_id", "character_a_id", "character_b_id",
                "actor_id", "target_id",
            ):
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


def _combatant_ids(context: dict[str, Any]) -> set[int]:
    """ID autorizzati ad agire o essere bersagli nel combattimento."""
    ids: set[int] = set()
    combat = context.get("combat")
    if isinstance(combat, dict):
        for key in ("combatants", "participants", "fighters"):
            ids |= _ids_from(combat.get(key, []))
    for key in ("combatants", "participants", "fighters"):
        ids |= _ids_from(context.get(key, []))
    ids |= _present_character_ids(context)
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


def _optional_text(action: dict[str, Any], field: str, maximum: int = MAX_ACTION_TEXT_LENGTH) -> None:
    if field not in action:
        return
    value = action[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} deve essere una stringa non vuota.")
    if len(value.strip()) > maximum:
        raise ValueError(f"{field} è troppo lungo.")


def _validate_character_reaction(action: dict[str, Any], character_id: int) -> None:
    if _require_int(action, "character_id") != character_id:
        raise ValueError("character_reaction appartiene a un personaggio diverso.")
    for field in ("emotion", "thought", "intention", "goal"):
        value = action.get(field)
        if not isinstance(value, str):
            raise ValueError(f"character_reaction.{field} non è valido.")
        if len(value) > 500:
            raise ValueError(f"character_reaction.{field} è troppo lungo.")


def _validate_memory(action: dict[str, Any], character_id: int) -> None:
    if _require_int(action, "character_id") != character_id:
        raise ValueError("create_memory può salvare solamente memorie del personaggio reagente.")
    content = action.get("content")
    if not isinstance(content, str) or not content.strip() or len(content.strip()) > 500:
        raise ValueError("La memoria deve contenere testo da 1 a 500 caratteri.")
    importance = action.get("importance")
    if not isinstance(importance, int) or isinstance(importance, bool) or not 1 <= importance <= 10:
        raise ValueError("importance deve essere un intero compreso tra 1 e 10.")
    if action.get("secret") not in (True, False):
        raise ValueError("secret deve essere booleano.")
    if "memory_type" in action:
        if not isinstance(action["memory_type"], str) or not action["memory_type"].strip():
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
        if len(dialogue.strip()) > 1000:
            raise ValueError("dialogue troppo lungo.")

    if action_name == "move":
        location_id = _require_int(action, "location_id")
        available = _available_location_ids(context)
        if not available:
            raise ValueError("move rifiutata: il contesto non espone destinazioni raggiungibili.")
        if location_id not in available:
            raise ValueError(f"location_id={location_id} non è una destinazione raggiungibile nella scena.")


def _validate_combat_action(action: dict[str, Any], character_id: int, context: dict[str, Any]) -> None:
    """Valida l'intenzione di combattimento, non il suo risultato."""
    if _require_int(action, "character_id") != character_id:
        raise ValueError("combat_action appartiene a un combattente diverso.")

    combatants = _combatant_ids(context)
    if character_id not in combatants:
        raise ValueError("Il personaggio reagente non è presente nel combattimento.")

    action_name = action.get("action")
    if action_name not in COMBAT_ACTIONS:
        raise ValueError(f"Azione di combattimento non consentita: {action_name!r}.")

    for field in COMBAT_FORBIDDEN_FIELDS:
        if field in action:
            raise ValueError(
                f"combat_action non può modificare direttamente '{field}'. "
                "Il risultato deve essere calcolato dal combat engine."
            )

    if action_name in {"attack", "use_ability"}:
        target_id = _require_int(action, "target_id")
        if target_id == character_id:
            raise ValueError("Un combattente non può bersagliare se stesso.")
        if target_id not in combatants:
            raise ValueError(f"target_id={target_id} non appartiene ai combattenti autorizzati.")

    if action_name == "use_item":
        _optional_text(action, "item", 200)
        if not isinstance(action.get("item"), str) or not action["item"].strip():
            raise ValueError("use_item richiede il nome dell'item.")

    if action_name == "use_ability":
        _optional_text(action, "ability", 200)
        if not isinstance(action.get("ability"), str) or not action["ability"].strip():
            raise ValueError("use_ability richiede il nome dell'abilità.")

    if action_name == "flee" and "target_id" in action:
        raise ValueError("flee non richiede target_id.")

    _optional_text(action, "description", 500)
    _optional_text(action, "reason", 500)


def validate_actions(actions: list[Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        raise ValueError("actions deve essere una lista.")
    if not isinstance(context, dict):
        raise ValueError("Il contesto del game engine deve essere un dizionario.")
    if not actions:
        raise ValueError("Il turno deve contenere almeno una character_reaction.")
    if len(actions) > MAX_ACTIONS_PER_TURN:
        raise ValueError(f"Sono consentite al massimo {MAX_ACTIONS_PER_TURN} azioni per turno.")

    character = context.get("character", {})
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene il personaggio reagente.")
    character_id = character.get("id")
    if not isinstance(character_id, int) or isinstance(character_id, bool):
        raise ValueError("Il personaggio reagente non ha un ID valido.")

    validated: list[dict[str, Any]] = []
    reaction_count = 0
    memory_count = 0
    combat_count = 0

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
            memory_count += 1
            if memory_count > MAX_MEMORY_ACTIONS_PER_TURN:
                raise ValueError("È consentita al massimo una create_memory per turno.")
            _validate_memory(action, character_id)
        elif action_type == "relationship_change":
            _validate_relationship(action, character_id, context)
        elif action_type == "world_action":
            _validate_world_action(action, character_id, context)
        elif action_type == "combat_action":
            combat_count += 1
            if combat_count > MAX_COMBAT_ACTIONS_PER_TURN:
                raise ValueError("È consentita al massimo una combat_action per turno.")
            _validate_combat_action(action, character_id, context)

        validated.append(dict(action))

    if reaction_count != 1:
        raise ValueError("Deve esistere esattamente una character_reaction valida.")

    # La reazione è il nucleo del turno e viene sempre eseguita per prima.
    # combat_action rappresenta l'intenzione che il combat engine risolverà.
    reaction = next(action for action in validated if action["type"] == "character_reaction")
    others = [action for action in validated if action["type"] != "character_reaction"]
    return [reaction, *others]
