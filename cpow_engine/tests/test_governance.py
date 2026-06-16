"""시스템 거버넌스 — 공동발의·창조력 우위 투표."""

import unittest

from cpow_engine.areas.governance import (
    GovernanceLedger,
    GovernancePolicy,
    creation_exceeds_destruction,
    destruction_exceeds_creation,
)
from cpow_engine.areas.powers import UserPowers
from cpow_engine.areas.registry import AreaRegistry
from cpow_engine.areas import SimulationMode


def _test_policy() -> GovernancePolicy:
    return GovernancePolicy(
        min_composers=3,
        min_cosponsors=5,
        approval_ratio=0.51,
        reject_ratio=0.45,
        announcement_sec=0.0,
        voting_ttl_sec=600.0,
        max_sponsor_share=0.5,
    )


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
        )
        self.assertTrue(result.ok, result.reason)


class TestSystemGovernanceFlow(unittest.TestCase):
    def _registry_with_members(self, n: int) -> AreaRegistry:
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
        return reg

    def test_full_enactment_pipeline(self) -> None:
        reg = self._registry_with_members(8)
        draft = reg.draft_system_proposal(
            "user_1",
            kind="macro_bot_defense",
            title="매크로 봇 방지 시스템",
            spec={"rate_limit": 10},
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
        reg = self._registry_with_members(6)
        draft = reg.draft_system_proposal("user_0", kind="custom", title="테스트")
        pid = draft["proposal_id"]
        for i in (2, 3):
            reg.sign_system_composer(pid, f"user_{i}")
        for i in range(6):
            reg.cosponsor_system_proposal(pid, f"user_{i}")
        reg.governance.tick()

        vote = reg.vote_system_proposal(pid, "user_0", approve=True)
        self.assertFalse(vote["ok"])
        self.assertEqual(vote["reason"], "creation_must_exceed_destruction_to_vote")

    def test_announcement_broadcast(self) -> None:
        reg = self._registry_with_members(6)
        draft = reg.draft_system_proposal("user_1", kind="election_war", title="선거전")
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
