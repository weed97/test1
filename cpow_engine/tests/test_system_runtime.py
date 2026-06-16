"""시행 시스템 런타임 집행 테스트."""

import unittest

from cpow_engine.areas import SimulationMode
from cpow_engine.areas.governance import EnactedSystem, GovernancePolicy, SystemProposalKind
from cpow_engine.areas.registry import AreaRegistry
from cpow_engine.areas.system_runtime import SystemRuntime
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.physics import create_heat_object
from cpow_engine.tests.area_helpers import create_with_consensus, confirmed_object


def _enact_macro(runtime: SystemRuntime) -> None:
    runtime.register(EnactedSystem(
        system_id="test_macro",
        kind=SystemProposalKind.MACRO_BOT_DEFENSE,
        title="매크로 방지",
        spec={
            "creations_per_window": 2,
            "window_sec": 3600.0,
        },
    ))


class TestMacroBotRuntime(unittest.TestCase):
    def test_rate_limit_blocks_spam_creation(self) -> None:
        reg = AreaRegistry(governance_policy=GovernancePolicy(
            min_composers=1, min_cosponsors=1, announcement_sec=0.0,
        ))
        area = reg.found("aria", "월드", mode=SimulationMode.CREATION_ADVENTURE)
        instant = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
        area.world.policy = instant
        area._base_collab_policy = instant
        area.join("bob")
        _enact_macro(reg.system_runtime)
        area.refresh_runtime_policy()

        for i in range(2):
            obj = create_heat_object("bob", f"불{i}", 20.0)
            r = area.submit_creation(
                "bob", obj, creation_type="heat", bypass_consensus=True,
            )
            self.assertTrue(r.ok, r.reason)

        blocked = area.submit_creation(
            "bob",
            create_heat_object("bob", "불3", 20.0),
            creation_type="heat",
            bypass_consensus=True,
        )
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.reason, "macro_rate_limit_exceeded")

    def test_collab_policy_tightened_after_enact(self) -> None:
        reg = AreaRegistry()
        area = reg.found("aria", "월드", mode=SimulationMode.CREATION_ADVENTURE)
        base_cd = area.world.policy.min_creator_cooldown_sec
        reg.system_runtime.register(EnactedSystem(
            system_id="m",
            kind=SystemProposalKind.MACRO_BOT_DEFENSE,
            title="t",
            spec={"min_creator_cooldown_sec": base_cd + 50.0},
        ))
        area.refresh_runtime_policy()
        self.assertGreater(
            area.world.policy.min_creator_cooldown_sec,
            base_cd,
        )


class TestCreativeDestructionRuntime(unittest.TestCase):
    def test_destroy_limit_enforced(self) -> None:
        reg = AreaRegistry()
        area = reg.found("aria", "월드", mode=SimulationMode.CREATION_ADVENTURE)
        area.world.policy = CollabPolicy(
            pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0,
        )
        area.join("bob")
        reg.system_runtime.register(EnactedSystem(
            system_id="cd",
            kind=SystemProposalKind.CREATIVE_DESTRUCTION,
            title="창조적 파괴",
            spec={"max_destroys_per_window": 1, "destroy_window_sec": 3600.0},
        ))

        obj_a = create_heat_object("bob", "a", 15.0)
        obj_b = create_heat_object("bob", "b", 15.0)
        create_with_consensus(area, "bob", obj_a, creation_type="heat")
        create_with_consensus(area, "bob", obj_b, creation_type="heat")

        bob_powers = area.power_ledger.get_or_create("bob")
        bob_powers.destruction_gauge = 500.0

        r1 = area.submit_mutation("bob", obj_a.id, "destroy")
        self.assertTrue(r1.ok, r1.reason)

        r2 = area.submit_mutation("bob", obj_b.id, "destroy")
        self.assertFalse(r2.ok)
        self.assertEqual(r2.reason, "creative_destruction_limit_exceeded")


class TestGovernanceEnactmentWiresRuntime(unittest.TestCase):
    def test_vote_enactment_applies_runtime(self) -> None:
        policy = GovernancePolicy(
            min_composers=2,
            min_cosponsors=3,
            announcement_sec=0.0,
        )
        reg = AreaRegistry(governance_policy=policy)
        area = reg.found("aria", "월드", mode=SimulationMode.CREATION_ADVENTURE)
        for i in range(5):
            uid = f"u{i}"
            reg.join(area.area_id, uid)
            p = area.power_ledger.get_or_create(uid)
            p.creation_gauge = 90.0
            p.creation_data_score = 50.0
            p.destruction_gauge = 10.0

        draft = reg.draft_system_proposal(
            "u1",
            kind="macro_bot_defense",
            title="봇 방지",
            spec={"creations_per_window": 1, "window_sec": 3600.0},
        )
        pid = draft["proposal_id"]
        reg.sign_system_composer(pid, "u2")
        for i in range(5):
            reg.cosponsor_system_proposal(pid, f"u{i}")
        reg.governance.tick()

        for i in range(5):
            if i % 3 != 0:
                reg.vote_system_proposal(pid, f"u{i}", approve=True)

        rules = reg.system_runtime.merged_rules()
        self.assertEqual(rules.creations_per_window, 1)
        self.assertGreaterEqual(len(reg.system_runtime.enacted_systems()), 1)


if __name__ == "__main__":
    unittest.main()
