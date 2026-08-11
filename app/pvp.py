from __future__ import annotations

import random
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.combat.cards import can_learn_card, get_card, load_cards
from app.combat.combat_engine import create_combat, resolve_action
from app.combat.combat_models import CombatAction, CombatState
from app.database.characters_db import get_character


@dataclass
class PvPRoom:
    room_id: str
    state: CombatState
    player_tokens: dict[str, int]
    spectator_token: str
    created_at: float
    last_activity: float


_ROOMS: dict[str, PvPRoom] = {}
_LOCK = threading.RLock()
_ROOM_TTL = 24 * 60 * 60
_HAND_SIZE = 5
_DRAW_PER_TURN = 5


def _cleanup() -> None:
    now = time.time()
    expired = [room_id for room_id, room in _ROOMS.items() if now - room.last_activity > _ROOM_TTL]
    for room_id in expired:
        _ROOMS.pop(room_id, None)


def _load_character(character_id: int) -> dict[str, Any]:
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio {character_id} non trovato.")
    return character


def _known_card_ids(character: dict[str, Any]) -> list[str]:
    extra = character.get("extra", {}) if isinstance(character, dict) else {}
    if not isinstance(extra, dict):
        extra = {}
    raw = extra.get("deck", extra.get("cards", []))
    if not isinstance(raw, list):
        raw = []
    ids: list[str] = []
    for item in raw:
        card_id = item.get("id") if isinstance(item, dict) else item
        if card_id:
            ids.append(str(card_id).strip())
    return list(dict.fromkeys(x for x in ids if x))


def _build_deck(character: dict[str, Any]) -> list[str]:
    all_cards = {card["id"]: card for card in load_cards()}
    known = _known_card_ids(character)
    deck = [card_id for card_id in known if card_id in all_cards and can_learn_card(all_cards[card_id], character)[0]]
    if not deck:
        deck = [card_id for card_id in ("starter_strike", "starter_guard", "arcane_bolt") if card_id in all_cards and can_learn_card(all_cards[card_id], character)[0]]
    if not deck:
        raise ValueError(f"{character.get('identity', {}).get('name', 'Personaggio')} non possiede carte utilizzabili.")
    return deck


def _init_card_runtime(state: CombatState, characters: list[dict[str, Any]], seed: int | None = None) -> None:
    rng = random.Random(seed)
    runtime: dict[str, Any] = {}
    for character in characters:
        cid = int(character["id"])
        deck = _build_deck(character)
        draw_pile = list(deck) + list(deck)
        rng.shuffle(draw_pile)
        runtime[str(cid)] = {"draw_pile": draw_pile, "hand": [], "discard_pile": [], "exhausted": []}
    state.metadata["cards"] = runtime
    state.metadata["temporary_conditions"] = {}
    for cid in state.turn_order:
        _draw_cards(state, cid, _DRAW_PER_TURN)


def _runtime(state: CombatState, character_id: int) -> dict[str, Any]:
    cards = state.metadata.setdefault("cards", {})
    return cards.setdefault(str(character_id), {"draw_pile": [], "hand": [], "discard_pile": [], "exhausted": []})


def _draw_cards(state: CombatState, character_id: int, amount: int) -> int:
    runtime = _runtime(state, character_id)
    drawn = 0
    for _ in range(max(0, amount)):
        if not runtime["draw_pile"]:
            if not runtime["discard_pile"]:
                break
            runtime["draw_pile"] = list(runtime["discard_pile"])
            runtime["discard_pile"] = []
            random.Random(f"{state.combat_id}:{state.round_number}:{character_id}:{drawn}").shuffle(runtime["draw_pile"])
        runtime["hand"].append(runtime["draw_pile"].pop())
        drawn += 1
    return drawn


def _discard_card(state: CombatState, character_id: int, card_id: str) -> None:
    runtime = _runtime(state, character_id)
    if card_id in runtime["hand"]:
        runtime["hand"].remove(card_id)
        runtime["discard_pile"].append(card_id)


def _discard_hand(state: CombatState, character_id: int) -> int:
    runtime = _runtime(state, character_id)
    count = len(runtime["hand"])
    if count:
        runtime["discard_pile"].extend(runtime["hand"])
        runtime["hand"] = []
    return count


def _exhaust_card(state: CombatState, character_id: int, card_id: str) -> None:
    runtime = _runtime(state, character_id)
    if card_id in runtime["hand"]:
        runtime["hand"].remove(card_id)
    runtime["exhausted"].append(card_id)


