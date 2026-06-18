"""공성·수성 — 연속 압력 교전 테스트."""

import unittest

from cpow_engine.areas import SimulationMode
from cpow_engine.areas.registry import AreaRegistry
from cpow_engine.areas.siege import (
    area_fortification_strength,
    emergent_flow,
    object_fortification_contribution,
    siege_cross_scale_modifier,
)
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.models import PropertyDef
from cpow_engine.physics import create_heat_object
from cpow_engine.tests.area_helpers import create_with_consensus
from cpow_engine.areas.durability import is_confirmed


class TestSiegePressure(unittest.TestCase):
    def test_fortification_from_properties(self) -> None:
        obj = create_heat_object("u1", "wall", 50.0)
        obj.properties.append(PropertyDef("fortification_rating", 80.0, "points"))
        obj.properties.append(PropertyDef("is_confirmed", 1.0, "flag"))
        self.assertGreater(object_fortification_contribution(obj), 50.0)

    def test_cross_modifier_eases_under_sustained_assault(self) -> None:
        easy = siege_cross_scale_modifier(assault=30.0, fortification=10.0)
        hard = siege_cross_scale_modifier(assault=0.0, fortification=40.0)
        self.assertLess(easy, hard)

    def test_emergent_flow_not_fixed_phases(self) -> None:
        quiet = emergent_flow(0.0, 5.0, 1.0)
        siege = emergent_flow(25.0, 10.0, 0.8)
        self.assertNotEqual(quiet["flow"], siege["flow"])
        self.assertIn("label", siege)


class TestSiegeCombat(unittest.TestCase):
    def _hostile_pair(self):
        reg = AreaRegistry()
        atk = reg.found("atk", "공격국", mode=SimulationMode.CREATION_ADVENTURE)
        defn = reg.found("def", "수성국", mode=SimulationMode.CREATION_ADVENTURE)
        for a in (atk, defn):
            a.world.policy = CollabPolicy(
                pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0,
            )
        atk.join("raider")
        defn.join("guardian")
        reg.set_diplomatic_stance(atk.area_id, defn.area_id, "hostile", "atk")
        reg.set_diplomatic_stance(defn.area_id, atk.area_id, "hostile", "def")
        return reg, atk, defn

    def test_hostile_enables_siege_context_without_start_button(self) -> None:
        reg, atk, defn = self._hostile_pair()
        status = reg.siege_between(atk.area_id, defn.area_id)
        self.assertTrue(status["ok"])
        self.assertEqual(status["siege"]["assault_momentum"], 0.0)

    def test_cross_destroy_builds_assault_momentum(self) -> None:
        reg, atk, defn = self._hostile_pair()
        target = create_heat_object("def", "요새", 20.0)
        create_with_consensus(defn, "def", target, creation_type="heat")
        atk.power_ledger.get_or_create("raider").destruction_gauge = 600.0
        result = reg.cross_area_destroy(atk.area_id, "raider", defn.area_id, target.id)
        self.assertTrue(result["ok"], result.get("reason"))
        self.assertIn("siege", result)
        self.assertGreater(result["siege"]["assault_momentum"], 0.0)

    def test_fortification_slows_assault_over_ticks(self) -> None:
        reg, atk, defn = self._hostile_pair()
        wall = create_heat_object("def", "성벽", 30.0)
        wall.properties.append(PropertyDef("fortification_rating", 120.0))
        create_with_consensus(defn, "def", wall, creation_type="heat")
        reg.siege.on_assault(atk.area_id, defn.area_id, "raider", durability_destroyed=50.0)
        before = reg.siege.get(atk.area_id, defn.area_id)
        assert before is not None
        m0 = before.assault_momentum
        for _ in range(5):
            reg.tick_sieges()
        after = reg.siege.get(atk.area_id, defn.area_id)
        assert after is not None
        self.assertLess(after.assault_momentum, m0)

    def test_repulse_reduces_momentum(self) -> None:
        reg, atk, defn = self._hostile_pair()
        reg.siege.on_assault(atk.area_id, defn.area_id, "raider", durability_destroyed=40.0)
        defn.power_ledger.get_or_create("guardian").destruction_gauge = 200.0
        out = reg.repulse_siege(defn.area_id, atk.area_id, "guardian", power_spend=30.0)
        self.assertTrue(out["ok"])
        contest = reg.siege.get(atk.area_id, defn.area_id)
        assert contest is not None
        self.assertLess(contest.assault_momentum, 40.0 * 0.35)

    def test_second_destroy_easier_after_momentum(self) -> None:
        reg, atk, defn = self._hostile_pair()
        t1 = create_heat_object("def", "외곽", 18.0)
        t2 = create_heat_object("def", "내곽", 18.0)
        create_with_consensus(defn, "def", t1, creation_type="heat")
        create_with_consensus(defn, "def", t2, creation_type="heat")
        powers = atk.power_ledger.get_or_create("raider")
        powers.destruction_gauge = 800.0

        mod_before = reg._siege_cross_multiplier(atk.area_id, defn.area_id, defn)
        reg.cross_area_destroy(atk.area_id, "raider", defn.area_id, t1.id)
        mod_after = reg._siege_cross_multiplier(atk.area_id, defn.area_id, defn)
        self.assertLess(mod_after, mod_before)

    def test_active_sieges_list(self) -> None:
        reg, atk, defn = self._hostile_pair()
        reg.siege.on_assault(atk.area_id, defn.area_id, "raider", durability_destroyed=10.0)
        active = reg.active_sieges(defn.area_id)
        self.assertTrue(active["ok"])
        self.assertGreaterEqual(active["count"], 1)


if __name__ == "__main__":
    unittest.main()
