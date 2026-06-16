"""시스템 거버넌스 — 공동발의·창조력 우위 투표."""

import unittest

from cpow_engine.areas.area import CreatedArea
from cpow_engine.areas.governance import (
    GovernanceLedger,
    GovernancePolicy,
    SystemProposalKind,
    creation_exceeds_destruction,
)
from cpow_engine.areas.governance_eligibility import (
    LivingAreaPolicy,
    LongFlowPolicy,
    make_long_flow_spec,
    validate_long_flow_proposal,
)
from cpow_engine.areas.member_identity import IdentityPolicy
from cpow_engine.areas.powers import UserPowers
from cpow_engine.areas.registry import AreaRegistry
from cpow_engine.areas import SimulationMode
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.physics import create_heat_object


def _test_long_flow_policy() -> LongFlowPolicy:
    return LongFlowPolicy(
        min_flow_steps=3,
        min_rationale_chars=30,
        min_step_description_chars=15,
        min_title_chars=4,
        min_drafting_sec=0.0,
        min_composer_spread_sec=0.0,
        min_complexity_score=1.0,
        max_trivial_spec_keys=2,
    )


def _test_living_area_policy() -> LivingAreaPolicy:
    return LivingAreaPolicy(
        min_human_members=2,
        min_distinct_human_creators=2,
        min_human_confirmed_creations=2,
        min_collaborative_events=1,
        max_npc_creation_share=0.9,
        min_member_human_creations=1,
        min_member_creation_invested=5.0,
        min_member_collab_signals=1,
    )


def _test_identity_policy() -> IdentityPolicy:
    return IdentityPolicy(
        require_verified=True,
        min_person_key_chars=4,
    )


def _test_policy() -> GovernancePolicy:
    return GovernancePolicy(
        min_composers=3,
        min_cosponsors=5,
        approval_ratio=0.51,
        reject_ratio=0.45,
        announcement_sec=0.0,
        voting_ttl_sec=600.0,
        max_sponsor_share=0.5,
        long_flow=_test_long_flow_policy(),
        living_area=_test_living_area_policy(),
        identity=_test_identity_policy(),
    )


def _flow_steps(count: int = 4) -> list[dict]:
    base = [
        {"label": "관찰", "description": "현재 생태계와 봇 행동 패턴을 기록하고 분석한다."},
        {"label": "설계", "description": "단계별 규칙과 예외 조항을 문서화하여 합의한다."},
        {"label": "시범", "description": "소규모 그룹에서 시범 적용 후 피드백을 수집한다."},
        {"label": "전면", "description": "전역 적용 전 최종 검토와 공지 절차를 완료한다."},
    ]
    return base[:count]


def _macro_flow_spec(**extra) -> dict:
    rationale = (
        "매크로 봇이 단순 창조로 생태계를 교란하지 못하도록 "
        "단계적 방어 체계를 도입한다."
    )
    return make_long_flow_spec(rationale, _flow_steps(4), extra=extra)


def _creator(uid: str) -> UserPowers:
    return UserPowers(
        user_id=uid,
        creation_gauge=80.0,
        creation_data_score=40.0,
        destruction_gauge=20.0,
        destruction_penalty=5.0,
    )


def _destroyer(uid: str) -> UserPowers:
    return UserPowers(
        user_id=uid,
        creation_gauge=15.0,
        creation_data_score=5.0,
        destruction_gauge=90.0,
        destruction_penalty=10.0,
    )


def _register_identities(reg: AreaRegistry, *user_ids: str) -> None:
    for uid in user_ids:
        reg.register_member_identity(uid, f"person_secret_{uid}")


def _seed_living_area(area: CreatedArea) -> None:
    """인간 공동창작 활동 — 모든 구성원이 창조·합의에 참여."""
    instant = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)
    area.world.policy = instant
    humans = [uid for uid in area.members if uid not in area.npcs]
    if len(humans) < 2:
        return
    needed = area.consensus.policy.approvals_needed(len(area.members))
    for i, creator in enumerate(humans):
        obj = create_heat_object(creator, f"collab_work_{i}", 40.0)
        result = area.submit_creation(creator, obj, creation_type="heat")
        if result.consensus_pending and result.proposal_id:
            for j in range(needed):
                voter = humans[(i + j + 1) % len(humans)]
                proposal = area.consensus.get_proposal(result.proposal_id)
                if proposal is None or proposal.status.value != "pending":
                    break
                area.vote_on_creation(voter, result.proposal_id, approve=True)
        area.world.advance_pulse(force=True)


