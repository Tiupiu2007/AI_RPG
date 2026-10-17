from app.world.biomes import BiomeDefinition, BiomeMap, BiomeRegion
from app.world.locations import Location
from app.world.demography import DemographicState
from app.world.population import Population, PopulationGroup
from app.world.regions import Region, RacialTerritory
from app.world.settlements import Settlement
from app.world.economy import Market, ResourceNode
from app.world.trade import ProductionRule, TradeRoute
from app.world.world_state import WorldState


def test_over_capacity_demography_applies_population_penalty():
    demography = DemographicState(
        settlement_id="overcrowded",
        population=2000,
        carrying_capacity=1000,
        birth_rate=0.0,
        death_rate=0.0,
        migration_rate=0.0,
    )

    result = demography.simulate_year(
        health=100,
        happiness=100,
        prosperity=100,
        security=100,
    )

    assert result == 1900
    assert demography.population == 1900


def test_set_race_count_rejects_non_integer_values_without_mutation():
    population = Population()
    population.set_race_count("Human", 700)
    before = population.to_dict()

    for invalid_count in (1.5, True, -1):
        try:
            population.set_race_count("Human", invalid_count)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid population count accepted: {invalid_count!r}")
        assert population.to_dict() == before


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


def test_yearly_demography_keeps_population_groups_consistent():
    population = Population()
    population.add_group(PopulationGroup.create("Human", 700))
    population.add_group(PopulationGroup.create("Elf", 300))
    settlement = Settlement.create("Arken", "loc-1", "village", population=population)
    settlement.apply_demographic_year(health=100, happiness=100, prosperity=100, security=100)
    assert sum(settlement.population.distribution().values()) == settlement.population.total
    assert settlement.population.get_race_count("Human") == 704
    assert settlement.population.get_race_count("Elf") == 301
    assert abs(sum(group.share for group in settlement.population.groups.values()) - 1.0) < 1e-9
    assert settlement.demography.population == settlement.population.total


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


def test_location_cannot_be_removed_while_trade_route_references_it():
    world = WorldState.create("Trade integrity")
    origin = Location.create("Origin", "town")
    destination = Location.create("Destination", "town")
    world.add_location(origin)
    world.add_location(destination)
    route = TradeRoute.create(origin.location_id, destination.location_id)
    world.add_trade_route(route)

    try:
        world.remove_location(origin.location_id)
    except ValueError as error:
        assert "commerciale" in str(error)
    else:
        raise AssertionError("A location referenced by a trade route was removed")

    assert world.get_location(origin.location_id) is origin
    assert route.route_id in world.trade.routes



def test_location_cannot_be_removed_while_economy_references_it():
    world = WorldState.create("Economy integrity")
    location = Location.create("Mine", "town")
    world.add_location(location)
    resource = ResourceNode.create("iron", 100, location_id=location.location_id)
    world.economy.add_resource(resource)

    try:
        world.remove_location(location.location_id)
    except ValueError as error:
        assert "risorse" in str(error)
    else:
        raise AssertionError("A location referenced by a resource was removed")

    assert world.get_location(location.location_id) is location
    world.economy.resources.pop(resource.resource_id)

    market = Market.create(location.location_id)
    world.economy.add_market(market)
    try:
        world.remove_location(location.location_id)
    except ValueError as error:
        assert "mercato" in str(error)
    else:
        raise AssertionError("A location hosting a market was removed")

    assert world.get_location(location.location_id) is location


def test_production_rule_without_positive_inputs_cannot_generate_free_goods():
    rule = ProductionRule.create("Free iron", {"ore": 0}, {"iron": 1})

    assert rule.max_cycles({"ore": 100}) == 0
    try:
        rule.apply({"ore": 100}, cycles=1)
    except ValueError:
        pass
    else:
        raise AssertionError("A production rule generated goods without consuming resources")


def test_production_rejects_non_finite_quantities_and_invalid_cycle_counts():
    for invalid in (float("nan"), float("inf"), float("-inf")):
        try:
            ProductionRule.create("Invalid", {"ore": invalid}, {"iron": 1})
        except ValueError:
            pass
        else:
            raise AssertionError(f"Non-finite production input accepted: {invalid!r}")

    rule = ProductionRule.create("Smelt", {"ore": 2}, {"iron": 1})
    for cycles in (-1, 1.5, True):
        try:
            rule.apply({"ore": 10}, cycles=cycles)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid cycle count accepted: {cycles!r}")


