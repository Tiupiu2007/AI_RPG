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
from app.combat.decks import ensure_initialized, get_card_catalog_for_character, get_deck, learn_card, toggle_deck_card
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
_DRAW_PER_TURN = 5


def _cleanup() -> None:
    now = time.time()
    for room_id in [rid for rid, room in _ROOMS.items() if now - room.last_activity > _ROOM_TTL]:
        _ROOMS.pop(room_id, None)


def _load_character(character_id: int) -> dict[str, Any]:
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio {character_id} non trovato.")
    return character


def _build_deck(character: dict[str, Any]) -> list[str]:
    ensure_initialized(character)
    deck_state = get_deck(int(character["id"]))
    catalog = {card["id"]: card for card in load_cards()}
    deck = [card_id for card_id in deck_state["deck"] if card_id in catalog and can_learn_card(catalog[card_id], character)[0]]
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


def _advance_conditions(state: CombatState, character_id: int) -> None:
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
    _advance_conditions(state, character_id)
    drawn = _draw_cards(state, character_id, _DRAW_PER_TURN)
    state.add_event("cards_drawn", f"{state.get_combatant(character_id).name} pesca {drawn} carte.", actor_id=character_id, drawn=drawn, hand_size=len(_runtime(state, character_id)["hand"]))


def create_room(character_a_id: int, character_b_id: int) -> dict[str, Any]:
    if character_a_id == character_b_id:
        raise ValueError("Devi selezionare due personaggi diversi.")
    a = _load_character(character_a_id)
    b = _load_character(character_b_id)
    ensure_initialized(a)
    ensure_initialized(b)
    room_id = uuid.uuid4().hex[:12]
    tokens = {secrets.token_urlsafe(24): character_a_id, secrets.token_urlsafe(24): character_b_id}
    player_a_token, player_b_token = list(tokens.keys())
    spectator_token = secrets.token_urlsafe(24)
    state = create_combat([a, b], combat_id=room_id, metadata={"mode": "pvp-1v1", "style": "slay-the-spire", "created_by_server": True})
    _init_card_runtime(state, [a, b], seed=state.metadata.get("seed"))
    now = time.time()
    with _LOCK:
        _cleanup()
        _ROOMS[room_id] = PvPRoom(room_id, state, tokens, spectator_token, now, now)
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
    hand = [get_card(card_id) for card_id in runtime["hand"]]
    return {"hand": [card for card in hand if card], "hand_ids": list(runtime["hand"]), "draw_count": len(runtime["draw_pile"]), "discard_count": len(runtime["discard_pile"]), "exhaust_count": len(runtime["exhausted"])}


def _public_combatant(combatant: Any, own: bool, spectator: bool, state: CombatState) -> dict[str, Any]:
    data = combatant.to_dict()
    if spectator or own:
        data["cards"] = _card_view(state, combatant.character_id)
        return data
    return {key: data[key] for key in ("character_id", "name", "health", "max_health", "stamina", "max_stamina", "mana", "max_mana", "action_points", "max_action_points", "status", "alive", "defeated", "conditions")}


def _deck_payload(character: dict[str, Any]) -> dict[str, Any]:
    state = get_deck(int(character["id"]))
    return {"known": state["known"], "deck": state["deck"], "catalog": get_card_catalog_for_character(character)}


def serialize_room(room_id: str, token: str | None = None) -> dict[str, Any]:
    room = _room(room_id)
    spectator = token == room.spectator_token
    player_character_id = room.player_tokens.get(token or "")
    if not spectator and player_character_id is None:
        raise ValueError("Token della stanza non valido.")
    state = room.state
    result = {"room_id": room.room_id, "mode": "pvp-1v1", "phase": state.phase, "round_number": state.round_number, "current_turn_character_id": state.current_turn_character_id, "winner_id": state.winner_id, "loser_ids": list(state.loser_ids), "turn_order": list(state.turn_order), "you_are": "spectator" if spectator else player_character_id, "is_spectator": spectator, "combatants": {str(cid): _public_combatant(c, spectator or cid == player_character_id, spectator, state) for cid, c in state.combatants.items()}, "events": [event.to_dict() for event in state.events[-100:]], "rules": {"action_points_per_turn": 3, "physical_attack_ap": 2, "ability_ap": 1, "ability_uses_mana": True, "physical_attack_uses_stamina": True, "starting_hand": _DRAW_PER_TURN, "draw_per_turn": _DRAW_PER_TURN, "discard_hand_at_end_turn": True, "reshuffle_discard_when_draw_pile_empty": True, "temporary_conditions_tick_on_owner_turn": True, "exhaust_supported": True}}
    if not spectator:
        result["deck"] = _deck_payload(_load_character(player_character_id))
    else:
        result["deck"] = None
    return result


