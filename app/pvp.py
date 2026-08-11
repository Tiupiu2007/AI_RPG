from __future__ import annotations

import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

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


def create_room(character_a_id: int, character_b_id: int) -> dict[str, Any]:
    if character_a_id == character_b_id:
        raise ValueError("Devi selezionare due personaggi diversi.")

    a = _load_character(character_a_id)
    b = _load_character(character_b_id)
    room_id = uuid.uuid4().hex[:12]
    player_a_token = secrets.token_urlsafe(24)
    player_b_token = secrets.token_urlsafe(24)
    spectator_token = secrets.token_urlsafe(24)

    state = create_combat(
        [a, b],
        combat_id=room_id,
        metadata={
            "mode": "pvp-1v1",
            "style": "slay-the-spire",
            "created_by_server": True,
        },
    )
    now = time.time()
    room = PvPRoom(
        room_id=room_id,
        state=state,
        player_tokens={player_a_token: character_a_id, player_b_token: character_b_id},
        spectator_token=spectator_token,
        created_at=now,
        last_activity=now,
    )
    with _LOCK:
        _cleanup()
        _ROOMS[room_id] = room
    return {
        "room_id": room_id,
        "player_a_token": player_a_token,
        "player_b_token": player_b_token,
        "spectator_token": spectator_token,
        "player_a_character_id": character_a_id,
        "player_b_character_id": character_b_id,
    }


def _room(room_id: str) -> PvPRoom:
    with _LOCK:
        _cleanup()
        room = _ROOMS.get(room_id)
    if room is None:
        raise ValueError("Stanza PvP non trovata o scaduta.")
    room.last_activity = time.time()
    return room


def get_editor_character_id(room_id: str, token: str | None) -> int | None:
    """Restituisce il personaggio associato al token PvP.

    Il token spettatore non dà accesso all'editor. Solo i due token giocatore
    possono aprire la scheda del proprio personaggio.
    """
    room = _room(room_id)
    if not token or token == room.spectator_token:
        return None
    return room.player_tokens.get(token)


def _public_combatant(combatant: Any, own: bool, spectator: bool) -> dict[str, Any]:
    data = combatant.to_dict()
    if spectator or own:
        return data
    return {
        "character_id": data["character_id"],
        "name": data["name"],
        "health": data["health"],
        "max_health": data["max_health"],
        "stamina": data["stamina"],
        "max_stamina": data["max_stamina"],
        "mana": data["mana"],
        "max_mana": data["max_mana"],
        "action_points": data["action_points"],
        "max_action_points": data["max_action_points"],
        "status": data["status"],
        "alive": data["alive"],
        "defeated": data["defeated"],
        "conditions": data["conditions"],
        "abilities": [{"name": item.get("name", "Abilità")} for item in data.get("abilities", [])],
        "skills": [{"name": item.get("name", "Skill")} for item in data.get("skills", [])],
    }


def serialize_room(room_id: str, token: str | None = None) -> dict[str, Any]:
    room = _room(room_id)
    spectator = token == room.spectator_token
    player_character_id = room.player_tokens.get(token or "")
    if not spectator and player_character_id is None:
        raise ValueError("Token della stanza non valido.")

    state = room.state
    return {
        "room_id": room.room_id,
        "mode": "pvp-1v1",
        "phase": state.phase,
        "round_number": state.round_number,
        "current_turn_character_id": state.current_turn_character_id,
        "winner_id": state.winner_id,
        "loser_ids": list(state.loser_ids),
        "turn_order": list(state.turn_order),
        "you_are": "spectator" if spectator else player_character_id,
        "is_spectator": spectator,
        "combatants": {
            str(cid): _public_combatant(combatant, spectator or cid == player_character_id, spectator)
            for cid, combatant in state.combatants.items()
        },
        "events": [event.to_dict() for event in state.events[-80:]],
        "rules": {
            "action_points_per_turn": 3,
            "physical_attack_ap": 2,
            "ability_ap": 1,
            "ability_uses_mana": True,
            "physical_attack_uses_stamina": True,
            "description": "Le abilità/magie costano meno PA e sono generalmente più forti, ma consumano mana.",
        },
    }


def perform_action(room_id: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    room = _room(room_id)
    character_id = room.player_tokens.get(token)
    if character_id is None:
        raise ValueError("Token giocatore non valido.")

    if room.state.current_turn_character_id != character_id:
        raise ValueError("Non è il tuo turno.")

    action_payload = dict(payload)
    action_payload["character_id"] = character_id
    action = CombatAction.from_dict(action_payload)
    resolve_action(room.state, action)
    room.last_activity = time.time()
    return serialize_room(room_id, token)


def get_room_character_ids(room_id: str) -> list[int]:
    room = _room(room_id)
    return list(room.state.combatants.keys())
