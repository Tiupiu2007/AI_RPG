from __future__ import annotations

from copy import deepcopy
from typing import Any


STAT_NAMES = (
    "strength", "constitution", "agility", "intelligence",
    "perception", "willpower", "charisma", "luck",
)

DEFAULT_CONDITIONS = {
    "health": 100,
    "max_health": 100,
    "stamina": 100,
    "max_stamina": 100,
    "mana": 100,
    "max_mana": 100,
    "status": "Normale",
}


def _number(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ensure_game_state(extra: dict) -> dict:
    """Normalizza lo stato autorevole senza creare dettagli narrativi."""
    state = extra.get("game_state")
    if not isinstance(state, dict):
        state = {}

    state.setdefault("location", None)
    state.setdefault("flags", {})
    state.setdefault("active_effects", {})
    state.setdefault("turn", 0)

    if not isinstance(state["flags"], dict):
        state["flags"] = {}
    if not isinstance(state["active_effects"], dict):
        state["active_effects"] = {}

    conditions = extra.get("conditions")
    if not isinstance(conditions, dict):
        conditions = {}

    for key, default in DEFAULT_CONDITIONS.items():
        conditions.setdefault(key, default)

    conditions["max_health"] = max(1, _number(conditions["max_health"], 100))
    conditions["max_stamina"] = max(0, _number(conditions["max_stamina"], 100))
    conditions["max_mana"] = max(0, _number(conditions["max_mana"], 100))

    conditions["health"] = max(0, min(
        _number(conditions["health"], conditions["max_health"]),
        conditions["max_health"],
    ))
    conditions["stamina"] = max(0, min(
        _number(conditions["stamina"], conditions["max_stamina"]),
        conditions["max_stamina"],
    ))
    conditions["mana"] = max(0, min(
        _number(conditions["mana"], conditions["max_mana"]),
        conditions["max_mana"],
    ))

    extra["conditions"] = conditions
    extra["game_state"] = state
    return extra


def snapshot(extra: dict) -> dict:
    """Restituisce solo lo stato che il motore considera autorevole."""
    extra = ensure_game_state(extra)
    return {
        "game_state": deepcopy(extra["game_state"]),
        "conditions": deepcopy(extra["conditions"]),
        "inventory": deepcopy(extra.get("inventory", {})),
        "statistics": deepcopy(extra.get("statistics", {})),
        "abilities": deepcopy(extra.get("abilities", [])),
        "skills": deepcopy(extra.get("skills", [])),
        "magic": deepcopy(extra.get("magic", {})),
        "combat": deepcopy(extra.get("combat_state")) if isinstance(extra.get("combat_state"), dict) else None,
    }


def advance_turn(extra: dict) -> dict:
    ensure_game_state(extra)
    extra["game_state"]["turn"] = _number(extra["game_state"].get("turn"), 0) + 1
    return extra


def spend_resource(extra: dict, resource: str, amount: int) -> bool:
    """Consuma una risorsa solo se il motore può farlo."""
    ensure_game_state(extra)

    amount = _number(amount)
    if amount < 0:
        raise ValueError("amount non può essere negativo.")

    conditions = extra["conditions"]
    current = _number(conditions.get(resource), 0)

    if current < amount:
        return False

    conditions[resource] = current - amount
    return True


def restore_resource(extra: dict, resource: str, amount: int) -> None:
    """Ripristina una risorsa rispettando il relativo massimo."""
    ensure_game_state(extra)

    amount = max(0, _number(amount))
    conditions = extra["conditions"]
    maximum = _number(conditions.get(f"max_{resource}"), 0)
    current = _number(conditions.get(resource), 0)

    conditions[resource] = min(maximum, current + amount)


def change_health(extra: dict, amount: int) -> int:
    """Modifica gli HP e restituisce il nuovo valore."""
    ensure_game_state(extra)

    conditions = extra["conditions"]
    maximum = _number(conditions["max_health"], 100)
    current = _number(conditions["health"], maximum)
    conditions["health"] = max(0, min(maximum, current + _number(amount)))
    return conditions["health"]


def set_flag(extra: dict, name: str, value: Any = True) -> None:
    ensure_game_state(extra)
    name = str(name).strip()
    if not name:
        raise ValueError("Il nome del flag non può essere vuoto.")
    extra["game_state"]["flags"][name] = value


def has_flag(extra: dict, name: str) -> bool:
    ensure_game_state(extra)
    return bool(extra["game_state"]["flags"].get(str(name).strip(), False))


def set_location(extra: dict, location_id: str | None) -> None:
    ensure_game_state(extra)
    extra["game_state"]["location"] = location_id


def add_item(extra: dict, item_id: str, quantity: int = 1) -> None:
    ensure_game_state(extra)

    item_id = str(item_id).strip()
    quantity = _number(quantity)

    if not item_id:
        raise ValueError("item_id non può essere vuoto.")
    if quantity <= 0:
        raise ValueError("quantity deve essere maggiore di zero.")

    inventory = extra.setdefault("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
        extra["inventory"] = inventory

    current = _number(inventory.get(item_id), 0)
    inventory[item_id] = current + quantity


def remove_item(extra: dict, item_id: str, quantity: int = 1) -> bool:
    ensure_game_state(extra)

    item_id = str(item_id).strip()
    quantity = _number(quantity)

    if not item_id or quantity <= 0:
        return False

    inventory = extra.setdefault("inventory", {})
    if not isinstance(inventory, dict):
        return False

    current = _number(inventory.get(item_id), 0)
    if current < quantity:
        return False

    remaining = current - quantity
    if remaining:
        inventory[item_id] = remaining
    else:
        inventory.pop(item_id, None)
    return True


SUPPORTED_ACTION_TYPES = {
    "none", "move", "inspect", "interact", "use_item",
    "cast_magic", "attack", "defend", "talk", "flee",
}


def _find_inventory_quantity(extra: dict, item_id: str) -> int:
    inventory = extra.get("inventory", {})
    if not isinstance(inventory, dict):
        return 0
    return _number(inventory.get(item_id), 0)


def validate_action(extra: dict, action: dict) -> dict:
    """Valida un intento AI senza modificare lo stato autorevole."""
    ensure_game_state(extra)

    if not isinstance(action, dict):
        return {"valid": False, "reason": "Azione non valida.", "action": {"type": "none"}}

    action_type = str(action.get("type", "none")).strip()
    if action_type not in SUPPORTED_ACTION_TYPES:
        return {"valid": False, "reason": f"Azione non supportata: {action_type}.", "action": {"type": "none"}}

    target_id = action.get("target_id")
    target_text = action.get("target_text")
    parameters = action.get("parameters")
    if not isinstance(parameters, dict):
        parameters = {}

    normalized = {
        "type": action_type,
        "target_id": target_id,
        "target_text": target_text if isinstance(target_text, str) else None,
        "parameters": parameters,
    }

    if action_type == "move":
        available = extra.get("available_location_ids", [])
        if not isinstance(available, list):
            available = []
        if target_id is None and not target_text:
            return {"valid": False, "reason": "Movimento senza destinazione.", "action": normalized}
        if target_id is not None and available and target_id not in available:
            return {"valid": False, "reason": "La destinazione non è disponibile.", "action": normalized}

    if action_type == "use_item":
        item_id = target_id if target_id is not None else target_text
        quantity = max(1, _number(parameters.get("quantity"), 1))
        if not item_id:
            return {"valid": False, "reason": "Uso oggetto senza identificare l'oggetto.", "action": normalized}
        if _find_inventory_quantity(extra, str(item_id)) < quantity:
            return {"valid": False, "reason": "L'oggetto non è presente nell'inventario in quantità sufficiente.", "action": normalized}

    if action_type in {"attack", "defend", "cast_magic", "flee"}:
        if action_type == "attack" and (
            not isinstance(target_id, int) or isinstance(target_id, bool)
        ):
            return {"valid": False, "reason": "L'attacco richiede un target_id numerico.", "action": normalized}
        if action_type == "cast_magic" and isinstance(extra.get("combat_state"), dict):
            if not isinstance(target_id, int) or isinstance(target_id, bool):
                return {"valid": False, "reason": "La magia in combattimento richiede un target_id numerico.", "action": normalized}
        if action_type in {"defend", "flee"} and not isinstance(extra.get("combat_state"), dict):
            return {"valid": False, "reason": "Questa azione richiede un combattimento attivo.", "action": normalized}

    if action_type == "cast_magic":
        ability_id = parameters.get("ability_id")
        if ability_id is None and target_id is not None and not isinstance(extra.get("combat_state"), dict):
            ability_id = target_id
        abilities = extra.get("abilities", [])
        magic = extra.get("magic", {})
        known = set()
        if isinstance(abilities, list):
            for ability in abilities:
                if isinstance(ability, str):
                    known.add(ability)
                elif isinstance(ability, dict):
                    for key in ("id", "ability_id", "name"):
                        if ability.get(key) is not None:
                            known.add(str(ability[key]))
        if isinstance(magic, dict):
            spells = magic.get("spells", magic.get("abilities", []))
            if isinstance(spells, list):
                for spell in spells:
                    if isinstance(spell, str):
                        known.add(spell)
                    elif isinstance(spell, dict):
                        for key in ("id", "ability_id", "name"):
                            if spell.get(key) is not None:
                                known.add(str(spell[key]))
        if ability_id is None or str(ability_id) not in known:
            return {"valid": False, "reason": "Magia o abilità non presente nello stato autorevole.", "action": normalized}

    return {"valid": True, "reason": None, "action": normalized}


def execute_action(extra: dict, action: dict, actor_id: int | None = None) -> dict:
    """Esegue solo modifiche autorizzate dal Game Engine."""
    validation = validate_action(extra, action)
    if not validation["valid"]:
        return {
            "executed": False,
            "valid": False,
            "reason": validation["reason"],
            "action": validation["action"],
            "changes": {},
        }

    action = validation["action"]
    action_type = action["type"]
    parameters = action["parameters"]
    changes = {}

    if action_type == "move":
        old_location = extra["game_state"].get("location")
        try:
            from app.world.runtime import move_actor
            movement = move_actor(
                extra,
                actor_id if isinstance(actor_id, int) else 0,
                str(action["target_id"]) if action["target_id"] is not None else None,
                action["target_text"],
            )
        except (ValueError, TypeError) as error:
            return {
                "executed": False,
                "valid": False,
                "reason": str(error),
                "action": action,
                "changes": {},
            }
        new_location = movement["to"]
        set_location(extra, new_location)
        changes["location"] = {"from": old_location, **movement}

    elif action_type == "use_item":
        item_id = str(action["target_id"] if action["target_id"] is not None else action["target_text"])
        quantity = max(1, _number(parameters.get("quantity"), 1))
        if not remove_item(extra, item_id, quantity):
            return {
                "executed": False,
                "valid": False,
                "reason": "L'oggetto non è disponibile in quantità sufficiente.",
                "action": action,
                "changes": {},
            }

        item_definitions = extra.get("item_definitions", {})
        item = item_definitions.get(item_id, {}) if isinstance(item_definitions, dict) else {}
        effects = item.get("effects", {}) if isinstance(item, dict) else {}
        if not isinstance(effects, dict):
            effects = {}
        effect_changes = {}
        for resource in ("health", "stamina", "mana"):
            if resource in effects:
                amount = max(0, _number(effects.get(resource), 0)) * quantity
                if amount:
                    before = _number(extra["conditions"].get(resource), 0)
                    if resource == "health":
                        after = change_health(extra, amount)
                    else:
                        restore_resource(extra, resource, amount)
                        after = _number(extra["conditions"].get(resource), 0)
                    effect_changes[resource] = {"from": before, "to": after}
        changes["inventory"] = {"removed": {item_id: quantity}}
        changes["effects"] = effect_changes

    elif action_type in {"attack", "defend", "cast_magic", "flee"}:
        if not isinstance(actor_id, int) or isinstance(actor_id, bool):
            return {
                "executed": False,
                "valid": False,
                "reason": "Il Game Engine non conosce il combattente che esegue l'azione.",
                "action": action,
                "changes": {},
            }

        in_combat = isinstance(extra.get("combat_state"), dict)

        if action_type == "flee" and not in_combat:
            return {
                "executed": False,
                "valid": False,
                "reason": "Non sei in combattimento.",
                "action": action,
                "changes": {},
            }

        if action_type == "cast_magic" and not in_combat:
            ability_id = parameters.get("ability_id", action.get("target_id"))
            definitions = []
            abilities = extra.get("abilities", [])
            if isinstance(abilities, list):
                definitions.extend(x for x in abilities if isinstance(x, dict))
            magic = extra.get("magic", {})
            if isinstance(magic, dict):
                spells = magic.get("spells", magic.get("abilities", []))
                if isinstance(spells, list):
                    definitions.extend(x for x in spells if isinstance(x, dict))

            ability = next(
                (
                    item for item in definitions
                    if str(item.get("id", item.get("ability_id", item.get("name", "")))) == str(ability_id)
                ),
                None,
            )
            if ability is None:
                return {
                    "executed": False,
                    "valid": False,
                    "reason": "Magia o abilità non trovata nello stato autorevole.",
                    "action": action,
                    "changes": {},
                }

            mana_cost = max(0, _number(ability.get("mana_cost"), 0))
            if not spend_resource(extra, "mana", mana_cost):
                return {
                    "executed": False,
                    "valid": False,
                    "reason": "Mana insufficiente.",
                    "action": action,
                    "changes": {},
                }

            changes["magic"] = {
                "ability_id": ability_id,
                "mana_cost": mana_cost,
                "remaining_mana": extra["conditions"]["mana"],
            }
        else:
            try:
                from app.game_engine.combat_runtime import resolve_narrative_combat
                combat_result = resolve_narrative_combat(extra, actor_id, action)
            except (ValueError, TypeError) as error:
                return {
                    "executed": False,
                    "valid": False,
                    "reason": str(error),
                    "action": action,
                    "changes": {},
                }
            changes["combat"] = combat_result

    # inspect, interact e talk sono azioni narrative: non modificano numeri
    # da sole, ma il risultato viene passato al narratore.
    return {
        "executed": True,
        "valid": True,
        "reason": None,
        "action": action,
        "changes": changes,
    }
