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


def ensure_member_collab(area: CreatedArea, user_id: str, *, min_signals: int = 1) -> None:
    """테스트용 — 확장·투표 등 협력 신호 충족."""
    if area.activity is None:
        return
    rec = area.activity.member_record(user_id)
    if rec is None:
        return
    while rec.collab_signals() < min_signals:
        rec.consensus_votes_cast += 1


def declare_hostile_bilateral(
    reg,
    area_a_id: str,
    founder_a: str,
    confirmer_a: str,
    area_b_id: str,
    founder_b: str,
    confirmer_b: str,
) -> None:
    """적대 2단계 — 창립자 발의, 구성원 확인."""
    reg.set_diplomatic_stance(area_a_id, area_b_id, "hostile", founder_a)
    reg.set_diplomatic_stance(area_a_id, area_b_id, "hostile", confirmer_a)
    reg.set_diplomatic_stance(area_b_id, area_a_id, "hostile", founder_b)
    reg.set_diplomatic_stance(area_b_id, area_a_id, "hostile", confirmer_b)
