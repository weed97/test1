"""창조 합의 — 새 오브젝트는 구성원 승인 후 반영."""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from cpow_engine.models import CreativeObject


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ConsensusPolicy:
    """합의 규칙 — 과반 이상 승인 필요."""

    required_approval_ratio: float = 0.51
    min_votes: int = 2
    proposal_ttl_sec: float = 600.0
    reject_threshold_ratio: float = 0.5

    def approvals_needed(self, member_count: int) -> int:
        if member_count <= 1:
            return 1
        ratio_votes = math.ceil(member_count * self.required_approval_ratio)
        return max(self.min_votes, ratio_votes)

    def rejections_to_block(self, member_count: int) -> int:
        return math.ceil(member_count * self.reject_threshold_ratio)

    def to_dict(self) -> dict[str, float | int]:
        return {
            "required_approval_ratio": self.required_approval_ratio,
            "min_votes": self.min_votes,
            "proposal_ttl_sec": self.proposal_ttl_sec,
            "reject_threshold_ratio": self.reject_threshold_ratio,
        }


@dataclass
class CreationProposal:
    proposal_id: str
    proposer_id: str
    obj: CreativeObject
    creation_type: str
    creativity_score: float
    approvals: set[str] = field(default_factory=set)
    rejections: set[str] = field(default_factory=set)
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: float = field(default_factory=time.time)

    def is_expired(self, policy: ConsensusPolicy, now: float) -> bool:
        return (now - self.created_at) > policy.proposal_ttl_sec

    def to_public_dict(self, policy: ConsensusPolicy, member_count: int) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "proposer_id": self.proposer_id,
            "object_id": self.obj.id,
            "label": self.obj.label,
            "creation_type": self.creation_type,
            "status": self.status.value,
            "approvals": sorted(self.approvals),
            "rejections": sorted(self.rejections),
            "approvals_needed": policy.approvals_needed(member_count),
            "approvals_received": len(self.approvals),
            "rejections_received": len(self.rejections),
            "created_at": self.created_at,
        }


@dataclass
class VoteResult:
    ok: bool
    proposal_id: str = ""
    status: str = ""
    reason: str = ""
    approvals_needed: int = 0
    approvals_received: int = 0
    approved: bool = False


class ConsensusGate:
    """새 오브젝트 창조 제안·투표."""

    def __init__(self, policy: ConsensusPolicy | None = None) -> None:
        self.policy = policy or ConsensusPolicy()
        self._proposals: dict[str, CreationProposal] = {}

    def propose(
        self,
        proposer_id: str,
        obj: CreativeObject,
        *,
        creation_type: str,
        creativity_score: float = 1.0,
        member_count: int,
        now: float | None = None,
    ) -> CreationProposal:
        self._expire_old(now)
        proposal = CreationProposal(
            proposal_id=f"prop_{uuid.uuid4().hex[:10]}",
            proposer_id=proposer_id,
            obj=obj,
            creation_type=creation_type,
            creativity_score=creativity_score,
            created_at=now if now is not None else time.time(),
        )
        proposal.approvals.add(proposer_id)
        self._proposals[proposal.proposal_id] = proposal
        self._update_status(proposal, member_count)
        return proposal

    def vote(
        self,
        voter_id: str,
        proposal_id: str,
        *,
        approve: bool,
        member_count: int,
        now: float | None = None,
    ) -> VoteResult:
        self._expire_old(now)
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return VoteResult(False, proposal_id, reason="proposal_not_found")

        if proposal.status != ProposalStatus.PENDING:
            return VoteResult(
                False, proposal_id,
                status=proposal.status.value,
                reason="proposal_already_closed",
            )

        if voter_id in proposal.approvals or voter_id in proposal.rejections:
            return VoteResult(False, proposal_id, reason="already_voted")

        if approve:
            proposal.approvals.add(voter_id)
        else:
            proposal.rejections.add(voter_id)

        approved = self._update_status(proposal, member_count)
        needed = self.policy.approvals_needed(member_count)

        return VoteResult(
            ok=True,
            proposal_id=proposal_id,
            status=proposal.status.value,
            reason="approved" if approved else "vote_recorded",
            approvals_needed=needed,
            approvals_received=len(proposal.approvals),
            approved=approved,
        )

    def get_proposal(self, proposal_id: str) -> CreationProposal | None:
        return self._proposals.get(proposal_id)

    def pending_proposals(self) -> list[CreationProposal]:
        return [
            p for p in self._proposals.values()
            if p.status == ProposalStatus.PENDING
        ]

    def pop_approved(self, proposal_id: str) -> CreationProposal | None:
        proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal.status != ProposalStatus.APPROVED:
            return None
        del self._proposals[proposal_id]
        return proposal

    def _update_status(self, proposal: CreationProposal, member_count: int) -> bool:
        needed = self.policy.approvals_needed(member_count)
        if len(proposal.approvals) >= needed:
            proposal.status = ProposalStatus.APPROVED
            return True
        if len(proposal.rejections) >= self.policy.rejections_to_block(member_count):
            proposal.status = ProposalStatus.REJECTED
        return False

    def _expire_old(self, now: float | None) -> None:
        ts = now if now is not None else time.time()
        for pid, proposal in list(self._proposals.items()):
            if (
                proposal.status == ProposalStatus.PENDING
                and proposal.is_expired(self.policy, ts)
            ):
                proposal.status = ProposalStatus.EXPIRED
                del self._proposals[pid]
