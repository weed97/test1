"""Test helpers for area creation with consensus."""

from __future__ import annotations

from cpow_engine.areas.area import CreatedArea
from cpow_engine.areas.consensus import ProposalStatus
from cpow_engine.collab import WorldSubmissionResult
from cpow_engine.models import CreativeObject


def approve_pending_creation(
    area: CreatedArea,
    result: WorldSubmissionResult,
    *,
    voter_id: str | None = None,
) -> WorldSubmissionResult:
    """합의 대기 창조를 승인하고 펄스까지 반영."""
    if not result.consensus_pending:
        area.world.advance_pulse(force=True)
        return result

    voter = voter_id or area.founder_id
    area.vote_on_creation(voter, result.proposal_id, approve=True)
    area.world.advance_pulse(force=True)
    return result


def create_with_consensus(
    area: CreatedArea,
    creator_id: str,
    obj: CreativeObject,
    *,
    creation_type: str = "heat",
    approver_id: str | None = None,
) -> WorldSubmissionResult:
    result = area.submit_creation(creator_id, obj, creation_type=creation_type)
    if result.consensus_pending:
        needed = area.consensus.policy.approvals_needed(len(area.members))
        voters = list(area.members.keys())
        if approver_id and approver_id not in voters:
            voters.append(approver_id)
        for voter in voters:
            proposal = area.consensus.get_proposal(result.proposal_id)
            if proposal is None or proposal.status != ProposalStatus.PENDING:
                break
            if voter in proposal.approvals:
                continue
            area.vote_on_creation(voter, result.proposal_id, approve=True)
            proposal = area.consensus.get_proposal(result.proposal_id)
            if proposal and len(proposal.approvals) >= needed:
                break
        if obj.id not in area.world.state.objects or not _is_confirmed(area, obj.id):
            area.world.advance_pulse(force=True)
    elif result.ok:
        area.world.advance_pulse(force=True)
    return result


def _is_confirmed(area: CreatedArea, object_id: str) -> bool:
    from cpow_engine.areas.durability import is_confirmed

    live = area.world.state.objects.get(object_id)
    return live is not None and is_confirmed(live)


def confirmed_object(area: CreatedArea, object_id: str):
    return area.world.state.objects.get(object_id)
