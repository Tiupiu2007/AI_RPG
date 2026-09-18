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