def _advance_temporary_conditions(state: CombatState, character_id: int) -> None:
    registry = state.metadata.setdefault("temporary_conditions", {})
    entries = registry.get(str(character_id), [])
    if not isinstance(entries, list):
        entries = []
    combatant = state.get_combatant(character_id)
    remaining: list[dict[str, Any]] = []
    expired: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        condition = str(entry.get("condition", "")).strip()
        turns = int(entry.get("turns", 0) or 0) - 1
        if turns <= 0:
            if condition in combatant.conditions:
                combatant.conditions.remove(condition)
            if condition:
                expired.append(condition)
        else:
            entry["turns"] = turns
            remaining.append(entry)
    registry[str(character_id)] = remaining
    if expired:
        state.add_event("conditions_expired", f"Terminano gli effetti temporanei di {combatant.name}: {', '.join(expired)}.", actor_id=character_id, expired_conditions=expired)


def _prepare_next_turn_cards(state: CombatState, character_id: int) -> None:
    _discard_hand(state, character_id)
    _advance_temporary_conditions(state, character_id)
    drawn = _draw_cards(state, character_id, _DRAW_PER_TURN)
    state.add_event("cards_drawn", f"{state.get_combatant(character_id).name} pesca {drawn} carte.", actor_id=character_id, drawn=drawn, hand_size=len(_runtime(state, character_id)["hand"]), draw_pile_count=len(_runtime(state, character_id)["draw_pile"]), discard_count=len(_runtime(state, character_id)["discard_pile"]))


def create_room(character_a_id: int, character_b_id: int) -> dict[str, Any]:
    if character_a_id == character_b_id:
        raise ValueError("Devi selezionare due personaggi diversi.")
    a = _load_character(character_a_id)
    b = _load_character(character_b_id)
    room_id = uuid.uuid4().hex[:12]
    player_a_token = secrets.token_urlsafe(24)
    player_b_token = secrets.token_urlsafe(24)
    spectator_token = secrets.token_urlsafe(24)
    state = create_combat([a, b], combat_id=room_id, metadata={"mode": "pvp-1v1", "style": "slay-the-spire", "created_by_server": True})
    _init_card_runtime(state, [a, b], seed=state.metadata.get("seed"))
    now = time.time()
    room = PvPRoom(room_id=room_id, state=state, player_tokens={player_a_token: character_a_id, player_b_token: character_b_id}, spectator_token=spectator_token, created_at=now, last_activity=now)
    with _LOCK:
        _cleanup()
        _ROOMS[room_id] = room
    return {"room_id": room_id, "player_a_token": player_a_token, "player_b_token": player_b_token, "spectator_token": spectator_token, "player_a_character_id": character_a_id, "player_b_character_id": character_b_id}


def _room(room_id: str) -> PvPRoom:
    with _LOCK:
        _cleanup()
        room = _ROOMS.get(room_id)
    if room is None:
        raise ValueError("Stanza PvP non trovata o scaduta.")
    room.last_activity = time.time()
    return room


def get_editor_character_id(room_id: str, token: str | None) -> int | None:
    room = _room(room_id)
    if not token or token == room.spectator_token:
        return None
    return room.player_tokens.get(token)


def _card_view(state: CombatState, character_id: int) -> dict[str, Any]:
    runtime = _runtime(state, character_id)
    result: dict[str, Any] = {}
    for card_id in runtime["hand"]:
        card = get_card(card_id)
        if card:
            result[card_id] = card
    return {"hand": list(result.values()), "hand_ids": list(runtime["hand"]), "draw_count": len(runtime["draw_pile"]), "discard_count": len(runtime["discard_pile"]), "exhaust_count": len(runtime["exhausted"])}


def _public_combatant(combatant: Any, own: bool, spectator: bool, state: CombatState) -> dict[str, Any]:
    data = combatant.to_dict()
    if spectator or own:
        data["cards"] = _card_view(state, combatant.character_id)
        return data
    return {"character_id": data["character_id"], "name": data["name"], "health": data["health"], "max_health": data["max_health"], "stamina": data["stamina"], "max_stamina": data["max_stamina"], "mana": data["mana"], "max_mana": data["max_mana"], "action_points": data["action_points"], "max_action_points": data["max_action_points"], "status": data["status"], "alive": data["alive"], "defeated": data["defeated"], "conditions": data["conditions"], "cards": {"hand_count": len(_runtime(state, combatant.character_id)["hand"])} }


