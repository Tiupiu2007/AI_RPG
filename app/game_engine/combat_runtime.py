from __future__ import annotations

from typing import Any

from app.combat.combat_engine import create_combat, resolve_action
from app.combat.combat_models import CombatAction, CombatEvent, CombatState, CombatantState
from app.database.characters_db import get_character


def _state_from_dict(data: dict[str, Any]) -> CombatState:
    if not isinstance(data, dict):
        raise ValueError("combat_state non valido.")

    combatants: dict[int, CombatantState] = {}
    for raw_id, raw in (data.get("combatants") or {}).items():
        if not isinstance(raw, dict):
            continue
        try:
            character_id = int(raw.get("character_id", raw_id))
        except (TypeError, ValueError):
            continue
        combatants[character_id] = CombatantState(
            character_id=character_id,
            name=str(raw.get("name") or "Personaggio"),
            health=int(raw.get("health", 0)),
            max_health=max(1, int(raw.get("max_health", 1))),
            stamina=max(0, int(raw.get("stamina", 0))),
            max_stamina=max(0, int(raw.get("max_stamina", 0))),
            mana=max(0, int(raw.get("mana", 0))),
            max_mana=max(0, int(raw.get("max_mana", 0))),
            action_points=max(0, int(raw.get("action_points", 0))),
            max_action_points=max(1, int(raw.get("max_action_points", 3))),
            statistics=dict(raw.get("statistics") or {}),
            abilities=[x for x in (raw.get("abilities") or []) if isinstance(x, dict)],
            skills=[x for x in (raw.get("skills") or []) if isinstance(x, dict)],
            status=str(raw.get("status") or "Normale"),
            alive=bool(raw.get("alive", True)),
            defeated=bool(raw.get("defeated", False)),
            conditions=[str(x) for x in (raw.get("conditions") or [])],
        )

    events = []
    for raw in data.get("events") or []:
        if not isinstance(raw, dict):
            continue
        events.append(
            CombatEvent(
                round_number=int(raw.get("round_number", 1)),
                actor_id=raw.get("actor_id"),
                target_id=raw.get("target_id"),
                event_type=str(raw.get("event_type") or "combat_event"),
                description=str(raw.get("description") or ""),
                data=dict(raw.get("data") or {}),
            )
        )

    state = CombatState(
        combat_id=str(data.get("combat_id") or ""),
        round_number=int(data.get("round_number", 1)),
        phase=str(data.get("phase") or "active"),
        combatants=combatants,
        turn_order=[int(x) for x in (data.get("turn_order") or [])],
        current_turn_character_id=data.get("current_turn_character_id"),
        events=events,
        winner_id=data.get("winner_id"),
        loser_ids=[int(x) for x in (data.get("loser_ids") or [])],
        metadata=dict(data.get("metadata") or {}),
    )
    return state


def load_combat(extra: dict[str, Any]) -> CombatState | None:
    raw = extra.get("combat_state")
    if not isinstance(raw, dict):
        return None
    return _state_from_dict(raw)


def save_combat(extra: dict[str, Any], state: CombatState) -> None:
    extra["combat_state"] = state.to_dict()


def start_combat(extra: dict[str, Any], actor_id: int, target_id: int) -> CombatState:
    if actor_id == target_id:
        raise ValueError("Non puoi iniziare un combattimento contro te stesso.")

    actor = get_character(actor_id)
    target = get_character(target_id)
    if actor is None or target is None:
        raise ValueError("Combattente non trovato.")

    state = create_combat([actor, target], metadata={"source": "narrative"})
    # Un combattimento nato direttamente da un'azione del PLAYER parte dal
    # giocatore: non facciamo perdere la sua azione a causa di un tiro
    # d'iniziativa astratto.
    state.turn_order = [actor_id, target_id]
    state.current_turn_character_id = actor_id
    state.get_combatant(actor_id).reset_turn_resources()
    state.get_combatant(target_id).action_points = 0
    save_combat(extra, state)
    return state


def _npc_action(state: CombatState, npc_id: int, player_id: int) -> CombatEvent | None:
    npc = state.get_combatant(npc_id)
    if not npc.alive or npc.defeated or state.phase != "active":
        return None

    if npc.health <= max(1, npc.max_health // 4):
        action = CombatAction(character_id=npc_id, action="flee")
    elif npc.abilities and npc.mana >= 5:
        action = CombatAction(
            character_id=npc_id,
            action="ability",
            target_id=player_id,
            ability=str(npc.abilities[0].get("name") or ""),
        )
    else:
        action = CombatAction(character_id=npc_id, action="attack", target_id=player_id)

    return resolve_action(state, action)


def resolve_narrative_combat(extra: dict[str, Any], actor_id: int, action: dict[str, Any]) -> dict[str, Any]:
    target_id = action.get("target_id")
    if not isinstance(target_id, int) or isinstance(target_id, bool):
        raise ValueError("Il combattimento richiede un target_id numerico.")

    state = load_combat(extra)
    if state is None or state.phase != "active":
        state = start_combat(extra, actor_id, target_id)

    combat_action = CombatAction(
        character_id=actor_id,
        action={
            "attack": "attack",
            "defend": "defend",
            "cast_magic": "ability",
            "flee": "flee",
        }.get(str(action.get("type")), str(action.get("type"))),
        target_id=target_id,
        ability=str((action.get("parameters") or {}).get("ability") or (action.get("target_text") or "")) or None,
        description=str((action.get("parameters") or {}).get("description") or ""),
        intent=str((action.get("parameters") or {}).get("intent") or ""),
    )

    event_start = len(state.events)
    event = resolve_action(state, combat_action)

    # Il turno NPC viene risolto automaticamente quando il giocatore ha ancora
    # un avversario vivo. Questo mantiene il combattimento dentro il flusso
    # conversazionale senza trasformarlo in un menu separato.
    npc_events: list[CombatEvent] = []
    if state.phase == "active":
        opponent_ids = [cid for cid in state.combatants if cid != actor_id]
        if opponent_ids:
            npc_id = opponent_ids[0]
            if state.current_turn_character_id != npc_id:
                state.current_turn_character_id = npc_id
                state.get_combatant(npc_id).reset_turn_resources()
            npc_event = _npc_action(state, npc_id, actor_id)
            if npc_event is not None:
                npc_events.append(npc_event)

            if state.phase == "active":
                state.current_turn_character_id = actor_id
                state.get_combatant(actor_id).reset_turn_resources()

    save_combat(extra, state)
    new_events = state.events[event_start:]
    return {
        "combat_state": state.to_dict(),
        "events": [item.to_dict() for item in new_events],
        "last_event": event.to_dict(),
        "finished": state.phase != "active",
        "winner_id": state.winner_id,
    }
