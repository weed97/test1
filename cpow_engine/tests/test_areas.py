"""Area mode tests — creation, adventure, regional growth."""

import unittest

from cpow_engine.areas import (
    AreaRegistry,
    ContributorRole,
    SimulationMode,
    found_area,
)
from cpow_engine.physics import create_heat_object, create_material_object


class TestAreaFounding(unittest.TestCase):
    def test_founder_creates_area_with_seed(self) -> None:
        area = found_area("aria", "불의 정원", mode=SimulationMode.CREATION_ADVENTURE)
        self.assertTrue(area.area_id.startswith("area_"))
        self.assertEqual(area.founder_id, "aria")
        self.assertEqual(area.role_of("aria"), ContributorRole.FOUNDER)
        self.assertGreaterEqual(len(area.world.state.objects), 1)
        self.assertIn("energy_exchange", area.economy.systems_unlocked)

    def test_join_assigns_role_by_mode(self) -> None:
        area = found_area("founder", "작업장", mode=SimulationMode.CREATION_ADVENTURE)
        role = area.join("bob")
        self.assertEqual(role, ContributorRole.COLLABORATOR)

        adv_area = found_area("f2", "황야", mode=SimulationMode.ADVENTURE)
        adv_role = adv_area.join("carol")
        self.assertEqual(adv_role, ContributorRole.ADVENTURER)


class TestCreationMode(unittest.TestCase):
    def test_collaborator_can_create_in_creation_adventure(self) -> None:
        area = found_area(
            "aria",
            "협동 정원",
            mode=SimulationMode.CREATION_ADVENTURE,
        )
        area.join("bob")
        obj = create_material_object("bob", "철괴", "iron")
        result = area.submit_creation("bob", obj, creation_type="material")
        self.assertTrue(result.ok, result.reason)
        area.world.advance_pulse(force=True)

    def test_adventurer_blocked_from_direct_create(self) -> None:
        area = found_area("aria", "정원", mode=SimulationMode.ADVENTURE)
        area.join("carol")
        obj = create_heat_object("carol", "불", 70.0)
        result = area.submit_creation("carol", obj, creation_type="heat")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "mode_blocks_creation")


class TestAdventureMode(unittest.TestCase):
    def test_explore_and_interact(self) -> None:
        area = found_area("aria", "탐험지", mode=SimulationMode.CREATION_ADVENTURE)
        area.join("bob", requested_role=ContributorRole.ADVENTURER)
        explore = area.submit_adventure("bob", "explore")
        self.assertTrue(explore.ok)

        seed_id = next(iter(area.world.state.objects))
        interact = area.submit_adventure(
            "bob", "interact", target_object_id=seed_id,
        )
        self.assertTrue(interact.ok)
        self.assertGreater(interact.energy_delta, 0.0)

    def test_adventurer_contribute_small_creation(self) -> None:
        area = found_area(
            "aria",
            "정착지",
            mode=SimulationMode.CREATION_ADVENTURE,
        )
        area.join("carol", requested_role=ContributorRole.ADVENTURER)
        result = area.submit_adventure("carol", "contribute", label="불씨")
        self.assertTrue(result.ok, result.reason)


class TestRegionalGrowth(unittest.TestCase):
    def test_civilization_grows_with_activity(self) -> None:
        area = found_area(
            "aria",
            "성장 테스트",
            mode=SimulationMode.CREATION_ADVENTURE,
        )
        start_level = area.economy.civilization_level
        area.join("bob")
        area.join("carol")
        for i, cid in enumerate(["bob", "carol", "aria"]):
            obj = create_heat_object(cid, f"열{i}", 65.0 + i * 5)
            area.submit_creation(cid, obj, creation_type="heat")
        area.world.advance_pulse(force=True)
        self.assertGreaterEqual(area.economy.civilization_level, start_level)
        pub = area.to_public_dict()
        self.assertIn("economy", pub)
        self.assertIn("civilization_label", pub["economy"])


class TestAreaRegistry(unittest.TestCase):
    def test_registry_found_and_join(self) -> None:
        reg = AreaRegistry()
        area = reg.found("aria", "레지스트리 테스트")
        joined = reg.join(area.area_id, "bob")
        self.assertEqual(joined.role_of("bob"), ContributorRole.COLLABORATOR)
        self.assertEqual(len(reg.list_areas()), 1)


if __name__ == "__main__":
    unittest.main()