def serialize_room(room_id: str, token: str | None = None) -> dict[str, Any]:
    room = _room(room_id)
    spectator = token == room.spectator_token
    player_character_id = room.player_tokens.get(token or "")
    if not spectator and player_character_id is None:
        raise ValueError("Token della stanza non valido.")
    state = room.state
    return {"room_id": room.room_id, "mode": "pvp-1v1", "phase": state.phase, "round_number": state.round_number, "current_turn_character_id": state.current_turn_character_id, "winner_id": state.winner_id, "loser_ids": list(state.loser_ids), "turn_order": list(state.turn_order), "you_are": "spectator" if spectator else player_character_id, "is_spectator": spectator, "combatants": {str(cid): _public_combatant(combatant, spectator or cid == player_character_id, spectator, state) for cid, combatant in state.combatants.items()}, "events": [event.to_dict() for event in state.events[-100:]], "rules": {"action_points_per_turn": 3, "physical_attack_ap": 2, "ability_ap": 1, "ability_uses_mana": True, "physical_attack_uses_stamina": True, "starting_hand": _DRAW_PER_TURN, "draw_per_turn": _DRAW_PER_TURN, "discard_hand_at_end_turn": True, "reshuffle_discard_when_draw_pile_empty": True, "temporary_conditions_tick_on_owner_turn": True, "exhaust_supported": True, "description": "Ogni turno parte con una nuova mano. Le carte non giocate vengono scartate; il mazzo si rimescola quando la pesca è vuota. Le magie/abilità possono costare pochi PA ma consumano mana."}}


def _apply_card_effect(state: CombatState, actor: Any, target: Any, effect: dict[str, Any], rng: random.Random) -> list[str]:
    messages: list[str] = []
    effect_type = str(effect.get("type", "")).strip().lower()
    amount = max(0, int(effect.get("amount", 0) or 0))
    if effect_type == "damage":
        damage = max(1, amount + rng.randint(-2, 2))
        target.health = max(0, target.health - damage)
        target.alive = target.health > 0 and not target.defeated
        messages.append(f"infligge {damage} danni")
    elif effect_type == "heal":
        healed = min(target.max_health - target.health, amount)
        target.health += healed
        messages.append(f"recupera {healed} HP")
    elif effect_type == "gain_stamina":
        gained = min(target.max_stamina - target.stamina, amount)
        target.stamina += gained
        messages.append(f"recupera {gained} stamina")
    elif effect_type == "gain_mana":
        gained = min(target.max_mana - target.mana, amount)
        target.mana += gained
        messages.append(f"recupera {gained} mana")
    elif effect_type == "apply_condition":
        condition = str(effect.get("condition", "effetto")).strip()
        if condition:
            for _ in range(max(1, amount or 1)):
                target.conditions.append(condition)
            duration = int(effect.get("duration_turns", 0) or 0)
            if duration > 0:
                registry = state.metadata.setdefault("temporary_conditions", {})
                entries = registry.setdefault(str(target.character_id), [])
                entries.append({"condition": condition, "turns": duration})
            messages.append(f"applica {condition}" + (f" per {duration} turno/i" if duration > 0 else ""))
    elif effect_type == "remove_condition":
        condition = str(effect.get("condition", "")).strip()
        if condition:
            target.conditions = [x for x in target.conditions if x != condition]
            registry = state.metadata.setdefault("temporary_conditions", {})
            registry[str(target.character_id)] = [x for x in registry.get(str(target.character_id), []) if x.get("condition") != condition]
            messages.append(f"rimuove {condition}")
    elif effect_type == "draw_cards":
        drawn = _draw_cards(state, actor.character_id, amount or 1)
        messages.append(f"pesca {drawn} carte")
    elif effect_type == "discard_random":
        runtime = _runtime(state, actor.character_id)
        count = min(amount or 1, len(runtime["hand"]))
        for _ in range(count):
            index = rng.randrange(len(runtime["hand"]))
            card_id = runtime["hand"].pop(index)
            runtime["discard_pile"].append(card_id)
        messages.append(f"scarta {count} carta/e")
    else:
        messages.append("non produce effetti riconosciuti")
    return messages


