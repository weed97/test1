from mmorpg_sim.engine import SimulatorEngine


def test_world_bootstraps_with_regions_and_factions() -> None:
    engine = SimulatorEngine(player_name="Tester", seed=42)
    assert len(engine.world.regions) >= 6
    assert len(engine.world.factions) >= 4
    assert engine.player.region_key in engine.world.regions


def test_travel_requires_neighbor() -> None:
    engine = SimulatorEngine(player_name="Tester", seed=42)
    engine.player.region_key = "eldenhaven"
    result = engine.travel("moonmere")
    assert "travel from" in result.lower()
    blocked = engine.travel("goldmeadow")
    assert "cannot travel directly" in blocked.lower() or "already in that region" in blocked.lower()


def test_buy_sell_loop_changes_gold_and_inventory() -> None:
    engine = SimulatorEngine(player_name="Tester", seed=42)
    engine.player.region_key = "eldenhaven"
    pre_gold = engine.player.gold
    purchase = engine.buy("herb_bundle", 2)
    assert "Purchased" in purchase
    assert engine.player.inventory.get("herb_bundle", 0) >= 2
    sale = engine.sell("herb_bundle", 1)
    assert "Sold" in sale
    assert engine.player.gold != pre_gold
