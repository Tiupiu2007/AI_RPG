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


def save_world(extra: dict[str, Any]) -> WorldState:
    world = ensure_world(extra)
    world.update()
    _repository.save(world)
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



def resolve_existing_location(extra: dict[str, Any], target: str) -> Location | None:
    """Risolvi solo una località già presente nel mondo persistente."""
    world = ensure_world(extra)
    wanted = " ".join(str(target).strip().split()).casefold()
    if not wanted:
        return None
    direct = world.get_location(wanted)
    if direct is not None:
        return direct
    for location in world.locations.values():
        if location.location_id.casefold() == wanted or location.name.casefold() == wanted:
            return location
    return None


def reachable_location_ids(extra: dict[str, Any]) -> list[str]:
    """Restituisce solo le destinazioni realmente collegate alla posizione corrente."""
    world = ensure_world(extra)
    current = extra.get("game_state", {}).get("location")
    if current is None:
        return sorted(world.locations.keys())
    routes = world.geography.connected_routes(str(current), available_only=True)
    result = set()
    for route in routes:
        other = route.destination_id if route.origin_id == str(current) else route.origin_id
        if other in world.locations:
            result.add(other)
    return sorted(result)


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
        target = resolve_existing_location(extra, target_name)

    if target is None:
        raise ValueError("Destinazione non trovata nel mondo persistente.")

    previous = extra.get("game_state", {}).get("location")
    if previous is not None and target.location_id != str(previous):
        reachable = set(reachable_location_ids(extra))
        if target.location_id not in reachable:
            raise ValueError("La destinazione non è collegata alla posizione corrente.")
    extra["game_state"]["location"] = target.location_id
    target.add_character(str(actor_id))
    world.update()
    _repository.save(world)
    return {"from": previous, "to": target.location_id, "name": target.name}

def add_character_to_location(extra: dict[str, Any], character_id: int, location_id: str | None = None) -> None:
    world = ensure_world(extra)
    location_id = location_id or extra.get("game_state", {}).get("location")
    if location_id is None:
        return
    location = world.get_location(str(location_id))
    if location is None:
        return
    location.add_character(str(character_id))
    world.update()
    _repository.save(world)


def get_world_context(extra: dict[str, Any]) -> dict[str, Any]:
    world = ensure_world(extra)
    current_id = None
    game_state = extra.get("game_state")
    if isinstance(game_state, dict):
        current_id = game_state.get("location")
    current = world.get_location(str(current_id)) if current_id is not None else None
    return {
        "world_id": world.world_id,
        "name": world.name,
        "description": world.description,
        "clock": world.clock.to_dict(),
        "current_location": (
            {
                "id": current.location_id,
                "name": current.name,
                "type": current.location_type,
                "description": current.description,
                "character_ids": list(current.character_ids),
            }
            if current is not None
            else None
        ),
        "location_ids": sorted(world.locations.keys()),
        "recent_world_events": list(world.events.values())[-12:],
        "factions": sorted(world.factions.factions.keys()),
        "settlements": sorted(world.settlements.settlements.keys()),
    }
