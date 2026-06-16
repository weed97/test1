"""적대·중립·동맹 외교 테스트."""

import unittest

from cpow_engine.areas import SimulationMode
from cpow_engine.areas.diplomacy import (
    DiplomaticStance,
    can_cooperative_create,
    can_cross_area_combat,
    observer_can_intervene_cross_area,
)
from cpow_engine.areas.registry import AreaRegistry
from cpow_engine.areas.roles import ContributorRole
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.physics import create_heat_object
from cpow_engine.tests.area_helpers import create_with_consensus, confirmed_object


class TestDiplomacyResolution(unittest.TestCase):
    def test_hostile_overrides_neutral(self) -> None:
        reg = AreaRegistry()
        a = reg.found("fa", "A", mode=SimulationMode.CREATION_ADVENTURE)
        b = reg.found("fb", "B", mode=SimulationMode.CREATION_ADVENTURE)
        reg.set_diplomatic_stance(a.area_id, b.area_id, "hostile", "fa")
        reg.set_diplomatic_stance(b.area_id, a.area_id, "neutral", "fb")
        stance = reg.diplomacy.resolved_stance(a.area_id, b.area_id)
        self.assertEqual(stance, DiplomaticStance.HOSTILE)

    def test_alliance_requires_mutual(self) -> None:
        reg = AreaRegistry()
        a = reg.found("fa", "A", mode=SimulationMode.CREATION_ADVENTURE)
        b = reg.found("fb", "B", mode=SimulationMode.CREATION_ADVENTURE)
        reg.set_diplomatic_stance(a.area_id, b.area_id, "alliance", "fa")
        self.assertEqual(
            reg.diplomacy.resolved_stance(a.area_id, b.area_id),
            DiplomaticStance.NEUTRAL,
        )
        reg.set_diplomatic_stance(b.area_id, a.area_id, "alliance", "fb")
        self.assertEqual(
            reg.diplomacy.resolved_stance(a.area_id, b.area_id),
            DiplomaticStance.ALLIANCE,
        )


class TestHostileCombat(unittest.TestCase):
    def _pair(self):
        reg = AreaRegistry()
        atk = reg.found("atk", "공격", mode=SimulationMode.CREATION_ADVENTURE)
        defn = reg.found("def", "방어", mode=SimulationMode.CREATION_ADVENTURE)
        atk.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
        defn.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
        atk.join("fighter")
        reg.set_diplomatic_stance(atk.area_id, defn.area_id, "hostile", "atk")
        reg.set_diplomatic_stance(defn.area_id, atk.area_id, "hostile", "def")
        return reg, atk, defn

    def test_neutral_blocks_cross_destroy(self) -> None:
        reg = AreaRegistry()
        atk = reg.found("atk", "공격", mode=SimulationMode.CREATION_ADVENTURE)
        defn = reg.found("def", "방어", mode=SimulationMode.CREATION_ADVENTURE)
        atk.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
        defn.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
        atk.join("fighter")
        obj = create_heat_object("def", "타겟", 20.0)
        create_with_consensus(defn, "def", obj, creation_type="heat")
        blocked = reg.cross_area_destroy(atk.area_id, "fighter", defn.area_id, obj.id)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["reason"], "diplomacy_not_hostile")

    def test_hostile_allows_cross_destroy(self) -> None:
        reg, atk, defn = self._pair()
        obj = create_heat_object("def", "타겟", 15.0)
        create_with_consensus(defn, "def", obj, creation_type="heat")
        powers = atk.power_ledger.get_or_create("fighter")
        powers.destruction_gauge = 500.0
        result = reg.cross_area_destroy(atk.area_id, "fighter", defn.area_id, obj.id)
        self.assertTrue(result["ok"], result.get("reason"))
        self.assertNotIn(obj.id, defn.world.state.objects)


class TestAllianceCoop(unittest.TestCase):
    def test_allied_creation_in_partner_area(self) -> None:
        reg = AreaRegistry()
        home = reg.found("h", "동맹A", mode=SimulationMode.CREATION_ADVENTURE)
        ally = reg.found("a", "동맹B", mode=SimulationMode.CREATION_ADVENTURE)
        home.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
        ally.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
        home.join("builder")
        reg.set_diplomatic_stance(home.area_id, ally.area_id, "alliance", "h")
        reg.set_diplomatic_stance(ally.area_id, home.area_id, "alliance", "a")

        obj = create_heat_object("builder", "협력 불", 25.0)
        result = reg.allied_creation(
            home.area_id, ally.area_id, "builder", obj, creation_type="heat",
        )
        self.assertTrue(result.ok, result.reason)
        self.assertIn(result.object_id, ally.world.state.objects)

    def test_neutral_blocks_allied_creation(self) -> None:
        reg = AreaRegistry()
        home = reg.found("h", "A", mode=SimulationMode.CREATION_ADVENTURE)
        other = reg.found("o", "B", mode=SimulationMode.CREATION_ADVENTURE)
        home.join("builder")
        obj = create_heat_object("builder", "불", 20.0)
        result = reg.allied_creation(
            home.area_id, other.area_id, "builder", obj,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "diplomacy_not_allied")


class TestObserverNeutral(unittest.TestCase):
    def test_observer_cannot_cross_intervene(self) -> None:
        self.assertFalse(
            observer_can_intervene_cross_area(
                DiplomaticStance.NEUTRAL, ContributorRole.OBSERVER,
            )
        )
        self.assertTrue(
            observer_can_intervene_cross_area(
                DiplomaticStance.NEUTRAL, ContributorRole.COLLABORATOR,
            )
        )

    def test_observer_blocked_on_cross_destroy(self) -> None:
        reg = AreaRegistry()
        atk = reg.found("atk", "A", mode=SimulationMode.CREATION_ADVENTURE)
        defn = reg.found("def", "B", mode=SimulationMode.CREATION_ADVENTURE)
        atk.join("spy", requested_role=ContributorRole.OBSERVER)
        reg.set_diplomatic_stance(atk.area_id, defn.area_id, "hostile", "atk")
        reg.set_diplomatic_stance(defn.area_id, atk.area_id, "hostile", "def")
        obj = create_heat_object("def", "x", 10.0)
        defn.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
        create_with_consensus(defn, "def", obj, creation_type="heat")
        result = reg.cross_area_destroy(atk.area_id, "spy", defn.area_id, obj.id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "observer_cannot_intervene")


class TestPermissionHelpers(unittest.TestCase):
    def test_stance_permissions(self) -> None:
        self.assertTrue(can_cross_area_combat(DiplomaticStance.HOSTILE))
        self.assertFalse(can_cross_area_combat(DiplomaticStance.NEUTRAL))
        self.assertTrue(
            can_cooperative_create(DiplomaticStance.ALLIANCE, ContributorRole.COLLABORATOR)
        )
        self.assertFalse(
            can_cooperative_create(DiplomaticStance.NEUTRAL, ContributorRole.COLLABORATOR)
        )


if __name__ == "__main__":
    unittest.main()
