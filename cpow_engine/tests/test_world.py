"""월드 — 바이옴·채굴·모듈 건축."""

from __future__ import annotations

import unittest

from cpow_engine.world.biomes import BiomeId, ZoneClass
from cpow_engine.world.building import validate_blueprint_placement
from cpow_engine.world.grid import biome_at, cell_from_world, ore_at_position
from cpow_engine.world.mining import MiningProfile, attempt_mine
from cpow_engine.world.ores import ORE_CATALOG
from cpow_engine.world.service import WorldService
from cpow_engine.world.tools import resolve_tool


class TestWorldGrid(unittest.TestCase):
    def test_biome_deterministic(self) -> None:
        a = biome_at("seed1", 0, 0).biome_id
        b = biome_at("seed1", 0, 0).biome_id
        c = biome_at("seed1", 1, 0).biome_id
        self.assertEqual(a, b)
        self.assertIsInstance(a, BiomeId)

    def test_cell_from_world(self) -> None:
        self.assertEqual(cell_from_world(128.0, -32.0, 64), (2, -1))


class TestMining(unittest.TestCase):
    def test_pickaxe_cannot_mine_diamond_well(self) -> None:
        ore = ORE_CATALOG["diamond_ore"]
        tool = resolve_tool("pickaxe", 3)
        assert tool is not None
        profile = MiningProfile(user_id="miner")
        result = attempt_mine(
            actor_id="miner",
            ore=ore,
            tool=tool,
            profile=profile,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "requires_drill")

    def test_drill_mines_diamond(self) -> None:
        ore = ORE_CATALOG["diamond_ore"]
        tool = resolve_tool("drill", 4)
        assert tool is not None
        profile = MiningProfile(user_id="miner")
        result = attempt_mine(
            actor_id="miner",
            ore=ore,
            tool=tool,
            profile=profile,
        )
        self.assertTrue(result.ok, result.reason)
        self.assertGreater(result.amount, 0.0)

    def test_black_mithril_shard_boss_only(self) -> None:
        ore = ORE_CATALOG["black_mithril_shard"]
        tool = resolve_tool("drill", 6)
        assert tool is not None
        result = attempt_mine(
            actor_id="x",
            ore=ore,
            tool=tool,
            profile=MiningProfile(user_id="x"),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "boss_drop_only")

    def test_black_mithril_ore_needs_stabilizer(self) -> None:
        ore = ORE_CATALOG["black_mithril_ore"]
        tool = resolve_tool("drill", 6)
        assert tool is not None
        result = attempt_mine(
            actor_id="x",
            ore=ore,
            tool=tool,
            profile=MiningProfile(user_id="x"),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "missing_consumable")

    def test_mining_tier_grows(self) -> None:
        profile = MiningProfile(user_id="m")
        tool = resolve_tool("pickaxe", 1)
        assert tool is not None
        for _ in range(30):
            attempt_mine(
                actor_id="m",
                ore=ORE_CATALOG["coal"],
                tool=tool,
                profile=profile,
            )
        self.assertGreater(profile.tier, 1)


class TestBuilding(unittest.TestCase):
    def test_settlement_blocked_in_volcano(self) -> None:
        result = validate_blueprint_placement(
            biome_id="volcano",
            blueprint_id="smelter_lv1",
            placed_modules={
                "foundation_2x2": 1,
                "wall_t1": 8,
                "furnace_box": 1,
                "chimney_stack": 1,
            },
            placed_materials={"iron_plate": 12, "stone_brick": 16},
            civilization_level=2,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "settlement_only_in_safe_zone")

    def test_outpost_allowed_in_desert(self) -> None:
        result = validate_blueprint_placement(
            biome_id="desert",
            blueprint_id="camp_kit",
            placed_modules={
                "foundation_1x1": 1,
                "wall_t1": 4,
                "heater_core": 1,
            },
            placed_materials={"wood_plank": 8, "stone_brick": 4},
        )
        self.assertTrue(result.ok, result.reason)


class TestWorldService(unittest.TestCase):
    def test_cell_has_hazard_audio(self) -> None:
        svc = WorldService()
        out = svc.inspect_cell("area_test", x=100.0, z=50.0, advance_tick=True)
        self.assertTrue(out.get("ok"))
        self.assertIn("hazard", out)
        self.assertIn("audio_cue", out["hazard"]["phase"])

    def test_boss_loot_black_mithril_shard(self) -> None:
        svc = WorldService()
        out = svc.boss_loot("area_boss", {"actor_id": "hero", "amount": 1.0})
        self.assertTrue(out.get("ok"))
        self.assertEqual(
            out["resource"]["properties"][0]["unit"],
            "black_mithril_shard",
        )

    def test_mine_at_position(self) -> None:
        svc = WorldService()
        runtime = svc.runtime_for("mine_area")
        biome = biome_at(runtime.world_seed, 0, 0)
        ore = ore_at_position(runtime.world_seed, biome.biome_id, 40, 0, 0)
        if ore is None:
            ore = ORE_CATALOG["coal"]
        out = svc.mine(
            "mine_area",
            {
                "actor_id": "digger",
                "x": 10.0,
                "z": 10.0,
                "depth_y": 40,
                "tool_type": "pickaxe",
                "tool_tier": 2,
                "ore_id": ore.ore_id,
            },
        )
        self.assertTrue(out.get("ok"), out)
        self.assertIn("hazard_audio", out)


if __name__ == "__main__":
    unittest.main()
