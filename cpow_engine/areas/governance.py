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

from cpow_engine.areas.governance_eligibility import (
    LongFlowPolicy,
    LivingAreaPolicy,
    composer_spread_ok,
    drafting_duration_ok,
    validate_long_flow_proposal,
)
from cpow_engine.areas.member_identity import IdentityPolicy, MemberIdentityRegistry
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
    min_collab_signals_for_vote: int = 2
    max_active_cosponsors_per_user: int = 2
    min_hostile_endorsers: int = 2
    long_flow: LongFlowPolicy = field(default_factory=LongFlowPolicy)
    living_area: LivingAreaPolicy = field(default_factory=LivingAreaPolicy)
    identity: IdentityPolicy = field(default_factory=IdentityPolicy)

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
            "min_collab_signals_for_vote": self.min_collab_signals_for_vote,
            "max_active_cosponsors_per_user": self.max_active_cosponsors_per_user,
            "min_hostile_endorsers": self.min_hostile_endorsers,
            "long_flow": self.long_flow.to_dict(),
            "living_area": self.living_area.to_dict(),
            "identity": self.identity.to_dict(),
        }


def creation_exceeds_destruction(powers: UserPowers) -> bool:
    """투표권 — 창조력이 파괴력보다 높은 구성원."""
    creation_total = powers.creation_gauge + powers.creation_data_score
    destruction_total = powers.destruction_gauge + powers.destruction_penalty
    return creation_total > destruction_total


def vote_weight(powers: UserPowers) -> float:
    """창조 점수 그라인드 완화 — 로그 스케일 가중치."""
    creation_total = powers.creation_gauge + powers.creation_data_score
    destruction_total = powers.destruction_gauge + powers.destruction_penalty
    margin = creation_total - destruction_total
    if margin <= 0:
        return 0.0
    return min(1.0, 0.15 + math.log1p(margin) * 0.12)


def destruction_exceeds_creation(powers: UserPowers) -> bool:
    """창조적 파괴 시스템 발의 권장 대상."""
    creation_total = powers.creation_gauge + powers.creation_data_score
    destruction_total = powers.destruction_gauge + powers.destruction_penalty
    return destruction_total > creation_total


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
    origin_area_id: str = ""
    composers: set[str] = field(default_factory=set)
    cosponsors: set[str] = field(default_factory=set)
    approvals: set[str] = field(default_factory=set)
    rejections: set[str] = field(default_factory=set)
    approval_weight: float = 0.0
    rejection_weight: float = 0.0
    phase: SystemProposalPhase = SystemProposalPhase.DRAFTING
    created_at: float = field(default_factory=time.time)
    announced_at: float | None = None
    voting_open_at: float | None = None
    composer_signed_at: dict[str, float] = field(default_factory=dict)

    def to_public_dict(self, policy: GovernancePolicy, *, eligible_voters: int) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "kind": self.kind.value,
            "title": self.title,
            "spec": dict(self.spec),
            "lead_author": self.lead_author,
            "origin_area_id": self.origin_area_id,
            "phase": self.phase.value,
            "composers_count": len(self.composers),
            "composers_needed": policy.min_composers,
            "cosponsors_count": len(self.cosponsors),
            "cosponsors_needed": policy.min_cosponsors,
            "unique_cosponsors_count": len(self.cosponsors),
            "approvals": sorted(self.approvals),
            "rejections": sorted(self.rejections),
            "approval_weight": round(self.approval_weight, 4),
            "rejection_weight": round(self.rejection_weight, 4),
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
    codes: list[str] = field(default_factory=list)


