"""에리어 규모·파괴력 부여·NPC·지배 테스트."""

import unittest

from cpow_engine.areas import SimulationMode, found_area
from cpow_engine.areas.dominance import effective_imbued_power, is_dominated
from cpow_engine.areas.extent import compute_extent, max_imbue_amount
from cpow_engine.areas.imbue import get_imbued_destruction
from cpow_engine.areas.registry import AreaRegistry
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.physics import create_heat_object
from cpow_engine.tests.area_helpers import create_with_consensus, confirmed_object, ensure_member_collab


def _area():
    area = found_area("aria", "테스트", mode=SimulationMode.CREATION_ADVENTURE)
    area.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
    area.join("bob")
    return area


class TestAreaExtent(unittest.TestCase):
    def test_expand_increases_extent(self) -> None:
        area = _area()
        before = area.area_extent()
        aria = area.power_ledger.get_or_create("aria")
        aria.creation_gauge = 200.0
        aria.destruction_gauge = 200.0
        ensure_member_collab(area, "aria", min_signals=1)
        ensure_member_collab(area, "bob", min_signals=1)
        result = area.expand_area("aria")
        self.assertTrue(result["ok"], result.get("reason"))
        self.assertGreater(area.area_extent(), before)

    def test_small_area_dominated_by_large(self) -> None:
        reg = AreaRegistry()
        small = reg.found("s", "작은 땅", mode=SimulationMode.CREATION_ADVENTURE)
        large = reg.found("l", "큰 땅", mode=SimulationMode.CREATION_ADVENTURE)
        large.extent_bonus = 8.0
        dom = reg.dominance_between(small.area_id, large.area_id)
        self.assertTrue(dom["a_dominated_by_b"])
        self.assertFalse(dom["b_dominated_by_a"])


class TestImbueDestruction(unittest.TestCase):
    def test_imbue_increases_destroy_resistance(self) -> None:
        area = _area()
        obj = create_heat_object("bob", "방어 탑", 40.0)
        create_with_consensus(area, "bob", obj, creation_type="heat")
        confirmed = confirmed_object(area, obj.id)
        assert confirmed is not None

        bob = area.power_ledger.get_or_create("bob")
        bob.destruction_gauge = 120.0
        bob.destruction_gauge_max = 120.0

        imbue = area.imbue_object_destruction("bob", obj.id, 30.0)
        self.assertTrue(imbue["ok"], imbue.get("reason"))
        self.assertGreater(get_imbued_destruction(confirmed), 0.0)

    def test_personal_cap_limits_imbue_in_small_area(self) -> None:
        extent = 12.0
        weak_cap = max_imbue_amount(
            extent=extent,
            destruction_gauge_max=30.0,
            destruction_gauge=20.0,
        )
        strong_cap = max_imbue_amount(
            extent=extent,
            destruction_gauge_max=150.0,
            destruction_gauge=140.0,
        )
        self.assertGreater(strong_cap, weak_cap)
        small_regional = max_imbue_amount(
            extent=2.0,
            destruction_gauge_max=150.0,
            destruction_gauge=140.0,
        )
        self.assertLess(small_regional, strong_cap)


class TestNpcFarming(unittest.TestCase):
    def test_npc_farms_with_allocated_creation(self) -> None:
        area = _area()
        aria = area.power_ledger.get_or_create("aria")
        aria.creation_gauge = 100.0

        spawned = area.spawn_npc("aria", "농부")
        self.assertTrue(spawned["ok"])
        npc_id = spawned["npc"]["npc_id"]

        alloc = area.allocate_npc_creation("aria", npc_id, 25.0)
        self.assertTrue(alloc["ok"], alloc.get("reason"))

        task = area.set_npc_task("aria", npc_id, "farm")
        self.assertTrue(task["ok"])
        self.assertEqual(task["npc"]["task"], "farm")

        results = area.tick_npcs()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["creation_ok"], results[0].get("creation_reason"))
        self.assertIn("object_id", results[0])

        npc = area.npcs[npc_id]
        self.assertLess(npc.creation_gauge, 25.0)


class TestDominanceEffectivePower(unittest.TestCase):
    def test_foreign_extent_suppresses_imbued(self) -> None:
        full = effective_imbued_power(50.0, local_extent=3.0)
        suppressed = effective_imbued_power(
            50.0, local_extent=3.0, foreign_extent=30.0,
        )
        self.assertEqual(full, 50.0)
        self.assertLess(suppressed, full)
        self.assertTrue(is_dominated(3.0, 30.0))


if __name__ == "__main__":
    unittest.main()
