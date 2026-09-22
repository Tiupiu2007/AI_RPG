from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from .world_repository import WorldRepository
from .world_state import WorldState
from .locations import Location


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



def move_actor(extra: dict[str, Any], actor_id: int, target_id: str | None = None, target_name: str | None = None) -> dict[str, Any]:
    world = ensure_world(extra)
    target = None

    if target_id:
        target = world.get_location(str(target_id))

    if target is None and target_name:
        wanted = " ".join(str(target_name).strip().split()).lower()
        for location in world.locations.values():
            if location.name.strip().lower() == wanted:
                target = location
                break

    if target is None and target_name:
        normalized = " ".join(str(target_name).strip().split())
        slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in normalized).strip("_")
        location_id = "loc_" + (slug[:80] or uuid.uuid4().hex)
        if location_id in world.locations:
            target = world.locations[location_id]
        else:
            target = Location.create(normalized, "area", location_id=location_id)
            world.add_location(target)

    if target is None:
        raise ValueError("Destinazione non trovata.")

    previous = extra.get("game_state", {}).get("location")
    extra["game_state"]["location"] = target.location_id
    target.add_character(str(actor_id))
    world.update()
    _repository.save(world)
    return {"from": previous, "to": target.location_id, "name": target.name}

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
