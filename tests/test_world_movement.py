from app.world.biomes import BiomeDefinition, BiomeMap, BiomeRegion
from app.world.geography import Route
from app.world.locations import Location
from app.world.movement import MovementEngine
from app.world.world_state import WorldState


def build_world():
    world = WorldState.create("Test World")
    a = Location.create("A", "area", coordinates={"x": 0, "y": 0})
    b = Location.create("B", "area", coordinates={"x": 10, "y": 0})
    c = Location.create("C", "area", coordinates={"x": 20, "y": 0})
    world.add_location(a)
    world.add_location(b)
    world.add_location(c)
    world.add_route(Route.create(a.location_id, b.location_id, 10, difficulty=1))
    world.add_route(Route.create(b.location_id, c.location_id, 10, difficulty=2))
    return world, a, b, c


def test_route_cannot_be_shorter_than_coordinates():
    world = WorldState.create("Geometry")
    a = Location.create("A", "area", coordinates={"x": 0, "y": 0})
    b = Location.create("B", "area", coordinates={"x": 10, "y": 0})
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
    isolated = Location.create("D", "area", coordinates={"x": 100, "y": 0})
    world.add_location(isolated)
    world.set_actor_position("hero", a.location_id)
    initial_time = world.clock.current_time
    engine = MovementEngine(world)
    try:
        engine.travel("hero", isolated.location_id, base_speed=10)
    except ValueError:
        pass
    else:
        raise AssertionError("Unreachable destination was accepted")
    assert world.require_actor_position("hero").location_id == a.location_id
    assert world.clock.current_time == initial_time


def test_world_roundtrip_preserves_geography_biomes_and_position():
    world, a, b, c = build_world()
    biome_map = BiomeMap()
    biome_map.add_definition(
        BiomeDefinition(biome_id="plain", name="Pianura", terrain="grass")
    )
    biome_map.add_definition(
        BiomeDefinition(biome_id="forest", name="Foresta", terrain="forest")
    )
    biome_map.add_region(
        BiomeRegion(
            region_id="plain-region",
            biome_id="plain",
            center={"x": 5, "y": 0},
            radius=6,
        )
    )
    biome_map.add_region(
        BiomeRegion(
            region_id="forest-region",
            biome_id="forest",
            center={"x": 20, "y": 0},
            radius=2,
        )
    )
    world.biomes = biome_map
    world.set_actor_position("hero", a.location_id)
    raw = world.to_dict()
    restored = WorldState.from_dict(raw)
    assert restored.get_location(a.location_id) is not None
    assert restored.get_route(next(iter(world.geography.routes))) is not None
    assert restored.require_actor_position("hero").location_id == a.location_id
    assert restored.biomes.biome_at(a.coordinates) == "plain"
    assert restored.biomes.biome_at(b.coordinates) == "plain"
    assert restored.biomes.biome_at(c.coordinates) == "forest"


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


def test_set_actor_position_cannot_teleport_actor_during_travel():
    world, a, b, _ = build_world()
    world.set_actor_position("hero", a.location_id)
    position = world.require_actor_position("hero")
    route_to_b = next(
        route for route in world.geography.routes.values()
        if route.origin_id == a.location_id and route.destination_id == b.location_id
    )
    world.begin_actor_travel("hero", b.location_id, (route_to_b.route_id,))
    initial_updated_at = world.updated_at
    initial_destination = position.destination_id
    initial_routes = position.route_ids

    try:
        world.set_actor_position("hero", b.location_id)
    except ValueError:
        pass
    else:
        raise AssertionError("An actor was repositioned while traveling")

    current = world.require_actor_position("hero")
    assert current is position
    assert current.location_id == a.location_id
    assert current.is_traveling
    assert current.destination_id == initial_destination == b.location_id
    assert current.route_ids == initial_routes == (route_to_b.route_id,)
    assert world.updated_at == initial_updated_at


def test_begin_actor_travel_rejects_route_path_that_does_not_reach_destination():
    world, a, b, c = build_world()
    world.set_actor_position("hero", a.location_id)
    route_to_b = next(
        route for route in world.geography.routes.values()
        if route.origin_id == a.location_id and route.destination_id == b.location_id
    )
    initial_updated_at = world.updated_at

    try:
        world.begin_actor_travel("hero", c.location_id, (route_to_b.route_id,))
    except ValueError:
        pass
    else:
        raise AssertionError("A route path ending at the wrong location was accepted")

    position = world.require_actor_position("hero")
    assert position.location_id == a.location_id
    assert not position.is_traveling
    assert position.destination_id is None
    assert world.updated_at == initial_updated_at


def test_begin_actor_travel_rejects_unavailable_route_without_mutating_position():
    world, a, b, _ = build_world()
    world.set_actor_position("hero", a.location_id)
    route = next(iter(world.geography.routes.values()))
    route.set_available(False)
    initial_updated_at = world.updated_at

    try:
        world.begin_actor_travel("hero", b.location_id, (route.route_id,))
    except ValueError:
        pass
    else:
        raise AssertionError("An unavailable route was accepted for travel")

    position = world.require_actor_position("hero")
    assert position.location_id == a.location_id
    assert not position.is_traveling
    assert world.updated_at == initial_updated_at
