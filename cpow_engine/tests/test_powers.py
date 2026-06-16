"""Creation/destruction power tests."""

import unittest

from cpow_engine.areas import SimulationMode, found_area
from cpow_engine.areas.durability import get_durability, is_confirmed
from cpow_engine.areas.powers import UserPowers
from cpow_engine.areas.rift import MIGRATION_RIFT_THRESHOLD
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.models import PropertyDef
from cpow_engine.physics import create_heat_object
from cpow_engine.tests.area_helpers import create_with_consensus, confirmed_object


def _area():
    area = found_area("aria", "파워 테스트", mode=SimulationMode.CREATION_ADVENTURE)
    area.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
    area.join("bob")
    return area


class TestCreationPower(unittest.TestCase):
    def test_creation_spends_gauge_and_sets_durability(self) -> None:
        area = _area()
        obj = create_heat_object("bob", "단단한 불", 80.0)
        create_with_consensus(area, "bob", obj, creation_type="heat")
        confirmed = confirmed_object(area, obj.id)
        assert confirmed is not None
        self.assertTrue(is_confirmed(confirmed))
        self.assertGreater(get_durability(confirmed), 15.0)
        bob = area.power_ledger.get_or_create("bob")
        self.assertLess(bob.creation_gauge, 100.0)
        self.assertGreater(bob.creation_data_score, 0.0)

    def test_high_creation_makes_tougher_object(self) -> None:
        area = _area()
        big = create_heat_object("aria", "핵심 시설", 60.0)
        big.properties.append(PropertyDef("is_core_facility", 1.0, "flag"))
        create_with_consensus(area, "aria", big, creation_type="heat")
        small = create_heat_object("bob", "작은 불", 30.0)
        create_with_consensus(area, "bob", small, creation_type="heat")
        big_c = confirmed_object(area, big.id)
        small_c = confirmed_object(area, small.id)
        assert big_c and small_c
        self.assertGreater(get_durability(big_c), get_durability(small_c))


class TestDestructionPower(unittest.TestCase):
    def test_destroy_requires_destruction_power(self) -> None:
        area = _area()
        obj = create_heat_object("bob", "약한 불", 30.0)
        create_with_consensus(area, "bob", obj, creation_type="heat")
        confirmed = confirmed_object(area, obj.id)
        assert confirmed is not None
        durability = get_durability(confirmed)

        weak = area.power_ledger.get_or_create("bob")
        weak.destruction_gauge = durability - 1
        result = area.submit_mutation("bob", obj.id, "destroy")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "insufficient_destruction_power")

    def test_successful_destroy_applies_penalty_and_rift(self) -> None:
        area = _area()
        obj = create_heat_object("bob", "없앨 불", 40.0)
        create_with_consensus(area, "bob", obj, creation_type="heat")
        bob_before = area.power_ledger.get_or_create("bob").creation_data_score

        result = area.submit_mutation("bob", obj.id, "destroy")
        self.assertTrue(result.ok, result.reason)
        self.assertGreater(result.penalty_applied, 0.0)
        self.assertGreater(area.rift.level, 0.0)
        bob_after = area.power_ledger.get_or_create("bob")
        self.assertLess(bob_after.creation_data_score, bob_before)

    def test_creation_redeems_destruction_penalty(self) -> None:
        area = _area()
        obj = create_heat_object("bob", "부술 것", 35.0)
        create_with_consensus(area, "bob", obj, creation_type="heat")
        bob = area.power_ledger.get_or_create("bob")
        area.submit_mutation("bob", obj.id, "destroy")
        penalty_after_destroy = bob.destruction_penalty
        self.assertGreater(penalty_after_destroy, 0.0)

        new_obj = create_heat_object("bob", "회복의 불", 70.0)
        create_with_consensus(area, "bob", new_obj, creation_type="heat")
        self.assertLess(bob.destruction_penalty, penalty_after_destroy)
        self.assertGreater(bob.effective_creation_cap(), 0.0)
        confirmed = confirmed_object(area, new_obj.id)
        assert confirmed is not None
        self.assertTrue(is_confirmed(confirmed))

    def test_partial_creation_redeems_when_penalty_caps_gauge(self) -> None:
        from cpow_engine.areas.powers import REDEMPTION_MIN_SPEND, UserPowers

        powers = UserPowers(user_id="bob", creation_gauge=15.0)
        powers.destruction_penalty = 20.0
        spend = powers.resolve_creation_spend(24.6)
        self.assertGreaterEqual(spend, REDEMPTION_MIN_SPEND)
        self.assertLess(spend, 24.6)
        powers.spend_creation(spend)
        redeemed = powers.redeem_penalty_with_creation(spend)
        self.assertGreater(redeemed, 0.0)
        self.assertLess(powers.destruction_penalty, 20.0)

    def test_defend_reduces_rift_threat(self) -> None:
        area = _area()
        obj = create_heat_object("bob", "불", 60.0)
        create_with_consensus(area, "bob", obj, creation_type="heat")
        area.submit_mutation("bob", obj.id, "destroy")
        threat_before = area.rift.monster_threat
        defend = area.defend_rift("aria", power_spend=20.0)
        self.assertTrue(defend.ok)
        self.assertLess(area.rift.monster_threat, threat_before)


class TestCoreAndMigration(unittest.TestCase):
    def test_extract_and_restore_core(self) -> None:
        area = _area()
        aria = area.power_ledger.get_or_create("aria")
        aria.destruction_gauge = 200.0
        extracted = area.extract_core("aria")
        self.assertTrue(extracted["ok"], extracted.get("reason"))
        has_seed = any(
            o.get_property("area_seed") for o in area.world.state.objects.values()
        )
        self.assertFalse(has_seed)

        area2 = found_area("aria2", "새 땅", mode=SimulationMode.CREATION_ADVENTURE)
        area2.join("aria")
        assert "aria" in area.carried_cores
        area2.carried_cores["aria"] = area.carried_cores["aria"]
        restored = area2.restore_core("aria")
        self.assertTrue(restored.ok, restored.reason)

    def test_migration_when_rift_high(self) -> None:
        area = _area()
        area.rift.level = MIGRATION_RIFT_THRESHOLD + 5
        mig = area.migrate_member("bob")
        self.assertTrue(mig["ok"])
        self.assertNotIn("bob", area.members)


if __name__ == "__main__":
    unittest.main()