def test_trade_route_rejects_non_finite_or_negative_values():
    for invalid in (float("nan"), float("inf"), float("-inf"), -1):
        try:
            TradeRoute.create("origin", "destination", goods={"iron": invalid})
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid goods quantity accepted: {invalid!r}")

    for field, value in (("travel_hours", float("inf")), ("tariff", float("nan"))):
        try:
            TradeRoute.create("origin", "destination", **{field: value})
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid {field} accepted: {value!r}")


def test_resource_nodes_reject_non_finite_values_without_mutation():
    for invalid in (float("nan"), float("inf"), float("-inf")):
        try:
            ResourceNode.create("iron", invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid resource amount accepted: {invalid!r}")

    resource = ResourceNode.create("iron", 10, regeneration_rate=2)
    for operation in (
        lambda: resource.advance(float("nan")),
        lambda: resource.consume(float("inf")),
    ):
        before = resource.amount
        try:
            operation()
        except ValueError:
            pass
        else:
            raise AssertionError("A non-finite resource operation was accepted")
        assert resource.amount == before


def test_market_rejects_non_finite_prices_supply_and_demand():
    market = Market.create("loc-1")
    for operation in (
        lambda: market.set_price("iron", float("nan")),
        lambda: market.set_supply("iron", float("inf")),
        lambda: market.set_demand("iron", float("-inf")),
        lambda: market.update_price_from_supply_demand("iron", base_price=1, sensitivity=float("nan")),
    ):
        try:
            operation()
        except ValueError:
            pass
        else:
            raise AssertionError("A non-finite market value was accepted")

    assert market.prices == {}
    assert market.supply == {}
    assert market.demand == {}


def test_regions_reject_non_finite_bounds():
    for invalid in (float("nan"), float("inf"), float("-inf")):
        try:
            Region.create("Broken", x_min=0, x_max=invalid, y_min=0, y_max=10)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Non-finite region bound accepted: {invalid!r}")

    region = Region.create("Valid", x_min=0, x_max=10, y_min=0, y_max=10)
    for coordinates in ({"x": float("nan"), "y": 1}, {"x": 1, "y": float("inf")}):
        try:
            region.contains(coordinates)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Non-finite coordinates accepted: {coordinates!r}")


def test_racial_territories_reject_non_finite_values():
    for invalid in (float("nan"), float("inf"), float("-inf")):
        for kwargs in (
            {"concentration": invalid, "x_min": 0, "x_max": 10, "y_min": 0, "y_max": 10},
            {"concentration": 0.5, "x_min": 0, "x_max": invalid, "y_min": 0, "y_max": 10},
        ):
            try:
                RacialTerritory.create("Elf", "Woodlands", **kwargs)
            except ValueError:
                pass
            else:
                raise AssertionError(f"Non-finite territory value accepted: {kwargs!r}")


def test_economy_overflow_is_rejected_without_mutation():
    resource = ResourceNode.create("iron", 1e308, regeneration_rate=1e308)
    before = resource.amount
    try:
        resource.advance(2)
    except ValueError:
        pass
    else:
        raise AssertionError("Resource regeneration overflow was accepted")
    assert resource.amount == before

    market = Market.create("loc-1")
    market.set_supply("iron", 1e-308)
    market.set_demand("iron", 1e308)
    try:
        market.update_price_from_supply_demand("iron", base_price=1e308, sensitivity=1e308)
    except ValueError:
        pass
    else:
        raise AssertionError("Overflowing market price was accepted")
    assert market.prices == {}


def test_market_loading_rejects_non_finite_saved_prices():
    data = {
        "market_id": "market-1",
        "location_id": "loc-1",
        "prices": {"iron": float("nan")},
        "supply": {},
        "demand": {},
    }
    try:
        Market.from_dict(data)
    except ValueError:
        pass
    else:
        raise AssertionError("A market with a non-finite saved price was loaded")


def test_world_loading_rejects_missing_region_references():
    world = WorldState.create("Region integrity")
    region = Region.create("Parent", x_min=0, x_max=10, y_min=0, y_max=10)
    world.add_region(region)
    territory = RacialTerritory.create("Elf", "Forest", concentration=0.8, x_min=0, x_max=5, y_min=0, y_max=5, region_id=region.region_id)
    world.add_racial_territory(territory)
    data = world.to_dict()
    data["regions"]["regions"][region.region_id]["parent_region_id"] = "missing-parent"

    try:
        WorldState.from_dict(data)
    except ValueError as error:
        assert "genitore" in str(error)
    else:
        raise AssertionError("A region with a missing parent was loaded")

    data = world.to_dict()
    data["regions"]["racial_territories"][territory.territory_id]["region_id"] = "missing-region"
    try:
        WorldState.from_dict(data)
    except ValueError as error:
        assert "territorio razziale" in str(error).lower()
    else:
        raise AssertionError("A racial territory with a missing region was loaded")


def test_world_loading_rejects_region_cycles_and_missing_biomes():
    world = WorldState.create("Region graph integrity")
    first = Region.create("First", x_min=0, x_max=10, y_min=0, y_max=10)
    second = Region.create("Second", x_min=10, x_max=20, y_min=0, y_max=10, parent_region_id=first.region_id)
    world.add_region(first)
    world.add_region(second)

    data = world.to_dict()
    data["regions"]["regions"][first.region_id]["parent_region_id"] = second.region_id
    try:
        WorldState.from_dict(data)
    except ValueError as error:
        assert "ciclo" in str(error).lower()
    else:
        raise AssertionError("A cyclic region hierarchy was loaded")

    data = world.to_dict()
    data["regions"]["regions"][first.region_id]["biome_ids"] = ["missing-biome"]
    try:
        WorldState.from_dict(data)
    except ValueError as error:
        assert "bioma inesistente" in str(error).lower()
    else:
        raise AssertionError("A region referencing an unknown biome was loaded")

def test_adding_region_rejects_missing_parent_and_biome_without_mutation():
    world = WorldState.create("Region validation")
    missing_parent = Region.create(
        "Orphan", x_min=0, x_max=10, y_min=0, y_max=10,
        parent_region_id="missing-parent",
    )
    try:
        world.add_region(missing_parent)
    except KeyError as error:
        assert "genitore" in str(error).lower()
    else:
        raise AssertionError("A region with a missing parent was added")
    assert missing_parent.region_id not in world.regions.regions

    missing_biome = Region.create(
        "Unknown biome", x_min=0, x_max=10, y_min=0, y_max=10,
        biome_ids=["missing-biome"],
    )
    try:
        world.add_region(missing_biome)
    except KeyError as error:
        assert "biomi esistenti" in str(error).lower()
    else:
        raise AssertionError("A region with a missing biome was added")
    assert missing_biome.region_id not in world.regions.regions

def test_biome_regions_reject_non_finite_geometry_and_invalid_identifiers():
    invalid_regions = [
        {"region_id": "r1", "biome_id": "forest", "center": {"x": float("nan"), "y": 0}, "radius": 2},
        {"region_id": "r2", "biome_id": "forest", "center": {"x": 0, "y": 0}, "radius": float("inf")},
        {"region_id": "r3", "biome_id": "forest", "center": {"x": 0, "y": 0}, "radius": 2, "transition_radius": float("nan")},
        {"region_id": "", "biome_id": "forest", "center": {"x": 0, "y": 0}, "radius": 2},
    ]
    for data in invalid_regions:
        try:
            BiomeRegion(**data)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"Invalid biome region was accepted: {data}")

    try:
        BiomeMap().add_definition(BiomeDefinition(biome_id="", name="Forest"))
    except ValueError:
        pass
    else:
        raise AssertionError("A biome definition with an empty ID was accepted")

def test_production_rejects_invalid_stock_and_overflow_without_mutation():
    rule = ProductionRule.create("Smelt", {"ore": 1}, {"ingot": 2})
    for stock in ({"ore": float("nan")}, {"ore": float("inf")}, {"ore": -1}, {"ore": "invalid"}):
        try:
            rule.max_cycles(stock)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"Invalid stock was accepted: {stock}")

    stock = {"ore": 1, "ingot": float("1e308")}
    original = dict(stock)
    try:
        ProductionRule.create("Overflow", {"ore": 1}, {"ingot": 1e308}).apply(stock, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("Production overflow was accepted")
    assert stock == original

