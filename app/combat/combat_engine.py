from __future__ import annotations

import random
import uuid
from typing import Any, Iterable

from app.combat.combat_models import CombatAction, CombatEvent, CombatState, CombatantState, combatant_from_character


# The combat engine resolves intentions. The AI must never supply the final damage.
DEFAULT_MAX_ROUNDS = 100
MIN_DAMAGE = 1


def create_combat(
    characters: Iterable[dict[str, Any]],
    *,
    combat_id: str | None = None,
    seed: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> CombatState:
    """Create a fresh combat from persistent character dictionaries."""
    combatants: dict[int, CombatantState] = {}
    for character in characters:
        combatant = combatant_from_character(character)
        if combatant.character_id in combatants:
            raise ValueError(f"Personaggio duplicato nello scontro: {combatant.character_id}.")
        combatants[combatant.character_id] = combatant

    if len(combatants) < 2:
        raise ValueError("Uno scontro richiede almeno due personaggi.")

    state = CombatState(
        combat_id=combat_id or uuid.uuid4().hex,
        combatants=combatants,
        metadata=dict(metadata or {}),
    )
    state.metadata.setdefault("seed", seed)
    state.metadata.setdefault("engine", "deterministic-combat-v1")
    state.turn_order = _initiative_order(state, random.Random(seed))
    state.add_event(
        "combat_start",
        "Lo scontro ha inizio.",
        data={"combatants": [c.character_id for c in state.combatants.values()]},
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
    """Resolve one combat intention and mutate the combat state."""
    if state.phase != "active":
        raise ValueError("Lo scontro è già terminato.")

    combat_action = action if isinstance(action, CombatAction) else CombatAction.from_dict(action)
    actor = state.get_combatant(combat_action.character_id)
    if not actor.alive or actor.defeated:
        raise ValueError(f"{actor.name} non può agire perché è sconfitto.")

    rng = rng or random.Random()
    action_name = combat_action.action

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
        return state.add_event(
            "combat_action",
            f"{actor.name} decide di {action_name}.",
            actor_id=actor.character_id,
            target_id=combat_action.target_id,
            action=action_name,
            description=combat_action.description,
        )

    raise ValueError(f"Azione di combattimento non supportata: {action_name!r}.")


def _resolve_attack(
    state: CombatState,
    actor: CombatantState,
    action: CombatAction,
    rng: random.Random,
) -> CombatEvent:
    target = _require_target(state, actor, action.target_id)
    attack = _stat(actor, "strength", 50) * 0.55 + _stat(actor, "agility", 50) * 0.25 + _stat(actor, "luck", 50) * 0.05
    defence = _stat(target, "agility", 50) * 0.45 + _stat(target, "constitution", 50) * 0.20 + _stat(target, "perception", 50) * 0.10
    hit_chance = _clamp(0.55 + (attack - defence) / 180.0, 0.15, 0.90)

    actor.stamina = max(0, actor.stamina - _attack_stamina_cost(actor))
    if rng.random() > hit_chance:
        return state.add_event(
            "miss",
            f"{actor.name} attacca {target.name}, ma il colpo va a vuoto.",
            actor_id=actor.character_id,
            target_id=target.character_id,
            action="attack",
            hit_chance=round(hit_chance, 3),
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

    intelligence = _stat(actor, "intelligence", 50)
    willpower = _stat(actor, "willpower", 50)
    cost = max(5, int(8 + intelligence * 0.08))
    if actor.mana < cost:
        return state.add_event(
            "ability_failed",
            f"{actor.name} tenta di usare {ability_name}, ma non ha abbastanza mana.",
            actor_id=actor.character_id,
            target_id=target.character_id,
            ability=ability_name,
            reason="insufficient_mana",
            mana_cost=cost,
        )

    actor.mana -= cost
    power = 7 + intelligence * 0.11 + willpower * 0.07
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
        mana_cost=cost,
    )


def _resolve_defend(state: CombatState, actor: CombatantState) -> CombatEvent:
    actor.conditions = [condition for condition in actor.conditions if condition != "difesa"]
    actor.conditions.append("difesa")
    return state.add_event(
        "defend",
        f"{actor.name} assume una posizione difensiva.",
        actor_id=actor.character_id,
        action="defend",
    )


def _resolve_recover(state: CombatState, actor: CombatantState) -> CombatEvent:
    stamina_before = actor.stamina
    mana_before = actor.mana
    actor.stamina = min(actor.max_stamina, actor.stamina + max(5, actor.max_stamina // 8))
    actor.mana = min(actor.max_mana, actor.mana + max(1, actor.max_mana // 12))
    return state.add_event(
        "recover",
        f"{actor.name} prende fiato e recupera energie.",
        actor_id=actor.character_id,
        action="recover",
        stamina_recovered=actor.stamina - stamina_before,
        mana_recovered=actor.mana - mana_before,
    )


def _resolve_flee(state: CombatState, actor: CombatantState, rng: random.Random) -> CombatEvent:
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
        )
        state.check_finished()
        return event
    return state.add_event(
        "flee_failed",
        f"{actor.name} tenta di fuggire, ma non trova un'apertura.",
        actor_id=actor.character_id,
        action="flee",
        chance=round(chance, 3),
    )


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
    """Resolve one complete round in the engine's initiative order."""
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
        action = action_map.get(character_id)
        if action is None:
            action = CombatAction(character_id=character_id, action="wait", description="Nessuna intenzione fornita.")
        events.append(resolve_action(state, action, rng=rng))

    if state.phase == "active":
        state.round_number += 1
        state.turn_order = _initiative_order(state, rng)
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
