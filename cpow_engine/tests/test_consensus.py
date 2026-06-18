"""Law validator and consensus tests."""

import unittest

from cpow_engine.areas import SimulationMode, found_area
from cpow_engine.areas.consensus import ConsensusPolicy
from cpow_engine.areas.law_validator import validate_creation
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.models import CreativeObject, PropertyDef
from cpow_engine.physics import create_heat_object, create_material_object


def _area_with_members():
    area = found_area("aria", "합의 테스트", mode=SimulationMode.CREATION_ADVENTURE)
    area.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
    area.consensus = __import__(
        "cpow_engine.areas.consensus", fromlist=["ConsensusGate"]
    ).ConsensusGate(ConsensusPolicy(min_votes=2))
    area.join("bob")
    return area


class TestLawValidator(unittest.TestCase):
    def test_rejects_forbidden_property(self) -> None:
        area = found_area("aria", "법칙 테스트")
        obj = create_heat_object("aria", "해킹", 50.0)
        obj.properties.append(PropertyDef(name="god_mode", value=1.0))
        result = validate_creation(
            obj, area.laws, creation_type="heat",
            role_max_heat=500.0, state=area.world.state,
        )
        self.assertFalse(result.ok)
        self.assertIn("forbidden_property", result.codes)

    def test_rejects_heat_above_law_limit(self) -> None:
        area = found_area("aria", "법칙 테스트")
        obj = create_heat_object("aria", "폭발", 9999.0)
        result = validate_creation(
            obj, area.laws, creation_type="heat",
            role_max_heat=500.0, state=area.world.state,
        )
        self.assertFalse(result.ok)
        self.assertIn("heat_exceeds_law_limit", result.codes)

    def test_rejects_non_finite(self) -> None:
        area = found_area("aria", "법칙 테스트")
        obj = create_heat_object("aria", "나노", 50.0)
        heat = obj.get_property("heat_intensity")
        assert heat is not None
        heat.value = float("inf")
        result = validate_creation(
            obj, area.laws, creation_type="heat",
            role_max_heat=500.0, state=area.world.state,
        )
        self.assertFalse(result.ok)
        self.assertIn("non_finite_value", result.codes)


class TestCreationConsensus(unittest.TestCase):
    def test_new_object_requires_consensus(self) -> None:
        area = _area_with_members()
        obj = create_heat_object("bob", "협동 불", 70.0)
        result = area.submit_creation("bob", obj, creation_type="heat")
        self.assertTrue(result.consensus_pending)
        self.assertEqual(result.reason, "consensus_pending")
        self.assertNotIn(obj.id, area.world.state.objects)

    def test_approval_commits_object(self) -> None:
        area = _area_with_members()
        obj = create_heat_object("bob", "협동 불", 70.0)
        proposed = area.submit_creation("bob", obj, creation_type="heat")
        vote = area.vote_on_creation("aria", proposed.proposal_id, approve=True)
        self.assertTrue(vote.approved)
        area.world.advance_pulse(force=True)
        self.assertIn(obj.id, area.world.state.objects)

    def test_rejection_blocks_creation(self) -> None:
        area = _area_with_members()
        obj = create_heat_object("bob", "거부될 불", 70.0)
        proposed = area.submit_creation("bob", obj, creation_type="heat")
        area.vote_on_creation("aria", proposed.proposal_id, approve=False)
        self.assertNotIn(obj.id, area.world.state.objects)

    def test_law_violation_never_reaches_consensus(self) -> None:
        area = _area_with_members()
        obj = create_heat_object("bob", "불법", 9000.0)
        result = area.submit_creation("bob", obj, creation_type="heat")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "law_violation")
        self.assertIn("heat_exceeds_law_limit", result.law_violations)


if __name__ == "__main__":
    unittest.main()