class GovernanceLedger:
    """전역 시스템 발의·투표 — 에리어 오브젝트 창조와 분리."""

    def __init__(
        self,
        policy: GovernancePolicy | None = None,
        *,
        runtime: object | None = None,
        on_enact: Callable[[EnactedSystem], None] | None = None,
        identity: MemberIdentityRegistry | None = None,
    ) -> None:
        self.policy = policy or GovernancePolicy()
        self._runtime = runtime
        self._on_enact = on_enact
        self._identity = identity
        self._proposals: dict[str, SystemProposal] = {}
        self._enacted: list[EnactedSystem] = []
        self._announcements: list[dict] = []
        self._powers_by_area: dict[str, dict[str, UserPowers]] = {}

    def sync_member(
        self, user_id: str, powers: UserPowers, area_id: str,
    ) -> None:
        self._powers_by_area.setdefault(area_id, {})[user_id] = powers

    def powers_for(self, user_id: str, area_id: str) -> UserPowers | None:
        return self._powers_by_area.get(area_id, {}).get(user_id)

    def member_count(self, area_id: str | None = None) -> int:
        if area_id:
            return len(self._powers_by_area.get(area_id, {}))
        return sum(len(m) for m in self._powers_by_area.values())

    def eligible_voter_count(self, area_id: str) -> int:
        area_powers = self._powers_by_area.get(area_id, {})
        return sum(
            1 for p in area_powers.values()
            if creation_exceeds_destruction(p)
        )

    def eligible_vote_weight(self, area_id: str) -> float:
        area_powers = self._powers_by_area.get(area_id, {})
        return sum(
            vote_weight(p)
            for p in area_powers.values()
            if creation_exceeds_destruction(p)
        )

    def _unique_cosponsor_persons(self, proposal: SystemProposal) -> int:
        persons: set[str] = set()
        for uid in proposal.cosponsors:
            if self._identity is not None:
                pid = self._identity.person_id_for(uid)
                persons.add(pid if pid else uid)
            else:
                persons.add(uid)
        return len(persons)

    def _active_cosponsor_count(self, user_id: str) -> int:
        return sum(
            1
            for p in self._proposals.values()
            if user_id in p.cosponsors
            and p.phase
            not in (
                SystemProposalPhase.ENACTED,
                SystemProposalPhase.REJECTED,
                SystemProposalPhase.EXPIRED,
            )
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
        area_id: str = "",
    ) -> GovernanceResult:
        if not area_id:
            return GovernanceResult(False, reason="area_id_required")
        if self._world_monopolized():
            return GovernanceResult(False, reason="system_monopolized")
        if author_id not in self._powers_by_area.get(area_id, {}):
            return GovernanceResult(False, reason="not_a_registered_member")
        if lead_author_monopoly(
            list(self._proposals.values()),
            author_id,
            max_share=self.policy.max_sponsor_share,
        ):
            return GovernanceResult(False, reason="monopoly_limit_exceeded")

        powers = self.powers_for(author_id, area_id)
        if powers is None:
            return GovernanceResult(False, reason="not_a_registered_member")
        parsed_kind = SystemProposalKind.from_str(kind)
        flow_check = validate_long_flow_proposal(
            kind=parsed_kind,
            title=title,
            spec=spec,
            policy=self.policy.long_flow,
        )
        if not flow_check.ok:
            return GovernanceResult(
                False,
                reason=flow_check.reason,
                codes=list(flow_check.codes),
            )

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
            origin_area_id=area_id,
        )
        proposal.composers.add(author_id)
        proposal.composer_signed_at[author_id] = proposal.created_at
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
        if user_id not in self._powers_by_area.get(proposal.origin_area_id, {}):
            return GovernanceResult(False, reason="not_a_registered_member")
        if proposal.phase != SystemProposalPhase.DRAFTING:
            return GovernanceResult(False, reason="not_in_drafting_phase")

        proposal.composers.add(user_id)
        proposal.composer_signed_at[user_id] = time.time()
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
        if user_id not in self._powers_by_area.get(proposal.origin_area_id, {}):
            return GovernanceResult(False, reason="not_a_registered_member")
        if proposal.phase not in (
            SystemProposalPhase.COSPONSORING,
            SystemProposalPhase.DRAFTING,
        ):
            return GovernanceResult(False, reason="not_accepting_cosponsors")

        if proposal.phase == SystemProposalPhase.DRAFTING:
            return GovernanceResult(False, reason="composers_not_complete")

        if self._active_cosponsor_count(user_id) >= self.policy.max_active_cosponsors_per_user:
            return GovernanceResult(False, reason="cosponsor_limit_exceeded")

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

        powers = self.powers_for(user_id, proposal.origin_area_id)
        if powers is None:
            return GovernanceResult(False, reason="not_a_registered_member")
        if not creation_exceeds_destruction(powers):
            return GovernanceResult(False, reason="creation_must_exceed_destruction_to_vote")

        if user_id in proposal.approvals or user_id in proposal.rejections:
            return GovernanceResult(False, reason="already_voted")

        weight = vote_weight(powers)
        if approve:
            proposal.approvals.add(user_id)
            proposal.approval_weight += weight
        else:
            proposal.rejections.add(user_id)
            proposal.rejection_weight += weight

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
                continue
            if (
                proposal.phase == SystemProposalPhase.VOTING
                and proposal.voting_open_at is not None
                and (ts - proposal.voting_open_at) >= self.policy.voting_ttl_sec
            ):
                if not self._tally_vote(proposal):
                    if proposal.phase == SystemProposalPhase.VOTING:
                        proposal.phase = SystemProposalPhase.EXPIRED
                changed.append(proposal.proposal_id)
        return changed

    def get_proposal(self, proposal_id: str) -> SystemProposal | None:
        return self._proposals.get(proposal_id)

    def pending_proposals(self) -> list[dict]:
        out: list[dict] = []
        for p in self._proposals.values():
            if p.phase in (
                SystemProposalPhase.ENACTED,
                SystemProposalPhase.REJECTED,
                SystemProposalPhase.EXPIRED,
            ):
                continue
            eligible = self.eligible_voter_count(p.origin_area_id)
            pub = p.to_public_dict(self.policy, eligible_voters=eligible)
            pub["unique_cosponsors_count"] = self._unique_cosponsor_persons(p)
            out.append(pub)
        return out

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
        if proposal.phase == SystemProposalPhase.DRAFTING:
            if len(proposal.composers) < self.policy.min_composers:
                return
            now = time.time()
            lf = self.policy.long_flow
            if not drafting_duration_ok(proposal.created_at, now, policy=lf):
                return
            if not composer_spread_ok(proposal.composer_signed_at, policy=lf):
                return
            proposal.phase = SystemProposalPhase.COSPONSORING

        if (
            proposal.phase == SystemProposalPhase.COSPONSORING
            and self._unique_cosponsor_persons(proposal) >= self.policy.min_cosponsors
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
        area_id = proposal.origin_area_id
        eligible_weight = self.eligible_vote_weight(area_id)
        ratio = self._approval_ratio()
        needed = max(1.0, eligible_weight * ratio) if eligible_weight > 0 else 1.0
        block = (
            max(1.0, eligible_weight * self._reject_ratio())
            if eligible_weight > 0
            else 1.0
        )

        if proposal.approval_weight >= needed:
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

        if proposal.rejection_weight >= block:
            proposal.phase = SystemProposalPhase.REJECTED
        return False
