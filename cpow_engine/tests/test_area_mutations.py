"""Area object mutation tests."""

import unittest

from cpow_engine.areas import SimulationMode, found_area
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.physics import create_heat_object
from cpow_engine.tests.area_helpers import create_with_consensus


def _instant_area(founder: str = "aria"):
    area = found_area(
        founder,
        "변형 테스트",
        mode=SimulationMode.CREATION_ADVENTURE,
    )
    area.world.policy = CollabPolicy(
        pulse_interval_sec=0.0,
        min_creator_cooldown_sec=0.0,
    )
    return area


class TestObjectMutations(unittest.TestCase):
    def test_collaborator_grows_object(self) -> None:
        area = _instant_area()
        area.join("bob")
        obj = create_heat_object("bob", "협동 불", 70.0)
        create_with_consensus(area, "bob", obj, creation_type="heat")
        oid = obj.id
        before = area.world.state.objects[oid].get_property("heat_intensity")
        assert before is not None

        result = area.submit_mutation("bob", oid, "grow", factor=1.2)
        self.assertTrue(result.ok, result.reason)
        assert result.new_value is not None
        self.assertGreater(result.new_value, before.value)

    def test_collaborator_shrinks_object(self) -> None:
        area = _instant_area()
        area.join("bob")
        oid = next(iter(area.world.state.objects))
        before = area.world.state.objects[oid].get_property("heat_intensity")
        assert before is not None

        result = area.submit_mutation("bob", oid, "shrink", factor=0.8)
        self.assertTrue(result.ok, result.reason)
        assert result.new_value is not None
        self.assertLess(result.new_value, before.value)

    def test_collaborator_destroys_object(self) -> None:
        area = _instant_area()
        area.join("bob")
        obj = create_heat_object("bob", "임시", 50.0)
        create_with_consensus(area, "bob", obj, creation_type="heat")
        oid = obj.id
        self.assertIn(oid, area.world.state.objects)

        result = area.submit_mutation("bob", oid, "destroy")
        self.assertTrue(result.ok, result.reason)
        self.assertNotIn(oid, area.world.state.objects)

    def test_cannot_destroy_founding_core(self) -> None:
        area = _instant_area()
        area.join("bob")
        seed_id = next(iter(area.world.state.objects))
        result = area.submit_mutation("bob", seed_id, "destroy")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "cannot_destroy_founding_core")

    def test_non_member_cannot_mutate(self) -> None:
        area = _instant_area()
        oid = next(iter(area.world.state.objects))
        result = area.submit_mutation("stranger", oid, "grow")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "not_a_member")

    def test_co_creator_tracked_on_mutation(self) -> None:
        area = _instant_area()
        area.join("bob")
        oid = next(iter(area.world.state.objects))
        area.submit_mutation("bob", oid, "modify", delta=5.0)
        obj = area.world.state.objects[oid]
        self.assertIn("bob", obj.creator_id)

    def test_rename_object(self) -> None:
        area = _instant_area()
        area.join("bob")
        oid = next(iter(area.world.state.objects))
        result = area.submit_mutation(
            "bob", oid, "rename", text_value="공동의 심장",
        )
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(area.world.state.objects[oid].label, "공동의 심장")


if __name__ == "__main__":
    unittest.main()