def _play_card(state: CombatState, actor: Any, target_id: int | None, card_id: str, rng: random.Random) -> Any:
    target = state.get_combatant(target_id) if target_id is not None else actor
    runtime = _runtime(state, actor.character_id)
    card = get_card(card_id)
    if card is None:
        raise ValueError(f"Carta {card_id!r} non trovata nel catalogo.")
    if card_id not in runtime["hand"]:
        raise ValueError("Questa carta non è nella tua mano.")
    ap_cost = int(card.get("action_points_cost", 1) or 0)
    mana_cost = int(card.get("mana_cost", 0) or 0)
    if card.get("resource") == "action_points":
        ap_cost = int(card.get("cost", ap_cost))
    elif card.get("resource") == "mana":
        mana_cost = int(card.get("cost", mana_cost))
        ap_cost = int(card.get("action_points_cost", 1) or 0)
    if actor.action_points < ap_cost:
        raise ValueError("Non hai abbastanza PA per giocare questa carta.")
    if actor.mana < mana_cost:
        raise ValueError("Non hai abbastanza mana per giocare questa carta.")
    actor.action_points -= ap_cost
    actor.mana -= mana_cost
    effects = card.get("effects", []) if isinstance(card.get("effects"), list) else []
    messages: list[str] = []
    for effect in effects:
        if isinstance(effect, dict):
            messages.extend(_apply_card_effect(state, actor, target, effect, rng))
    if bool(card.get("exhaust", False)) or str(card.get("type", "")).lower() == "power":
        _exhaust_card(state, actor.character_id, card_id)
        pile = "exhausted"
    else:
        _discard_card(state, actor.character_id, card_id)
        pile = "discard_pile"
    if not target.alive:
        target.defeated = True
        target.status = "Sconfitto"
        state.add_event("defeat", f"{target.name} è sconfitto.", actor_id=actor.character_id, target_id=target.character_id)
        state.check_finished()
    return state.add_event("card_played", f"{actor.name} gioca {card['name']}" + (f": {', '.join(messages)}." if messages else "."), actor_id=actor.character_id, target_id=target.character_id, card_id=card_id, card_name=card["name"], action_points_spent=ap_cost, mana_spent=mana_cost, remaining_action_points=actor.action_points, pile=pile, effects=effects)


def _start_next_turn_if_needed(state: CombatState) -> None:
    if state.phase != "active":
        return
    current = state.get_combatant(state.current_turn_character_id)
    if current.action_points > 0:
        return
    _finish_turn_and_prepare_next(state, current.character_id)


def _finish_turn_and_prepare_next(state: CombatState, character_id: int) -> None:
    if state.phase != "active":
        return
    if state.current_turn_character_id != character_id:
        raise ValueError("Il combattente indicato non è il proprietario del turno.")
    discarded = _discard_hand(state, character_id)
    if discarded:
        state.add_event("hand_discarded", f"{state.get_combatant(character_id).name} scarta la mano di fine turno.", actor_id=character_id, discarded=discarded)
    resolve_action(state, CombatAction(character_id=character_id, action="end_turn"))
    if state.phase == "active" and state.current_turn_character_id is not None:
        _prepare_next_turn_cards(state, state.current_turn_character_id)


def perform_action(room_id: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    room = _room(room_id)
    character_id = room.player_tokens.get(token)
    if character_id is None:
        raise ValueError("Token giocatore non valido.")
    if room.state.current_turn_character_id != character_id:
        raise ValueError("Non è il tuo turno.")
    action_name = str(payload.get("action", "")).strip().lower()
    if action_name == "card":
        card_id = str(payload.get("card_id", "")).strip()
        _play_card(room.state, room.state.get_combatant(character_id), payload.get("target_id"), card_id, random.Random())
        if room.state.phase == "active" and room.state.get_combatant(character_id).action_points <= 0:
            _start_next_turn_if_needed(room.state)
    elif action_name in {"end_turn", "end", "pass_turn"}:
        _finish_turn_and_prepare_next(room.state, character_id)
    else:
        action_payload = dict(payload)
        action_payload["character_id"] = character_id
        action = CombatAction.from_dict(action_payload)
        resolve_action(room.state, action)
        if room.state.phase == "active" and room.state.current_turn_character_id != character_id:
            _prepare_next_turn_cards(room.state, room.state.current_turn_character_id)
    room.last_activity = time.time()
    return serialize_room(room_id, token)


def get_room_character_ids(room_id: str) -> list[int]:
    return list(_room(room_id).state.combatants.keys())
