"""월드 인벤토리·드롭·AOI."""

from __future__ import annotations

import unittest

from cpow_engine.world.inventory import ActorInventory, InventoryLedger
from cpow_engine.world.drops import DropRegistry
from cpow_engine.world.aoi import in_aoi
from cpow_engine.world.service import WorldService
from cpow_engine.world.ores import ORE_CATALOG


class TestInventory(unittest.TestCase):
    def test_stack_merge(self) -> None:
        inv = ActorInventory(actor_id="a")
        t1 = inv.add("coal", 2.5)
        t2 = inv.add("coal", 1.0)
        self.assertAlmostEqual(t1, 2.5)
        self.assertAlmostEqual(t2, 3.5)

    def test_take(self) -> None:
        inv = ActorInventory(actor_id="a")
        inv.add("iron_ore", 5.0)
        ok, left = inv.take("iron_ore", 2.0)
        self.assertTrue(ok)
        self.assertAlmostEqual(left, 3.0)


class TestDrops(unittest.TestCase):
    def test_in_radius(self) -> None:
        reg = DropRegistry()
        reg.spawn("coal", 1.0, 10.0, 10.0, "miner")
        reg.spawn("coal", 1.0, 200.0, 200.0, "miner")
        near = reg.in_radius(10.0, 10.0, 32.0)
        self.assertEqual(len(near), 1)


class TestAoi(unittest.TestCase):
    def test_in_aoi(self) -> None:
        self.assertTrue(in_aoi(0, 0, 50, 0, 64))
        self.assertFalse(in_aoi(0, 0, 200, 0, 64))


class TestMineInventory(unittest.TestCase):
    def test_mine_deposits_inventory_not_area_object(self) -> None:
        svc = WorldService()
        area_id = "inv_test_area"
        out = svc.mine(
            area_id,
            {
                "actor_id": "miner1",
                "x": 12.0,
                "z": 8.0,
                "depth_y": 40,
                "tool_type": "pickaxe",
                "tool_tier": 2,
                "ore_id": "coal",
                "deposit_mode": "inventory",
            },
        )
        self.assertTrue(out.get("ok"), out)
        self.assertIn("inventory", out)
        self.assertIn("inventory_delta", out)
        self.assertIn("world_drop", out)
        self.assertNotIn("creation", out)
        inv = svc.get_inventory(area_id, "miner1")
        self.assertGreater(inv["inventory"]["stacks"].get("coal", 0), 0)

    def test_pickup_drop(self) -> None:
        svc = WorldService()
        area_id = "pickup_area"
        mined = svc.mine(
            area_id,
            {
                "actor_id": "p1",
                "x": 1.0,
                "z": 1.0,
                "depth_y": 40,
                "tool_type": "pickaxe",
                "tool_tier": 2,
                "ore_id": "coal",
                "spawn_world_drop": True,
            },
        )
        drop_id = mined["world_drop"]["drop_id"]
        runtime = svc.runtime_for(area_id)
        self.assertEqual(runtime.drops.count(), 1)
        picked = svc.pickup_drop(area_id, {"actor_id": "p1", "drop_id": drop_id})
        self.assertTrue(picked.get("ok"), picked)
        self.assertEqual(runtime.drops.count(), 0)


if __name__ == "__main__":
    unittest.main()
