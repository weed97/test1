"""시스템 거버넌스 — 공동발의·전체 공지·창조력 우위 투표.

구성원 오브젝트 창조는 자유. 매크로 방지·창조적 파괴·선거/전쟁 등
**시스템 규칙**은 100+ 창조자 구성 → 1000+ 공동발의 → 전체 공지 → 투표.
투표권: 창조력 > 파괴력 인 구성원만.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from typing import Callable

from cpow_engine.areas.powers import UserPowers


class SystemProposalPhase(str, Enum):
    DRAFTING = "drafting"
    COSPONSORING = "cosponsoring"
    ANNOUNCED = "announced"
    VOTING = "voting"
    ENACTED = "enacted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SystemProposalKind(str, Enum):
    MACRO_BOT_DEFENSE = "macro_bot_defense"
    CREATIVE_DESTRUCTION = "creative_destruction"
    ELECTION_WAR = "election_war"
    CUSTOM = "custom"

    @classmethod
    def from_str(cls, value: str) -> SystemProposalKind:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.CUSTOM


@dataclass
class GovernancePolicy:
    """전역 시스템 발의 규칙 — 테스트 시 축소 가능."""

    min_composers: int = 100
    min_cosponsors: int = 1000
    approval_ratio: float = 0.51
    reject_ratio: float = 0.45
    max_sponsor_share: float = 0.08
    announcement_sec: float = 60.0
    voting_ttl_sec: float = 600.0
    proposal_ttl_sec: float = 86_400.0

    def approvals_needed(self, eligible_voters: int) -> int:
        if eligible_voters <= 0:
            return 1
        return max(1, math.ceil(eligible_voters * self.approval_ratio))

    def rejections_to_block(self, eligible_voters: int) -> int:
        if eligible_voters <= 0:
            return 1
        return max(1, math.ceil(eligible_voters * self.reject_ratio))

    def to_dict(self) -> dict[str, float | int]:
        return {
            "min_composers": self.min_composers,
            "min_cosponsors": self.min_cosponsors,
            "approval_ratio": self.approval_ratio,
            "reject_ratio": self.reject_ratio,
            "max_sponsor_share": self.max_sponsor_share,
            "announcement_sec": self.announcement_sec,
            "voting_ttl_sec": self.voting_ttl_sec,
            "proposal_ttl_sec": self.proposal_ttl_sec,
        }


def creation_exceeds_destruction(powers: UserPowers) -> bool:
    """투표권 — 창조력이 파괴력보다 높은 구성원."""
    creation_total = powers.creation_gauge + powers.creation_data_score
    destruction_total = powers.destruction_gauge + powers.destruction_penalty
    return creation_total > destruction_total


def destruction_exceeds_creation(powers: UserPowers) -> bool:
    """창조적 파괴 시스템 발의 권장 대상."""
    creation_total = powers.creation_gauge + powers.creation_data_score
    destruction_total = powers.destruction_gauge + powers.destruction_penalty
    return destruction_total > creation_total


def monopoly_violation(
    sponsors: set[str],
    user_id: str,
    *,
    max_share: float,
) -> bool:
    """동일 발의자가 활성 발의에서 과도한 비중을 갖는지."""
    if not sponsors:
        return False
    if user_id not in sponsors:
        return False
    return (1.0 / len(sponsors)) > max_share + 1e-9 and len(sponsors) < int(1.0 / max_share)


def lead_author_monopoly(
    proposals: list[SystemProposal],
    user_id: str,
    *,
    max_share: float,
) -> bool:
    active = [
        p for p in proposals
        if p.phase not in (
            SystemProposalPhase.ENACTED,
            SystemProposalPhase.REJECTED,
            SystemProposalPhase.EXPIRED,
        )
    ]
    if not active:
        return False
    led = sum(1 for p in active if p.lead_author == user_id)
    return (led / len(active)) > max_share + 1e-9


@dataclass
class SystemProposal:
    proposal_id: str
    kind: SystemProposalKind
    title: str
    spec: dict
    lead_author: str
    composers: set[str] = field(default_factory=set)
    cosponsors: set[str] = field(default_factory=set)
    approvals: set[str] = field(default_factory=set)
    rejections: set[str] = field(default_factory=set)
    phase: SystemProposalPhase = SystemProposalPhase.DRAFTING
    created_at: float = field(default_factory=time.time)
    announced_at: float | None = None
    voting_open_at: float | None = None

    def to_public_dict(self, policy: GovernancePolicy, *, eligible_voters: int) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "kind": self.kind.value,
            "title": self.title,
            "spec": dict(self.spec),
            "lead_author": self.lead_author,
            "phase": self.phase.value,
            "composers_count": len(self.composers),
            "composers_needed": policy.min_composers,
            "cosponsors_count": len(self.cosponsors),
            "cosponsors_needed": policy.min_cosponsors,
            "approvals": sorted(self.approvals),
            "rejections": sorted(self.rejections),
            "approvals_needed": policy.approvals_needed(eligible_voters),
            "eligible_voters": eligible_voters,
            "announced_at": self.announced_at,
            "voting_open_at": self.voting_open_at,
            "created_at": self.created_at,
        }


@dataclass
class EnactedSystem:
    system_id: str
    kind: SystemProposalKind
    title: str
    spec: dict
    enacted_at: float = field(default_factory=time.time)
    proposal_id: str = ""

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "kind": self.kind.value,
            "title": self.title,
            "spec": dict(self.spec),
            "enacted_at": self.enacted_at,
            "proposal_id": self.proposal_id,
        }


@dataclass
class GovernanceResult:
    ok: bool
    reason: str = ""
    proposal_id: str = ""
    phase: str = ""
    enacted: bool = False


class GovernanceLedger:
    """전역 시스템 발의·투표 — 에리어 오브젝트 창조와 분리."""

    def __init__(
        self,
        policy: GovernancePolicy | None = None,
        *,
        runtime: object | None = None,
        on_enact: Callable[[EnactedSystem], None] | None = None,
    ) -> None:
        self.policy = policy or GovernancePolicy()
        self._runtime = runtime
        self._on_enact = on_enact
        self._proposals: dict[str, SystemProposal] = {}
        self._enacted: list[EnactedSystem] = []
        self._announcements: list[dict] = []
        self._member_powers: dict[str, UserPowers] = {}

    def sync_member(self, user_id: str, powers: UserPowers) -> None:
        self._member_powers[user_id] = powers

    def member_count(self) -> int:
        return len(self._member_powers)

    def eligible_voter_count(self) -> int:
        return sum(
            1 for p in self._member_powers.values()
            if creation_exceeds_destruction(p)
        )

    def _approval_ratio(self) -> float:
        base = self.policy.approval_ratio
        if self._runtime is not None:
            return self._runtime.governance_approval_ratio(base)
        return base

    def _reject_ratio(self) -> float:
        return self.policy.reject_ratio

    def draft_proposal(
        self,
        author_id: str,
        *,
        kind: str,
        title: str,
        spec: dict | None = None,
    ) -> GovernanceResult:
        if self._world_monopolized():
            return GovernanceResult(False, reason="system_monopolized")
        if author_id not in self._member_powers:
            return GovernanceResult(False, reason="not_a_registered_member")
        if lead_author_monopoly(
            list(self._proposals.values()),
            author_id,
            max_share=self.policy.max_sponsor_share,
        ):
            return GovernanceResult(False, reason="monopoly_limit_exceeded")

        powers = self._member_powers[author_id]
        parsed_kind = SystemProposalKind.from_str(kind)
        if parsed_kind == SystemProposalKind.CREATIVE_DESTRUCTION:
            if not destruction_exceeds_creation(powers):
                return GovernanceResult(
                    False,
                    reason="creative_destruction_requires_high_destruction",
                )

        proposal = SystemProposal(
            proposal_id=f"sys_{uuid.uuid4().hex[:10]}",
            kind=parsed_kind,
            title=title,
            spec=dict(spec or {}),
            lead_author=author_id,
        )
        proposal.composers.add(author_id)
        self._proposals[proposal.proposal_id] = proposal
        self._advance_phase(proposal)
        return GovernanceResult(
            True,
            reason="draft_created",
            proposal_id=proposal.proposal_id,
            phase=proposal.phase.value,
        )

    def sign_composer(self, proposal_id: str, user_id: str) -> GovernanceResult:
        proposal = self._get_open_proposal(proposal_id)
        if proposal is None:
            return GovernanceResult(False, proposal_id=proposal_id, reason="proposal_not_open")
        if user_id not in self._member_powers:
            return GovernanceResult(False, reason="not_a_registered_member")
        if proposal.phase != SystemProposalPhase.DRAFTING:
            return GovernanceResult(False, reason="not_in_drafting_phase")

        proposal.composers.add(user_id)
        self._advance_phase(proposal)
        return GovernanceResult(
            True,
            reason="composer_signed",
            proposal_id=proposal_id,
            phase=proposal.phase.value,
        )

    def cosponsor(self, proposal_id: str, user_id: str) -> GovernanceResult:
        proposal = self._get_open_proposal(proposal_id)
        if proposal is None:
            return GovernanceResult(False, proposal_id=proposal_id, reason="proposal_not_open")
        if user_id not in self._member_powers:
            return GovernanceResult(False, reason="not_a_registered_member")
        if proposal.phase not in (
            SystemProposalPhase.COSPONSORING,
            SystemProposalPhase.DRAFTING,
        ):
            return GovernanceResult(False, reason="not_accepting_cosponsors")

        if proposal.phase == SystemProposalPhase.DRAFTING:
            return GovernanceResult(False, reason="composers_not_complete")

        proposal.cosponsors.add(user_id)
        self._advance_phase(proposal)
        return GovernanceResult(
            True,
            reason="cosponsored",
            proposal_id=proposal_id,
            phase=proposal.phase.value,
        )

    def vote(self, proposal_id: str, user_id: str, *, approve: bool) -> GovernanceResult:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return GovernanceResult(False, proposal_id=proposal_id, reason="proposal_not_found")
        if proposal.phase != SystemProposalPhase.VOTING:
            return GovernanceResult(False, reason="not_in_voting_phase")

        powers = self._member_powers.get(user_id)
        if powers is None:
            return GovernanceResult(False, reason="not_a_registered_member")
        if not creation_exceeds_destruction(powers):
            return GovernanceResult(False, reason="creation_must_exceed_destruction_to_vote")

        if user_id in proposal.approvals or user_id in proposal.rejections:
            return GovernanceResult(False, reason="already_voted")

        if approve:
            proposal.approvals.add(user_id)
        else:
            proposal.rejections.add(user_id)

        enacted = self._tally_vote(proposal)
        return GovernanceResult(
            True,
            reason="enacted" if enacted else "vote_recorded",
            proposal_id=proposal_id,
            phase=proposal.phase.value,
            enacted=enacted,
        )

    def tick(self, now: float | None = None) -> list[str]:
        """공지 → 투표 전환, 만료 처리."""
        ts = now if now is not None else time.time()
        changed: list[str] = []
        for proposal in list(self._proposals.values()):
            if proposal.phase == SystemProposalPhase.EXPIRED:
                continue
            if (ts - proposal.created_at) > self.policy.proposal_ttl_sec:
                proposal.phase = SystemProposalPhase.EXPIRED
                changed.append(proposal.proposal_id)
                continue
            if (
                proposal.phase == SystemProposalPhase.ANNOUNCED
                and proposal.announced_at is not None
                and (ts - proposal.announced_at) >= self.policy.announcement_sec
            ):
                proposal.phase = SystemProposalPhase.VOTING
                proposal.voting_open_at = ts
                changed.append(proposal.proposal_id)
        return changed

    def get_proposal(self, proposal_id: str) -> SystemProposal | None:
        return self._proposals.get(proposal_id)

    def pending_proposals(self) -> list[dict]:
        eligible = self.eligible_voter_count()
        return [
            p.to_public_dict(self.policy, eligible_voters=eligible)
            for p in self._proposals.values()
            if p.phase not in (
                SystemProposalPhase.ENACTED,
                SystemProposalPhase.REJECTED,
                SystemProposalPhase.EXPIRED,
            )
        ]

    def announcements(self) -> list[dict]:
        return list(self._announcements)

    def enacted_systems(self) -> list[dict]:
        return [s.to_dict() for s in self._enacted]

    def _world_monopolized(self) -> bool:
        if len(self._enacted) < 5:
            return False
        by_kind: dict[str, int] = {}
        for s in self._enacted:
            by_kind[s.kind.value] = by_kind.get(s.kind.value, 0) + 1
        dominant = max(by_kind.values()) / len(self._enacted)
        return dominant > 0.85

    def _get_open_proposal(self, proposal_id: str) -> SystemProposal | None:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return None
        if proposal.phase in (
            SystemProposalPhase.ENACTED,
            SystemProposalPhase.REJECTED,
            SystemProposalPhase.EXPIRED,
        ):
            return None
        return proposal

    def _advance_phase(self, proposal: SystemProposal) -> None:
        if (
            proposal.phase == SystemProposalPhase.DRAFTING
            and len(proposal.composers) >= self.policy.min_composers
        ):
            proposal.phase = SystemProposalPhase.COSPONSORING

        if (
            proposal.phase == SystemProposalPhase.COSPONSORING
            and len(proposal.cosponsors) >= self.policy.min_cosponsors
        ):
            proposal.phase = SystemProposalPhase.ANNOUNCED
            proposal.announced_at = time.time()
            self._broadcast_announcement(proposal)

    def _broadcast_announcement(self, proposal: SystemProposal) -> None:
        notice = {
            "proposal_id": proposal.proposal_id,
            "title": proposal.title,
            "kind": proposal.kind.value,
            "phase": "announced",
            "message": (
                f"[전체 공지] 시스템 발의: {proposal.title} "
                f"({proposal.kind.value}) — 창조력>파괴력 구성원 투표 예정"
            ),
            "composers": len(proposal.composers),
            "cosponsors": len(proposal.cosponsors),
            "announced_at": proposal.announced_at,
        }
        self._announcements.append(notice)

    def _tally_vote(self, proposal: SystemProposal) -> bool:
        eligible = self.eligible_voter_count()
        ratio = self._approval_ratio()
        needed = max(1, math.ceil(eligible * ratio)) if eligible > 0 else 1
        block = max(1, math.ceil(eligible * self._reject_ratio())) if eligible > 0 else 1

        if len(proposal.approvals) >= needed:
            proposal.phase = SystemProposalPhase.ENACTED
            enacted = EnactedSystem(
                system_id=f"enacted_{uuid.uuid4().hex[:8]}",
                kind=proposal.kind,
                title=proposal.title,
                spec=dict(proposal.spec),
                proposal_id=proposal.proposal_id,
            )
            self._enacted.append(enacted)
            if self._on_enact:
                self._on_enact(enacted)
            return True

        if len(proposal.rejections) >= block:
            proposal.phase = SystemProposalPhase.REJECTED
        return False
