"""Test helpers for area creation with consensus."""

from __future__ import annotations

from cpow_engine.areas.area import CreatedArea
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
        voter = approver_id or area.founder_id
        if voter != creator_id or area.consensus.policy.approvals_needed(len(area.members)) > 1:
            area.vote_on_creation(voter, result.proposal_id, approve=True)
        area.world.advance_pulse(force=True)
    elif result.ok:
        area.world.advance_pulse(force=True)
    return result
