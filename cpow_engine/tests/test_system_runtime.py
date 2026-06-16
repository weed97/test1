"""시행 시스템 런타임 집행 테스트."""

import unittest

from cpow_engine.areas import SimulationMode
from cpow_engine.areas.governance import EnactedSystem, GovernancePolicy, SystemProposalKind
from cpow_engine.areas.governance_eligibility import (
    LivingAreaPolicy,
    LongFlowPolicy,
    make_long_flow_spec,
)
from cpow_engine.areas.member_identity import IdentityPolicy
from cpow_engine.areas.registry import AreaRegistry
from cpow_engine.areas.system_runtime import SystemRuntime
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.physics import create_heat_object
from cpow_engine.tests.area_helpers import create_with_consensus, confirmed_object


def _runtime_governance_policy() -> GovernancePolicy:
    return GovernancePolicy(
        min_composers=2,
        min_cosponsors=3,
        announcement_sec=0.0,
        long_flow=LongFlowPolicy(
            min_flow_steps=3,
            min_rationale_chars=30,
            min_step_description_chars=15,
            min_title_chars=4,
            min_drafting_sec=0.0,
            min_composer_spread_sec=0.0,
            min_complexity_score=1.0,
        ),
        living_area=LivingAreaPolicy(
            min_human_members=2,
            min_distinct_human_creators=2,
            min_human_confirmed_creations=2,
            min_collaborative_events=1,
            max_npc_creation_share=0.9,
            min_member_human_creations=1,
            min_member_creation_invested=5.0,
            min_member_collab_signals=1,
        ),
        identity=IdentityPolicy(require_verified=True, min_person_key_chars=4),
    )


def _seed_living_area(area) -> None:
    instant = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
    area.world.policy = instant
    humans = [uid for uid in area.members if uid not in area.npcs]
    if len(humans) < 2:
        return
    needed = area.consensus.policy.approvals_needed(len(area.members))
    for i, creator in enumerate(humans):
        obj = create_heat_object(creator, f"work_{i}", 40.0)
        result = area.submit_creation(creator, obj, creation_type="heat")
        if result.consensus_pending and result.proposal_id:
            for j in range(needed):
                voter = humans[(i + j + 1) % len(humans)]
                proposal = area.consensus.get_proposal(result.proposal_id)
                if proposal is None or proposal.status.value != "pending":
                    break
                area.vote_on_creation(voter, result.proposal_id, approve=True)
        area.world.advance_pulse(force=True)


def _macro_flow_spec(**extra) -> dict:
    steps = [
        {"label": "관찰", "description": "봇 탐지 지표와 신고 채널을 설계하고 기록한다."},
        {"label": "설계", "description": "rate limit과 창조 간격을 단계별로 정의한다."},
        {"label": "시범", "description": "소규모 에리어에서 시범 적용한다."},
        {"label": "전면", "description": "전역 적용 전 최종 합의 절차를 밟는다."},
    ]
    rationale = "매크로 봇이 단순 창조로 생태계를 교란하지 못하도록 단계적 방어를 둔다."
    return make_long_flow_spec(
        rationale,
        steps,
        extra={"creations_per_window": 1, "window_sec": 3600.0, **extra},
    )


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
        policy = _runtime_governance_policy()
        reg = AreaRegistry(governance_policy=policy)
        area = reg.found("aria", "월드", mode=SimulationMode.CREATION_ADVENTURE)
        for i in range(5):
            uid = f"u{i}"
            reg.join(area.area_id, uid)
            p = area.power_ledger.get_or_create(uid)
            p.creation_gauge = 90.0
            p.creation_data_score = 50.0
            p.destruction_gauge = 10.0
            reg.governance.sync_member(uid, p)

        for uid in area.members:
            if uid not in area.npcs:
                p = area.power_ledger.get_or_create(uid)
                p.creation_gauge = max(p.creation_gauge, 120.0)

        _seed_living_area(area)
        for uid in area.members:
            if uid not in area.npcs:
                reg.register_member_identity(uid, f"person_secret_{uid}")

        draft = reg.draft_system_proposal(
            "u1",
            kind="macro_bot_defense",
            title="봇 방지 시스템",
            spec=_macro_flow_spec(),
            area_id=area.area_id,
        )
        self.assertTrue(draft["ok"], draft.get("reason", draft))
        pid = draft["proposal_id"]
        reg.sign_system_composer(pid, "u2")
        for i in range(5):
            reg.cosponsor_system_proposal(pid, f"u{i}")
        reg.governance.tick()

        for i in range(5):
            reg.vote_system_proposal(pid, f"u{i}", approve=True)

        rules = reg.system_runtime.merged_rules()
        self.assertEqual(rules.creations_per_window, 1)
        self.assertGreaterEqual(len(reg.system_runtime.enacted_systems()), 1)


if __name__ == "__main__":
    unittest.main()
