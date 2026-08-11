from __future__ import annotations

import random
import uuid
from typing import Any, Iterable

from app.combat.combat_models import (
    CombatAction,
    CombatEvent,
    CombatState,
    CombatantState,
    DEFAULT_ACTION_POINTS,
    combatant_from_character,
)


# The combat engine resolves intentions. The client/AI must never supply
# the final damage, resource changes or outcome.
DEFAULT_MAX_ROUNDS = 100
MIN_DAMAGE = 1
PHYSICAL_ATTACK_AP = 2
ABILITY_AP = 1
DEFEND_AP = 1
RECOVER_AP = 1


def create_combat(
    characters: Iterable[dict[str, Any]],
    *,
    combat_id: str | None = None,
    seed: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> CombatState:
    """Create a fresh 1v1 combat from persistent character dictionaries."""
    combatants: dict[int, CombatantState] = {}
    for character in characters:
        combatant = combatant_from_character(character)
        if combatant.character_id in combatants:
            raise ValueError(f"Personaggio duplicato nello scontro: {combatant.character_id}.")
        combatants[combatant.character_id] = combatant

    if len(combatants) != 2:
        raise ValueError("Uno scontro PvP richiede esattamente due personaggi.")

    state = CombatState(
        combat_id=combat_id or uuid.uuid4().hex,
        combatants=combatants,
        metadata=dict(metadata or {}),
    )
    state.metadata.setdefault("seed", seed)
    state.metadata.setdefault("engine", "turn-based-pvp-v1")
    state.metadata.setdefault("rules", {
        "max_action_points": DEFAULT_ACTION_POINTS,
        "physical_attack_ap": PHYSICAL_ATTACK_AP,
        "ability_ap": ABILITY_AP,
        "ability_uses_mana": True,
        "physical_uses_stamina": True,
    })

    # L'iniziativa determina solo chi inizia. L'ordine non viene ricalcolato
    # dopo ogni turno: in un PvP 1v1 il controllo passa semplicemente all'altro.
    state.turn_order = _initiative_order(state, random.Random(seed))
    state.current_turn_character_id = state.turn_order[0]
    state.get_combatant(state.current_turn_character_id).reset_turn_resources()

    state.add_event(
        "combat_start",
        "Lo scontro ha inizio.",
        data_combatants=[c.character_id for c in state.combatants.values()],
        first_turn_character_id=state.current_turn_character_id,
    )
    return state


def _initiative_order(state: CombatState, rng: random.Random) -> list[int]:
    values: list[tuple[int, float, float]] = []
    for combatant in state.combatants.values():
        agility = _stat(combatant, "agility", 50)
        perception = _stat(combatant, "perception", 50)
        roll = rng.uniform(0, 20)
        values.append((combatant.character_id, agility + perception * 0.35 + roll, roll))
    values.sort(key=lambda item: (item[1], item[2]), reverse=True)
    return [item[0] for item in values]


def resolve_action(
    state: CombatState,
    action: CombatAction | dict[str, Any],
    *,
    rng: random.Random | None = None,
) -> CombatEvent:
    """Resolve one action belonging to the currently active player."""
    if state.phase != "active":
        raise ValueError("Lo scontro è già terminato.")

    combat_action = action if isinstance(action, CombatAction) else CombatAction.from_dict(action)
    actor = state.get_combatant(combat_action.character_id)
    if not actor.alive or actor.defeated:
        raise ValueError(f"{actor.name} non può agire perché è sconfitto.")

    if state.current_turn_character_id != actor.character_id:
        raise ValueError("Non è il turno di questo combattente.")

    rng = rng or random.Random()
    action_name = combat_action.action

    if action_name in {"end_turn", "end", "pass_turn"}:
        return _end_turn(state, actor)
    if action_name in {"attack", "physical_attack", "strike", "hit"}:
        return _resolve_attack(state, actor, combat_action, rng)
    if action_name in {"ability", "spell", "magic"}:
        return _resolve_ability(state, actor, combat_action, rng)
    if action_name in {"defend", "guard", "defence"}:
        return _resolve_defend(state, actor)
    if action_name in {"recover", "rest"}:
        return _resolve_recover(state, actor)
    if action_name in {"flee", "escape"}:
        return _resolve_flee(state, actor, rng)
    if action_name in {"wait", "observe", "taunt", "speak"}:
        return _resolve_non_combat_action(state, actor, combat_action)

    raise ValueError(f"Azione di combattimento non supportata: {action_name!r}.")


def _resolve_attack(
    state: CombatState,
    actor: CombatantState,
    action: CombatAction,
    rng: random.Random,
) -> CombatEvent:
    target = _require_target(state, actor, action.target_id)
    if not _spend_action_points(state, actor, PHYSICAL_ATTACK_AP, "attack"):
        return state.events[-1]

    stamina_cost = _attack_stamina_cost(actor)
    if actor.stamina < stamina_cost:
        actor.action_points += PHYSICAL_ATTACK_AP
        return state.add_event(
            "action_failed",
            f"{actor.name} tenta un attacco, ma non ha abbastanza stamina.",
            actor_id=actor.character_id,
            target_id=target.character_id,
            action="attack",
            reason="insufficient_stamina",
            stamina_cost=stamina_cost,
            action_points=actor.action_points,
        )

    actor.stamina -= stamina_cost
    attack = (
        _stat(actor, "strength", 50) * 0.55
        + _stat(actor, "agility", 50) * 0.25
        + _stat(actor, "luck", 50) * 0.05
    )
    defence = (
        _stat(target, "agility", 50) * 0.45
        + _stat(target, "constitution", 50) * 0.20
        + _stat(target, "perception", 50) * 0.10
    )
    hit_chance = _clamp(0.55 + (attack - defence) / 180.0, 0.15, 0.90)

    if rng.random() > hit_chance:
        return state.add_event(
            "miss",
            f"{actor.name} attacca {target.name}, ma il colpo va a vuoto.",
            actor_id=actor.character_id,
            target_id=target.character_id,
            action="attack",
            action_points_spent=PHYSICAL_ATTACK_AP,
            stamina_cost=stamina_cost,
            hit_chance=round(hit_chance, 3),
            remaining_action_points=actor.action_points,
        )

    base = 5 + _stat(actor, "strength", 50) * 0.12
    defence_reduction = _stat(target, "constitution", 50) * 0.035
    damage = max(MIN_DAMAGE, int(base - defence_reduction + rng.randint(-3, 6)))
    critical_chance = _clamp(0.03 + _stat(actor, "luck", 50) / 2500, 0.03, 0.12)
    critical = rng.random() < critical_chance
    if critical:
        damage = max(MIN_DAMAGE, int(damage * 1.5))

    return _apply_damage(
        state,
        actor,
        target,
        damage,
        "critical_hit" if critical else "hit",
        f"{actor.name} colpisce {target.name}{' con un colpo critico' if critical else ''} e infligge {damage} danni.",
        action="attack",
        critical=critical,
        hit_chance=round(hit_chance, 3),
        action_points_spent=PHYSICAL_ATTACK_AP,
        stamina_cost=stamina_cost,
        remaining_action_points=actor.action_points,
    )


def _resolve_ability(
    state: CombatState,
    actor: CombatantState,
    action: CombatAction,
    rng: random.Random,
) -> CombatEvent:
    target = _require_target(state, actor, action.target_id)
    ability = _find_ability(actor, action.ability)
    ability_name = action.ability or (ability.get("name") if ability else None) or "abilità"

    if not _spend_action_points(state, actor, ABILITY_AP, "ability"):
        return state.events[-1]

    intelligence = _stat(actor, "intelligence", 50)
    willpower = _stat(actor, "willpower", 50)

    # Un'abilità può definire il proprio costo mana. In assenza di un valore
    # esplicito usiamo un costo base inferiore al peso in PA dell'attacco fisico.
    cost_value = ability.get("mana_cost") if isinstance(ability, dict) else None
    try:
        mana_cost = max(1, int(cost_value)) if cost_value is not None else max(5, int(8 + intelligence * 0.08))
    except (TypeError, ValueError):
        mana_cost = max(5, int(8 + intelligence * 0.08))

    if actor.mana < mana_cost:
        actor.action_points += ABILITY_AP
        return state.add_event(
            "ability_failed",
            f"{actor.name} tenta di usare {ability_name}, ma non ha abbastanza mana.",
            actor_id=actor.character_id,
            target_id=target.character_id,
            ability=ability_name,
            reason="insufficient_mana",
            mana_cost=mana_cost,
            action_points=actor.action_points,
        )

    actor.mana -= mana_cost

    # Le magie/abilità hanno normalmente un output superiore all'attacco
    # fisico, pagando però mana invece di una grande spesa in PA.
    power_multiplier = 1.25
    if isinstance(ability, dict):
        try:
            power_multiplier = max(1.0, float(ability.get("power_multiplier", 1.25)))
        except (TypeError, ValueError):
            power_multiplier = 1.25

    power = (7 + intelligence * 0.11 + willpower * 0.07) * power_multiplier
    resistance = _stat(target, "willpower", 50) * 0.05 + _stat(target, "constitution", 50) * 0.03
    damage = max(MIN_DAMAGE, int(power - resistance + rng.randint(-3, 7)))
    return _apply_damage(
        state,
        actor,
        target,
        damage,
        "ability_hit",
        f"{actor.name} usa {ability_name} contro {target.name} e infligge {damage} danni.",
        action="ability",
        ability=ability_name,
        mana_cost=mana_cost,
        action_points_spent=ABILITY_AP,
        remaining_action_points=actor.action_points,
    )


def _resolve_defend(state: CombatState, actor: CombatantState) -> CombatEvent:
    if not _spend_action_points(state, actor, DEFEND_AP, "defend"):
        return state.events[-1]
    actor.conditions = [condition for condition in actor.conditions if condition != "difesa"]
    actor.conditions.append("difesa")
    return state.add_event(
        "defend",
        f"{actor.name} assume una posizione difensiva.",
        actor_id=actor.character_id,
        action="defend",
        action_points_spent=DEFEND_AP,
        remaining_action_points=actor.action_points,
    )


def _resolve_recover(state: CombatState, actor: CombatantState) -> CombatEvent:
    if not _spend_action_points(state, actor, RECOVER_AP, "recover"):
        return state.events[-1]
    stamina_before = actor.stamina
    mana_before = actor.mana
    actor.stamina = min(actor.max_stamina, actor.stamina + max(5, actor.max_stamina // 8))
    actor.mana = min(actor.max_mana, actor.mana + max(1, actor.max_mana // 12))
    return state.add_event(
        "recover",
        f"{actor.name} prende fiato e recupera energie.",
        actor_id=actor.character_id,
        action="recover",
        action_points_spent=RECOVER_AP,
        stamina_recovered=actor.stamina - stamina_before,
        mana_recovered=actor.mana - mana_before,
        remaining_action_points=actor.action_points,
    )


def _resolve_flee(state: CombatState, actor: CombatantState, rng: random.Random) -> CombatEvent:
    if not _spend_action_points(state, actor, 1, "flee"):
        return state.events[-1]
    chance = _clamp(0.25 + (_stat(actor, "agility", 50) - 50) / 150, 0.10, 0.75)
    success = rng.random() <= chance
    if success:
        actor.defeated = True
        actor.alive = False
        actor.status = "Fuggito"
        event = state.add_event(
            "flee_success",
            f"{actor.name} riesce a fuggire dallo scontro.",
            actor_id=actor.character_id,
            action="flee",
            chance=round(chance, 3),
            action_points_spent=1,
        )
        state.check_finished()
        return event
    return state.add_event(
        "flee_failed",
        f"{actor.name} tenta di fuggire, ma non trova un'apertura.",
        actor_id=actor.character_id,
        action="flee",
        chance=round(chance, 3),
        action_points_spent=1,
        remaining_action_points=actor.action_points,
    )


def _resolve_non_combat_action(
    state: CombatState,
    actor: CombatantState,
    action: CombatAction,
) -> CombatEvent:
    if not _spend_action_points(state, actor, 1, action.action):
        return state.events[-1]
    return state.add_event(
        "combat_action",
        f"{actor.name} decide di {action.action}.",
        actor_id=actor.character_id,
        target_id=action.target_id,
        action=action.action,
        action_points_spent=1,
        player_description=action.description,
        intent=action.intent,
        remaining_action_points=actor.action_points,
    )


def _end_turn(state: CombatState, actor: CombatantState) -> CombatEvent:
    event = state.add_event(
        "turn_end",
        f"{actor.name} termina il proprio turno.",
        actor_id=actor.character_id,
        remaining_action_points=actor.action_points,
    )
    if state.phase != "active":
        return event

    actor.action_points = 0
    if len(state.turn_order) != 2:
        raise ValueError("Il combattimento PvP richiede esattamente due combattenti.")

    current_index = state.turn_order.index(actor.character_id)
    next_character_id = state.turn_order[(current_index + 1) % 2]
    state.current_turn_character_id = next_character_id
    next_actor = state.get_combatant(next_character_id)

    if current_index == 1:
        state.round_number += 1

    next_actor.reset_turn_resources()
    state.add_event(
        "turn_start",
        f"Inizia il turno di {next_actor.name}.",
        actor_id=next_actor.character_id,
        action_points=next_actor.action_points,
        round_number=state.round_number,
    )
    return event


def _spend_action_points(
    state: CombatState,
    actor: CombatantState,
    cost: int,
    action_name: str,
) -> bool:
    if actor.action_points < cost:
        state.add_event(
            "action_failed",
            f"{actor.name} non ha abbastanza PA per {action_name}.",
            actor_id=actor.character_id,
            action=action_name,
            reason="insufficient_action_points",
            action_points_required=cost,
            action_points_available=actor.action_points,
        )
        return False
    actor.action_points -= cost
    return True


def _apply_damage(
    state: CombatState,
    actor: CombatantState,
    target: CombatantState,
    damage: int,
    event_type: str,
    description: str,
    **data: Any,
) -> CombatEvent:
    had_defence = "difesa" in target.conditions
    if had_defence:
        damage = max(MIN_DAMAGE, damage // 2)
        target.conditions = [condition for condition in target.conditions if condition != "difesa"]
        data["defence_reduced_damage"] = True

    target.health = max(0, target.health - damage)
    target.alive = target.health > 0 and not target.defeated
    data["damage"] = damage
    data["remaining_health"] = target.health

    event = state.add_event(
        event_type,
        description if not had_defence else description + " La difesa riduce l'impatto.",
        actor_id=actor.character_id,
        target_id=target.character_id,
        **data,
    )

    if not target.alive:
        target.defeated = True
        target.status = "Sconfitto"
        state.add_event(
            "defeat",
            f"{target.name} è sconfitto.",
            actor_id=actor.character_id,
            target_id=target.character_id,
        )
        state.check_finished()
    return event


def resolve_round(
    state: CombatState,
    actions: Iterable[CombatAction | dict[str, Any]],
    *,
    seed: int | None = None,
) -> list[CombatEvent]:
    """Compatibility helper for offline simulations.

    The online PvP API should normally call resolve_action() once per client
    action and use end_turn to pass control to the opponent.
    """
    if state.phase != "active":
        raise ValueError("Lo scontro è già terminato.")

    action_map: dict[int, CombatAction] = {}
    for raw_action in actions:
        action = raw_action if isinstance(raw_action, CombatAction) else CombatAction.from_dict(raw_action)
        if action.character_id in action_map:
            raise ValueError(f"Sono state fornite due azioni per il personaggio {action.character_id}.")
        action_map[action.character_id] = action

    rng = random.Random(seed)
    events: list[CombatEvent] = []
    for character_id in state.turn_order:
        if state.phase != "active":
            break
        actor = state.get_combatant(character_id)
        if not actor.alive or actor.defeated:
            continue
        state.current_turn_character_id = character_id
        actor.reset_turn_resources()
        action = action_map.get(character_id)
        if action is None:
            action = CombatAction(character_id=character_id, action="end_turn")
        events.append(resolve_action(state, action, rng=rng))
        if state.phase == "active" and state.current_turn_character_id == character_id:
            events.append(_end_turn(state, actor))

    return events


def simulate_combat(
    state: CombatState,
    rounds: Iterable[Iterable[CombatAction | dict[str, Any]]],
    *,
    seed: int | None = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
) -> CombatState:
    """Run supplied rounds until a winner exists or max_rounds is reached."""
    if max_rounds <= 0:
        raise ValueError("max_rounds deve essere maggiore di zero.")

    for index, actions in enumerate(rounds):
        if index >= max_rounds or state.phase != "active":
            break
        resolve_round(state, actions, seed=None if seed is None else seed + index)

    if state.phase == "active" and state.round_number > max_rounds:
        state.phase = "draw"
        state.current_turn_character_id = None
        state.add_event("combat_end", "Lo scontro termina senza un vincitore entro il limite di round.")
    elif state.phase == "finished":
        state.add_event(
            "combat_end",
            "Lo scontro è terminato.",
            actor_id=state.winner_id,
            winner_id=state.winner_id,
            loser_ids=list(state.loser_ids),
        )
    return state


def _require_target(state: CombatState, actor: CombatantState, target_id: int | None) -> CombatantState:
    if target_id is None:
        raise ValueError(f"{actor.name} deve specificare un bersaglio.")
    target = state.combatants.get(target_id)
    if target is None:
        raise ValueError(f"Bersaglio {target_id} non presente nello scontro.")
    if target.character_id == actor.character_id:
        raise ValueError("Un combattente non può attaccare se stesso.")
    if not target.alive or target.defeated:
        raise ValueError(f"{target.name} è già sconfitto.")
    return target


def _find_ability(actor: CombatantState, requested: str | None) -> dict[str, Any] | None:
    if not requested:
        return actor.abilities[0] if actor.abilities else None
    requested_lower = requested.strip().lower()
    for ability in actor.abilities:
        if str(ability.get("name", "")).strip().lower() == requested_lower:
            return ability
    return None


def _stat(actor: CombatantState, name: str, default: int) -> float:
    value = actor.statistics.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _attack_stamina_cost(actor: CombatantState) -> int:
    agility = _stat(actor, "agility", 50)
    return max(3, int(10 - agility / 25))


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
