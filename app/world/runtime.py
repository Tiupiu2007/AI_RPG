from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from .world_repository import WorldRepository
from .world_state import WorldState


WORLD_DATABASE_PATH = Path("data/worlds.db")
_repository = WorldRepository(WORLD_DATABASE_PATH)


def _world_name(extra: dict[str, Any]) -> str:
    value = extra.get("world_name")
    return str(value).strip() if isinstance(value, str) and value.strip() else "Mondo principale"


def ensure_world(extra: dict[str, Any]) -> WorldState:
    if not isinstance(extra, dict):
        raise ValueError("extra deve essere un dizionario.")

    world_id = extra.get("world_id")
    world = _repository.load(str(world_id)) if world_id else None
    if world is None:
        world = WorldState.create(
            _world_name(extra),
            str(extra.get("world_description") or "").strip(),
        )
        _repository.save(world)
        extra["world_id"] = world.world_id
    return world


def advance_world(extra: dict[str, Any], minutes: int = 1) -> dict[str, Any]:
    world = ensure_world(extra)
    minutes = max(0, int(minutes))
    before = world.clock.to_dict()
    if minutes:
        world.advance_time_minutes(minutes)
        _repository.save(world)
    return {
        "world_id": world.world_id,
        "before": before,
        "after": world.clock.to_dict(),
    }


def record_world_event(extra: dict[str, Any], event_type: str, payload: dict[str, Any]) -> str:
    world = ensure_world(extra)
    event_id = uuid.uuid4().hex
    world.events[event_id] = {
        "type": str(event_type),
        "payload": dict(payload),
        "timestamp": world.clock.to_dict(),
    }
    # Evitiamo che la cronologia tecnica del mondo cresca senza limite.
    if len(world.events) > 500:
        oldest = list(world.events)[:-500]
        for key in oldest:
            world.events.pop(key, None)
    world.update()
    _repository.save(world)
    return event_id


def get_world_context(extra: dict[str, Any]) -> dict[str, Any]:
    world = ensure_world(extra)
    return {
        "world_id": world.world_id,
        "name": world.name,
        "description": world.description,
        "clock": world.clock.to_dict(),
        "location_ids": sorted(world.locations.keys()),
        "recent_world_events": list(world.events.values())[-12:],
        "factions": sorted(world.factions.factions.keys()),
        "settlements": sorted(world.settlements.settlements.keys()),
    }
