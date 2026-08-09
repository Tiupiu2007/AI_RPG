from app.world.biomes import Biome, BiomeMap
from app.world.geography import Route
from app.world.locations import Location
from app.world.movement import MovementEngine
from app.world.world_state import WorldState


def build_world():
    world = WorldState.create("Test World")
    a = Location.create("A", coordinates={"x": 0, "y": 0})
    b = Location.create("B", coordinates={"x": 10, "y": 0})
    c = Location.create("C", coordinates={"x": 20, "y": 0})
    world.add_location(a)
    world.add_location(b)
    world.add_location(c)
    world.add_route(Route.create(a.location_id, b.location_id, 10, difficulty=1))
    world.add_route(Route.create(b.location_id, c.location_id, 10, difficulty=2))
    return world, a, b, c


def test_route_cannot_be_shorter_than_coordinates():
    world = WorldState.create("Geometry")
    a = Location.create("A", coordinates={"x": 0, "y": 0})
    b = Location.create("B", coordinates={"x": 10, "y": 0})
    world.add_location(a)
    world.add_location(b)
    try:
        world.add_route(Route.create(a.location_id, b.location_id, 5))
    except ValueError:
        return
    raise AssertionError("A route shorter than geometric distance was accepted")


def test_movement_uses_persisted_origin_and_updates_time_and_position():
    world, a, b, _ = build_world()
    world.set_actor_position("hero", a.location_id)
    engine = MovementEngine(world)
    result = engine.travel("hero", b.location_id, base_speed=10)
    assert result.origin_id == a.location_id
    assert result.destination_id == b.location_id
    assert result.travel_minutes == 60
    assert world.require_actor_position("hero").location_id == b.location_id
    assert world.clock.current_time == result.arrived_at


def test_unreachable_destination_does_not_change_position():
    world, a, b, c = build_world()
    isolated = Location.create("D", coordinates={"x": 100, "y": 0})
    world.add_location(isolated)
    world.set_actor_position("hero", a.location_id)
    engine = MovementEngine(world)
    try:
        engine.travel("hero", isolated.location_id, base_speed=10)
    except ValueError:
        pass
    else:
        raise AssertionError("Unreachable destination was accepted")
    assert world.require_actor_position("hero").location_id == a.location_id
    assert world.clock.current_time == world.clock.start_time


def test_world_roundtrip_preserves_geography_biomes_and_position():
    world, a, b, _ = build_world()
    biome_map = BiomeMap()
    biome_map.add_biome(Biome.create("plain", "Pianura", "grass", x_min=-1, x_max=11, y_min=-1, y_max=1))
    biome_map.add_biome(Biome.create("forest", "Foresta", "forest", x_min=11, x_max=21, y_min=-1, y_max=1))
    world.biomes = biome_map
    world.set_actor_position("hero", a.location_id)
    raw = world.to_dict()
    restored = WorldState.from_dict(raw)
    assert restored.get_location(a.location_id) is not None
    assert restored.get_route(next(iter(world.geography.routes))) is not None
    assert restored.require_actor_position("hero").location_id == a.location_id
    assert restored.biomes.biome_at(a.coordinates) == "plain"
    assert restored.biomes.biome_at(b.coordinates) == "plain"


def test_travel_cannot_start_twice():
    world, a, b, _ = build_world()
    world.set_actor_position("hero", a.location_id)
    position = world.require_actor_position("hero")
    position.begin_travel(b.location_id, tuple(world.geography.routes.keys())[:1])
    engine = MovementEngine(world)
    try:
        engine.travel("hero", b.location_id, base_speed=10)
    except ValueError:
        return
    raise AssertionError("Movement started while actor was already traveling")
