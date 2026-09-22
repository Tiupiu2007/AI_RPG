from __future__ import annotations

from typing import Any

from app.database.characters_db import get_character, save_character
from app.memory.memory import create_memory
from app.relationships.relationships import change_relationship

SOCIAL_FIELDS = ("trust", "affection", "respect", "hostility")
MAX_SOCIAL_DELTA = 5
MAX_MEMORY_LENGTH = 400


def _clamp_delta(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("Una variazione sociale deve essere un intero.")
    return max(-MAX_SOCIAL_DELTA, min(MAX_SOCIAL_DELTA, value))


def _present(extra: dict[str, Any], character_id: int) -> bool:
    raw = extra.get("characters_present", [])
    if not isinstance(raw, list):
        return False
    for item in raw:
        candidate = item.get("id", item.get("character_id")) if isinstance(item, dict) else item
        if candidate == character_id:
            return True
    return False


def _update_npc_state(character_id: int, effects: dict[str, Any]) -> dict[str, Any]:
    npc = get_character(character_id)
    if npc is None:
        raise ValueError(f"NPC con ID {character_id} non trovato.")
    extra = npc.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    state = extra.get("state", {})
    if not isinstance(state, dict):
        state = {}
    for field in ("emotion", "thought", "intention", "goal"):
        value = effects.get(field)
        if isinstance(value, str) and value.strip():
            state[field] = " ".join(value.strip().split())[:500]
    extra["state"] = state
    save_character(npc["identity"], npc.get("languages", []), extra_data=extra, character_id=character_id)
    return state


def apply_social_effects(
    actor_id: int,
    target_id: int,
    effects: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    """Applica conseguenze sociali proposte dall'AI entro limiti dell'engine."""
    if not isinstance(actor_id, int) or isinstance(actor_id, bool):
        raise ValueError("actor_id non valido.")
    if not isinstance(target_id, int) or isinstance(target_id, bool):
        raise ValueError("target_id non valido.")
    if actor_id == target_id:
        raise ValueError("Un personaggio non può avere un effetto sociale su se stesso.")
    if not isinstance(effects, dict):
        raise ValueError("social_effects deve essere un oggetto.")
    if not _present(extra, target_id):
        raise ValueError("L'NPC non è presente nella scena.")

    deltas = {}
    for field in SOCIAL_FIELDS:
        if field in effects:
            delta = _clamp_delta(effects[field])
            if delta:
                deltas[field] = delta

    relationship = change_relationship(actor_id, target_id, **deltas) if deltas else None
    npc_state = _update_npc_state(target_id, effects)

    memory_id = None
    memory = effects.get("memory")
    if isinstance(memory, dict):
        content = memory.get("content")
        importance = memory.get("importance", 5)
        if isinstance(content, str) and content.strip() and isinstance(importance, int):
            if 5 <= importance <= 8 and len(content.strip()) <= MAX_MEMORY_LENGTH:
                memory_id = create_memory(
                    character_id=target_id,
                    content=content.strip(),
                    memory_type="evento_importante",
                    importance=importance,
                    secret=False,
                )

    return {
        "target_id": target_id,
        "relationship": relationship,
        "npc_state": npc_state,
        "memory_id": memory_id,
    }
