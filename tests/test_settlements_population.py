from app.world.locations import Location
from app.world.population import Population, PopulationGroup
from app.world.regions import Region
from app.world.settlements import Settlement
from app.world.world_state import WorldState


def test_population_is_aggregated_by_race():
    population = Population()
    population.add_group(PopulationGroup.create("Human", 700))
    population.add_group(PopulationGroup.create("Elf", 300))

    assert population.total == 1000
    assert population.get_race_count("human") == 700
    assert population.distribution() == {"Human": 700, "Elf": 300}
    assert population.groups[next(iter(population.groups))].share is not None


def test_settlement_is_attached_to_location_and_region():
    world = WorldState.create("Test")
    location = Location.create("Arken", "village", coordinates={"x": 10, "y": 10})
    region = Region.create("Central Plains", x_min=0, x_max=100, y_min=0, y_max=100)
    world.add_location(location)
    world.add_region(region)

    population = Population()
    population.set_race_count("Human", 850)
    population.set_race_count("Elf", 150)
    settlement = Settlement.create("Arken", location.location_id, "village", population=population, region_id=region.region_id)
    world.add_settlement(settlement)

    assert world.population_at_location(location.location_id) == 1000
    assert world.racial_population_at_location(location.location_id) == {"Human": 850, "Elf": 150}
    assert world.population_in_region(region.region_id) == 1000
    assert location.attributes["settlement_type"] == "village"
    assert location.location_id in region.location_ids


def test_population_and_settlement_survive_world_roundtrip():
    world = WorldState.create("Persistence")
    location = Location.create("Northhold", "city", coordinates={"x": 20, "y": 30})
    world.add_location(location)
    population = Population()
    population.add_group(PopulationGroup.create("Human", 5000))
    population.add_group(PopulationGroup.create("Dwarf", 1200))
    settlement = Settlement.create("Northhold", location.location_id, "city", population=population)
    world.add_settlement(settlement)

    restored = WorldState.from_dict(world.to_dict())
    restored_settlement = restored.settlement_at_location(location.location_id)

    assert restored_settlement is not None
    assert restored_settlement.population.total == 6200
    assert restored_settlement.population.distribution() == {"Human": 5000, "Dwarf": 1200}


def test_location_cannot_be_removed_while_it_has_settlement():
    world = WorldState.create("Integrity")
    location = Location.create("Village", "village", coordinates={"x": 0, "y": 0})
    world.add_location(location)
    world.add_settlement(Settlement.create("Village", location.location_id, "village"))

    try:
        world.remove_location(location.location_id)
    except ValueError:
        return
    raise AssertionError("A location with a settlement was removed")