def _apply_effect(state: CombatState, actor: Any, target: Any, effect: dict[str, Any], rng: random.Random) -> list[str]:
    effect_type = str(effect.get("type", "")).strip().lower()
    amount = max(0, int(effect.get("amount", 0) or 0))
    messages: list[str] = []
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
            target.conditions.append(condition)
            duration = int(effect.get("duration_turns", 0) or 0)
            if duration > 0:
                registry = state.metadata.setdefault("temporary_conditions", {})
                registry.setdefault(str(target.character_id), []).append({"condition": condition, "turns": duration})
            messages.append(f"applica {condition}" + (f" per {duration} turno/i" if duration > 0 else ""))
    elif effect_type == "remove_condition":
        condition = str(effect.get("condition", "")).strip()
        if condition:
            target.conditions = [x for x in target.conditions if x != condition]
            messages.append(f"rimuove {condition}")
    elif effect_type == "draw_cards":
        messages.append(f"pesca {_draw_cards(state, actor.character_id, amount or 1)} carte")
    elif effect_type == "discard_random":
        runtime = _runtime(state, actor.character_id)
        count = min(amount or 1, len(runtime["hand"]))
        for _ in range(count):
            runtime["discard_pile"].append(runtime["hand"].pop(rng.randrange(len(runtime["hand"]))))
        messages.append(f"scarta {count} carta/e")
    return messages


def _play_card(state: CombatState, actor: Any, target_id: int | None, card_id: str, rng: random.Random) -> None:
    card = get_card(card_id)
    if card is None:
        raise ValueError("Carta non trovata nel catalogo.")
    runtime = _runtime(state, actor.character_id)
    if card_id not in runtime["hand"]:
        raise ValueError("Questa carta non è nella tua mano.")
    target = state.get_combatant(target_id) if target_id is not None else actor
    ap_cost = int(card.get("action_points_cost", 1) or 0)
    mana_cost = int(card.get("mana_cost", 0) or 0)
    if card.get("resource") == "action_points":
        ap_cost = int(card.get("cost", ap_cost))
    elif card.get("resource") == "mana":
        mana_cost = int(card.get("cost", mana_cost))
    if actor.action_points < ap_cost:
        raise ValueError("Non hai abbastanza PA per giocare questa carta.")
    if actor.mana < mana_cost:
        raise ValueError("Non hai abbastanza mana per giocare questa carta.")
    actor.action_points -= ap_cost
    actor.mana -= mana_cost
    messages: list[str] = []
    for effect in card.get("effects", []):
        if isinstance(effect, dict):
            messages.extend(_apply_effect(state, actor, target, effect, rng))
    if card.get("exhaust") or str(card.get("type", "")).lower() == "power":
        _exhaust_card(state, actor.character_id, card_id)
        pile = "exhausted"
    else:
        _discard_card(state, actor.character_id, card_id)
        pile = "discard_pile"
    state.add_event("card_played", f"{actor.name} gioca {card['name']}" + (f": {', '.join(messages)}." if messages else "."), actor_id=actor.character_id, target_id=target.character_id, card_id=card_id, card_name=card["name"], action_points_spent=ap_cost, mana_spent=mana_cost, remaining_action_points=actor.action_points, pile=pile)
    if not target.alive:
        target.defeated = True
        target.status = "Sconfitto"
        state.add_event("defeat", f"{target.name} è sconfitto.", actor_id=actor.character_id, target_id=target.character_id)
        state.check_finished()


def _finish_turn(state: CombatState, character_id: int) -> None:
    if state.phase != "active" or state.current_turn_character_id != character_id:
        return
    discarded = _discard_hand(state, character_id)
    if discarded:
        state.add_event("hand_discarded", f"{state.get_combatant(character_id).name} scarta la mano.", actor_id=character_id, discarded=discarded)
    resolve_action(state, CombatAction(character_id=character_id, action="end_turn"))
    if state.phase == "active" and state.current_turn_character_id is not None:
        _prepare_next_turn_cards(state, state.current_turn_character_id)


def _deck_action(room: PvPRoom, character_id: int, action: str, card_id: str) -> None:
    character = _load_character(character_id)
    if action == "deck_learn":
        learn_card(character, card_id)
        return
    if action == "deck_toggle":
        toggle_deck_card(character, card_id)
        return
    raise ValueError("Azione mazzo non supportata.")


def perform_action(room_id: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    room = _room(room_id)
    character_id = room.player_tokens.get(token)
    if character_id is None:
        raise ValueError("Token giocatore non valido.")
    action_name = str(payload.get("action", "")).strip().lower()
    if action_name in {"deck_learn", "deck_toggle"}:
        _deck_action(room, character_id, action_name, str(payload.get("card_id", "")))
        room.last_activity = time.time()
        return serialize_room(room_id, token)
    if room.state.current_turn_character_id != character_id:
        raise ValueError("Non è il tuo turno.")
    if action_name == "card":
        _play_card(room.state, room.state.get_combatant(character_id), payload.get("target_id"), str(payload.get("card_id", "")), random.Random())
        if room.state.phase == "active" and room.state.get_combatant(character_id).action_points <= 0:
            _finish_turn(room.state, character_id)
    elif action_name in {"end_turn", "end", "pass_turn"}:
        _finish_turn(room.state, character_id)
    else:
        action_payload = dict(payload)
        action_payload["character_id"] = character_id
        resolve_action(room.state, CombatAction.from_dict(action_payload))
    room.last_activity = time.time()
    return serialize_room(room_id, token)


def get_room_character_ids(room_id: str) -> list[int]:
    return list(_room(room_id).state.combatants.keys())