def _registry_with_members(n: int) -> tuple[AreaRegistry, CreatedArea]:
    reg = AreaRegistry(governance_policy=_test_policy())
    area = reg.found("founder", "테스트 월드", mode=SimulationMode.CREATION_ADVENTURE)
    for i in range(n):
        uid = f"user_{i}"
        reg.join(area.area_id, uid)
        p = reg.get(area.area_id).power_ledger.get_or_create(uid)
        if i % 3 == 0:
            reg.get(area.area_id).power_ledger.members[uid] = _destroyer(uid)
        else:
            reg.get(area.area_id).power_ledger.members[uid] = _creator(uid)
        reg.governance.sync_member(uid, reg.get(area.area_id).power_ledger.members[uid])
    for uid in area.members:
        if uid not in area.npcs:
            powers = area.power_ledger.get_or_create(uid)
            powers.creation_gauge = max(powers.creation_gauge, 120.0)
    _seed_living_area(area)
    humans = [uid for uid in area.members if uid not in area.npcs]
    _register_identities(reg, *humans)
    return reg, area


class TestLongFlowEligibility(unittest.TestCase):
    def test_trivial_spec_blocked(self) -> None:
        result = validate_long_flow_proposal(
            kind=SystemProposalKind.MACRO_BOT_DEFENSE,
            title="매크로 봇 방지 시스템",
            spec={"rate_limit": 10},
            policy=_test_long_flow_policy(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "simple_creation_blocked")
        self.assertIn("trivial_spec_blocked", result.codes)

    def test_long_flow_accepted(self) -> None:
        result = validate_long_flow_proposal(
            kind=SystemProposalKind.MACRO_BOT_DEFENSE,
            title="매크로 봇 방지 시스템",
            spec=_macro_flow_spec(rate_limit=10),
            policy=_test_long_flow_policy(),
        )
        self.assertTrue(result.ok, result.codes)


class TestMemberIdentity(unittest.TestCase):
    def test_unverified_identity_blocks_draft(self) -> None:
        reg, area = _registry_with_members(4)
        reg.identity._bindings.clear()
        reg.identity._person_to_user.clear()
        reg.identity._user_to_person.clear()
        draft = reg.draft_system_proposal(
            "user_1",
            kind="custom",
            title="커스텀 시스템 규칙",
            spec=make_long_flow_spec(
                "운영 규칙을 단계적으로 정립하고 전체 공지 절차를 따른다.",
                _flow_steps(3),
            ),
            area_id=area.area_id,
        )
        self.assertFalse(draft["ok"])
        self.assertEqual(draft["reason"], "identity_not_verified")

    def test_one_person_one_account(self) -> None:
        reg = AreaRegistry(governance_policy=_test_policy())
        first = reg.register_member_identity("alice", "same_person_key_1234")
        self.assertTrue(first["ok"], first.get("reason"))
        second = reg.register_member_identity("alice_bot", "same_person_key_1234")
        self.assertFalse(second["ok"])
        self.assertEqual(second["reason"], "duplicate_person_account")

    def test_one_account_one_person(self) -> None:
        reg = AreaRegistry(governance_policy=_test_policy())
        reg.register_member_identity("bob", "person_alpha_key_1234")
        rebound = reg.register_member_identity("bob", "person_beta_key_5678")
        self.assertFalse(rebound["ok"])
        self.assertEqual(rebound["reason"], "account_identity_locked")


class TestLivingAreaEligibility(unittest.TestCase):
    def test_inactive_area_blocks_governance(self) -> None:
        reg = AreaRegistry(governance_policy=_test_policy())
        area = reg.found("founder", "빈 월드", mode=SimulationMode.CREATION_ADVENTURE)
        reg.join(area.area_id, "alice")
        reg.join(area.area_id, "bob")
        reg.governance.sync_member("alice", _creator("alice"))
        _register_identities(reg, "alice")
        draft = reg.draft_system_proposal(
            "alice",
            kind="custom",
            title="커스텀 시스템 규칙",
            spec=make_long_flow_spec(
                "운영 규칙을 단계적으로 정립하고 전체 공지 절차를 따른다.",
                _flow_steps(3),
            ),
            area_id=area.area_id,
        )
        self.assertFalse(draft["ok"])
        self.assertEqual(draft["reason"], "area_not_living")
        self.assertIn("insufficient_human_creations", draft["codes"])

    def test_bot_dominated_area_blocked(self) -> None:
        reg = AreaRegistry(governance_policy=_test_policy())
        area = reg.found("founder", "봇 월드", mode=SimulationMode.CREATION_ADVENTURE)
        reg.join(area.area_id, "alice")
        reg.join(area.area_id, "bob")
        reg.governance.sync_member("alice", _creator("alice"))
        _register_identities(reg, "alice")
        assert area.activity is not None
        area.activity.record_human_creation("alice", invested=20.0)
        area.activity.record_human_creation("bob", invested=20.0)
        area.activity.record_consensus_vote("bob")
        area.activity.record_consensus_vote("alice")
        area.activity.npc_creations = 50
        draft = reg.draft_system_proposal(
            "alice",
            kind="custom",
            title="커스텀 시스템 규칙",
            spec=make_long_flow_spec(
                "운영 규칙을 단계적으로 정립하고 전체 공지 절차를 따른다.",
                _flow_steps(3),
            ),
            area_id=area.area_id,
        )
        self.assertFalse(draft["ok"])
        self.assertEqual(draft["reason"], "area_not_living")
        self.assertIn("npc_creation_dominates_area", draft["codes"])


class TestVoteEligibility(unittest.TestCase):
    def test_creation_majority_can_vote(self) -> None:
        self.assertTrue(creation_exceeds_destruction(_creator("a")))
        self.assertFalse(creation_exceeds_destruction(_destroyer("b")))

    def test_destroyer_can_draft_creative_destruction(self) -> None:
        ledger = GovernanceLedger(_test_policy())
        ledger.sync_member("d", _destroyer("d"))
        result = ledger.draft_proposal(
            "d",
            kind="creative_destruction",
            title="창조적 파괴 헌장",
            spec=make_long_flow_spec(
                "파괴가 창조를 잠식하지 않도록 단계적 규율과 상한을 문서화하여 합의한다.",
                _flow_steps(3),
            ),
            area_id="area_test",
        )
        self.assertTrue(result.ok, result.reason)

    def test_simple_creation_blocked_at_draft(self) -> None:
        ledger = GovernanceLedger(_test_policy())
        ledger.sync_member("a", _creator("a"))
        result = ledger.draft_proposal(
            "a",
            kind="macro_bot_defense",
            title="매크로 봇 방지 시스템",
            spec={"rate_limit": 10},
            area_id="area_test",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "simple_creation_blocked")
        self.assertIn("trivial_spec_blocked", result.codes)


class TestSystemGovernanceFlow(unittest.TestCase):
    def test_full_enactment_pipeline(self) -> None:
        reg, area = _registry_with_members(8)
        draft = reg.draft_system_proposal(
            "user_1",
            kind="macro_bot_defense",
            title="매크로 봇 방지 시스템",
            spec=_macro_flow_spec(rate_limit=10),
            area_id=area.area_id,
        )
        self.assertTrue(draft["ok"], draft.get("reason"))
        pid = draft["proposal_id"]

        for i in (2, 3):
            reg.sign_system_composer(pid, f"user_{i}")

        proposal = reg.governance.get_proposal(pid)
        assert proposal is not None
        self.assertEqual(proposal.phase.value, "cosponsoring")

        for i in range(8):
            reg.cosponsor_system_proposal(pid, f"user_{i}")

        reg.tick_governance()
        proposal = reg.governance.get_proposal(pid)
        assert proposal is not None
        self.assertIn(proposal.phase.value, ("announced", "voting"))

        reg.governance.tick()
        creators = [f"user_{i}" for i in range(8) if i % 3 != 0]
        for uid in creators:
            reg.vote_system_proposal(pid, uid, approve=True)

        proposal = reg.governance.get_proposal(pid)
        assert proposal is not None
        self.assertEqual(proposal.phase.value, "enacted")
        enacted = reg.governance.enacted_systems()
        self.assertEqual(len(enacted), 1)
        self.assertEqual(enacted[0]["kind"], "macro_bot_defense")

    def test_destroyer_cannot_vote(self) -> None:
        reg, area = _registry_with_members(6)
        draft = reg.draft_system_proposal(
            "user_0",
            kind="custom",
            title="커스텀 시스템 규칙",
            spec=make_long_flow_spec(
                "커뮤니티 합의로 운영 규칙을 단계적으로 정립하고 전체 공지 절차를 따른다.",
                _flow_steps(3),
            ),
            area_id=area.area_id,
        )
        self.assertTrue(draft["ok"], draft.get("reason"))
        pid = draft["proposal_id"]
        for i in (2, 3):
            reg.sign_system_composer(pid, f"user_{i}")
        for i in range(6):
            reg.cosponsor_system_proposal(pid, f"user_{i}")
        reg.governance.tick()

        area.power_ledger.members["user_0"] = _destroyer("user_0")
        reg.governance.sync_member("user_0", _destroyer("user_0"))

        vote = reg.vote_system_proposal(pid, "user_0", approve=True)
        self.assertFalse(vote["ok"])
        self.assertEqual(vote["reason"], "creation_must_exceed_destruction_to_vote")

    def test_announcement_broadcast(self) -> None:
        reg, area = _registry_with_members(6)
        draft = reg.draft_system_proposal(
            "user_1",
            kind="election_war",
            title="선거전 시스템 규칙",
            spec=make_long_flow_spec(
                "선거와 전쟁 규칙을 단계적으로 설계하여 공정성을 확보한다.",
                _flow_steps(4),
            ),
            area_id=area.area_id,
        )
        self.assertTrue(draft["ok"], draft.get("reason"))
        pid = draft["proposal_id"]
        for i in (2, 3):
            reg.sign_system_composer(pid, f"user_{i}")
        for i in range(6):
            reg.cosponsor_system_proposal(pid, f"user_{i}")
        announcements = reg.governance.announcements()
        self.assertGreaterEqual(len(announcements), 1)
        self.assertIn("전체 공지", announcements[-1]["message"])


if __name__ == "__main__":
    unittest.main()
