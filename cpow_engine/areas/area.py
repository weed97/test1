"""창조된 에리어 — 모드·역할·법칙·협동 월드 통합."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from cpow_engine.areas.destruction import (
    DestroyAttemptResult,
    DefendResult,
    attempt_defend_rift,
    attempt_powered_destroy,
)
from cpow_engine.areas.dominance import dominance_ratio
from cpow_engine.areas.extent import (
    compute_extent,
    expansion_cost,
    max_object_durability_gate,
)
from cpow_engine.areas.imbue import attempt_imbue_destruction, get_imbued_destruction
from cpow_engine.areas.npcs import (
    ALLOWED_NPC_TASKS,
    AreaNpc,
    NpcTask,
    allocate_creation,
    spawn_npc_record,
    tick_npc_farm,
)
from cpow_engine.areas.durability import (
    compute_durability,
    get_creation_investment,
    get_durability,
    is_confirmed,
    is_core_facility,
    stamp_creation_powers,
)
from cpow_engine.areas.economy import RegionalEconomy
from cpow_engine.areas.powers import PowerLedger, UserPowers, creation_cost_for_object
from cpow_engine.areas.rift import CarriedCore, RiftState
from cpow_engine.areas.laws import AreaLawSet, load_area_templates, template_for_mode
from cpow_engine.areas.modes import SimulationMode
from cpow_engine.areas.roles import (
    ContributorRole,
    RolePermissions,
    default_role_for_mode,
    permissions_for,
)
from cpow_engine.areas.area_activity import (
    AreaActivityTracker,
    is_human_member,
    is_npc_creation,
)
from cpow_engine.areas.consensus import (
    ConsensusGate,
    ConsensusPolicy,
    CreationProposal,
    ProposalStatus,
    VoteResult,
)
from cpow_engine.areas.law_validator import validate_creation, validate_mutation
from cpow_engine.areas.mutations import (
    MutationOp,
    MutationResult,
    PendingMutation,
    apply_destroy,
    apply_mutation,
    can_actor_mutate,
    mark_co_creator,
    object_in_area,
)
from cpow_engine.collab import CollaborativeWorld, WorldSubmissionResult
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.collab.pulse import PulseResult
from cpow_engine.models import ActionRecord, CreativeObject, PropertyDef
from cpow_engine.physics import create_heat_object


@dataclass
class AdventureResult:
    ok: bool
    action_type: str = ""
    reason: str = ""
    energy_delta: float = 0.0
    tick: int = 0


@dataclass
class CreatedArea:
    """초기 창조자가 세운 에리어 — 법칙·모드·경제를 가짐."""

    area_id: str
    label: str
    founder_id: str
    mode: SimulationMode
    laws: AreaLawSet
    world: CollaborativeWorld
    economy: RegionalEconomy = field(default_factory=RegionalEconomy)
    members: dict[str, ContributorRole] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    _pending_mutations: list[PendingMutation] = field(default_factory=list)
    consensus: ConsensusGate = field(default_factory=ConsensusGate)
    power_ledger: PowerLedger = field(default_factory=PowerLedger)
    rift: RiftState = field(default_factory=RiftState)
    carried_cores: dict[str, CarriedCore] = field(default_factory=dict)
    extent_bonus: float = 1.0
    npcs: dict[str, AreaNpc] = field(default_factory=dict)
    activity: AreaActivityTracker | None = field(default=None, repr=False)
    _system_runtime: object | None = field(default=None, repr=False)
    _base_collab_policy: CollabPolicy | None = field(default=None, repr=False)

    def attach_system_runtime(self, runtime: object) -> None:
        if self.activity is None:
            self.activity = AreaActivityTracker(area_id=self.area_id)
        self._system_runtime = runtime
        if self._base_collab_policy is None:
            p = self.world.policy
            self._base_collab_policy = CollabPolicy(
                max_relative_change=p.max_relative_change,
                max_absolute_heat_delta=p.max_absolute_heat_delta,
                max_creations_per_tick=p.max_creations_per_tick,
                max_patches_per_batch=p.max_patches_per_batch,
                damp_factor=p.damp_factor,
                noise_threshold=p.noise_threshold,
                min_creativity_for_large_change=p.min_creativity_for_large_change,
                large_change_multiplier=p.large_change_multiplier,
                pulse_interval_sec=p.pulse_interval_sec,
                min_creator_cooldown_sec=p.min_creator_cooldown_sec,
                max_creations_per_creator_per_pulse=p.max_creations_per_creator_per_pulse,
            )
        self.refresh_runtime_policy()

    def refresh_runtime_policy(self) -> None:
        if self._system_runtime is not None and self._base_collab_policy is not None:
            self.world.policy = self._system_runtime.apply_collab_policy(
                self._base_collab_policy,
            )

    def area_extent(self) -> float:
        return compute_extent(
            self.world.state.objects,
            extent_bonus=self.extent_bonus,
            member_count=len(self.members),
        )

    def dominance_vs(self, other: CreatedArea) -> float:
        return dominance_ratio(self.area_extent(), other.area_extent())

    def spawn_npc(self, owner_id: str, label: str) -> dict:
        if owner_id not in self.members:
            return {"ok": False, "reason": "not_a_member"}
        perms = permissions_for(self.role_of(owner_id))
        if not perms.can_spawn_npc:
            return {"ok": False, "reason": "role_cannot_spawn_npc"}

        npc = spawn_npc_record(owner_id, label)
        self.npcs[npc.npc_id] = npc
        self.join(npc.npc_id, requested_role=ContributorRole.OBSERVER)
        return {"ok": True, "npc": npc.to_dict()}

    def allocate_npc_creation(
        self,
        owner_id: str,
        npc_id: str,
        amount: float,
    ) -> dict:
        if owner_id not in self.members:
            return {"ok": False, "reason": "not_a_member"}
        npc = self.npcs.get(npc_id)
        if npc is None:
            return {"ok": False, "reason": "npc_not_found"}
        if npc.owner_id != owner_id:
            return {"ok": False, "reason": "not_npc_owner"}

        powers = self.power_ledger.get_or_create(owner_id)
        ok, reason = allocate_creation(npc, powers, amount)
        return {"ok": ok, "reason": reason, "npc": npc.to_dict()}

    def set_npc_task(self, owner_id: str, npc_id: str, task: str) -> dict:
        if owner_id not in self.members:
            return {"ok": False, "reason": "not_a_member"}
        npc = self.npcs.get(npc_id)
        if npc is None:
            return {"ok": False, "reason": "npc_not_found"}
        if npc.owner_id != owner_id:
            return {"ok": False, "reason": "not_npc_owner"}

        parsed = NpcTask.from_str(task)
        if parsed not in ALLOWED_NPC_TASKS and parsed != NpcTask.IDLE:
            return {"ok": False, "reason": "task_not_allowed_in_area"}
        npc.task = parsed
        return {"ok": True, "npc": npc.to_dict()}

    def tick_npcs(self) -> list[dict]:
        """NPC 작업 틱 — 농사 시 밭 오브젝트 창조."""
        results: list[dict] = []
        for npc in list(self.npcs.values()):
            if npc.task != NpcTask.FARM:
                continue
            if self._system_runtime is not None:
                npc_check = self._system_runtime.check_npc_creation_allowed(npc.npc_id)
                if not npc_check.ok:
                    results.append({
                        "ok": False,
                        "npc_id": npc.npc_id,
                        "task": "farm",
                        "reason": npc_check.reason,
                    })
                    continue
            tick_result, plot, cost = tick_npc_farm(npc)
            if not tick_result.ok or plot is None:
                results.append(tick_result.__dict__)
                continue

            created = self.submit_creation(
                npc.npc_id,
                plot,
                creation_type="heat",
                bypass_consensus=True,
                pre_spent_creation=cost,
            )
            entry = {
                **tick_result.__dict__,
                "creation_ok": created.ok,
                "creation_reason": created.reason,
            }
            if created.ok and created.object_id:
                entry["object_id"] = created.object_id
                if self._system_runtime is not None:
                    self._system_runtime.record_npc_creation(npc.npc_id)
            else:
                npc.creation_gauge += cost
            results.append(entry)
        if results:
            self._refresh_economy()
        return results

    def imbue_object_destruction(
        self,
        actor_id: str,
        object_id: str,
        amount: float,
    ) -> dict:
        if actor_id not in self.members:
            return {"ok": False, "reason": "not_a_member"}
        perms = permissions_for(self.role_of(actor_id))
        if not perms.can_imbue_destruction:
            return {"ok": False, "reason": "role_cannot_imbue"}

        obj = self.world.state.objects.get(object_id)
        if obj is None:
            return {"ok": False, "reason": "object_not_found"}
        if not object_in_area(obj, self.area_id):
            return {"ok": False, "reason": "object_not_in_area"}

        powers = self.power_ledger.get_or_create(actor_id)
        result = attempt_imbue_destruction(
            powers,
            obj,
            amount,
            area_extent=self.area_extent(),
            is_confirmed_obj=is_confirmed(obj),
        )
        out = {
            "ok": result.ok,
            "reason": result.reason,
            "amount_applied": result.amount_applied,
            "imbued_total": result.imbued_total,
            "destruction_spent": result.destruction_spent,
            "cap_remaining": result.cap_remaining,
            "area_extent": round(self.area_extent(), 2),
            "imbued_destruction": get_imbued_destruction(obj),
        }
        if result.ok:
            mark_co_creator(obj, actor_id)
            if is_human_member(self, actor_id) and self.activity is not None:
                self.activity.record_co_creation(actor_id)
        return out

    def expand_area(self, actor_id: str) -> dict:
        if actor_id not in self.members:
            return {"ok": False, "reason": "not_a_member"}
        perms = permissions_for(self.role_of(actor_id))
        if not perms.can_expand_area:
            return {"ok": False, "reason": "role_cannot_expand_area"}

        from cpow_engine.areas.area_activity import is_human_member

        human_members = [m for m in self.members if is_human_member(self, m)]
        if len(human_members) < 2:
            return {"ok": False, "reason": "expand_requires_collaborative_area"}
        if self.activity is not None:
            rec = self.activity.member_record(actor_id)
            if rec is None or rec.collab_signals() < 1:
                return {"ok": False, "reason": "expand_requires_member_collaboration"}

        creation_cost, destruction_cost = expansion_cost(self.extent_bonus)
        powers = self.power_ledger.get_or_create(actor_id)
        if powers.creation_gauge < creation_cost:
            return {"ok": False, "reason": "insufficient_creation_power"}
        if powers.destruction_gauge < destruction_cost:
            return {"ok": False, "reason": "insufficient_destruction_power"}

        if not powers.spend_creation(creation_cost):
            return {"ok": False, "reason": "insufficient_creation_power"}
        if not powers.spend_destruction(destruction_cost):
            powers.creation_gauge += creation_cost
            return {"ok": False, "reason": "insufficient_destruction_power"}

        self.extent_bonus += 0.25
        self._refresh_economy()
        return {
            "ok": True,
            "reason": "area_expanded",
            "extent_bonus": round(self.extent_bonus, 2),
            "area_extent": round(self.area_extent(), 2),
            "creation_spent": creation_cost,
            "destruction_spent": destruction_cost,
        }

    def role_of(self, creator_id: str) -> ContributorRole:
        return self.members.get(creator_id, ContributorRole.OBSERVER)

    def join(
        self,
        creator_id: str,
        *,
        requested_role: ContributorRole | None = None,
    ) -> ContributorRole:
        if creator_id == self.founder_id:
            role = ContributorRole.FOUNDER
        elif requested_role is not None:
            role = self._resolve_join_role(requested_role)
        else:
            role = default_role_for_mode(self.mode)
        self.members[creator_id] = role
        self.power_ledger.get_or_create(creator_id)
        if self.activity is None:
            self.activity = AreaActivityTracker(area_id=self.area_id)
        if is_human_member(self, creator_id):
            self.activity.record_join(creator_id)
        return role

    def _resolve_join_role(self, requested: ContributorRole) -> ContributorRole:
        if requested == ContributorRole.FOUNDER:
            return ContributorRole.COLLABORATOR
        if self.mode == SimulationMode.CREATION and requested == ContributorRole.ADVENTURER:
            return ContributorRole.COLLABORATOR
        if self.mode == SimulationMode.ADVENTURE and requested == ContributorRole.COLLABORATOR:
            return ContributorRole.ADVENTURER
        return requested

    def set_mode(self, actor_id: str, mode: SimulationMode) -> bool:
        if self.role_of(actor_id) != ContributorRole.FOUNDER:
            return False
        self.mode = mode
        return True

    def submit_creation(
        self,
        creator_id: str,
        obj: CreativeObject,
        *,
        creation_type: str = "heat",
        creativity_score: float = 1.0,
        bypass_consensus: bool = False,
        pre_spent_creation: float | None = None,
        allied_home_area: CreatedArea | None = None,
    ) -> WorldSubmissionResult:
        is_allied = allied_home_area is not None
        if is_allied:
            role = allied_home_area.role_of(creator_id)
            perms = permissions_for(role)
        else:
            role = self.role_of(creator_id)
            perms = permissions_for(role)
        npc_record = self.npcs.get(creator_id)
        is_npc_delegate = (
            npc_record is not None
            and npc_record.task != NpcTask.IDLE
            and pre_spent_creation is not None
        )

        if not is_allied and creator_id not in self.members:
            return WorldSubmissionResult(False, reason="not_a_member")
        if is_allied and creator_id not in allied_home_area.members:
            return WorldSubmissionResult(False, reason="not_a_member")

        if not is_npc_delegate:
            if not self._mode_allows_creation(role):
                return WorldSubmissionResult(False, reason="mode_blocks_creation")

            if not perms.can_create_objects and not (
                self.mode == SimulationMode.CREATION_ADVENTURE and perms.can_adventure
            ):
                if not is_allied:
                    return WorldSubmissionResult(False, reason="role_cannot_create")

        is_founding_seed = obj.get_property("area_seed") is not None
        if not is_founding_seed and self._system_runtime is not None:
            runtime_check = self._system_runtime.check_creation_allowed(creator_id)
            if not runtime_check.ok:
                return WorldSubmissionResult(
                    False,
                    object_id=obj.id,
                    reason=runtime_check.reason,
                )

        if not is_founding_seed and not self.laws.allows_creation_type(creation_type):
            return WorldSubmissionResult(False, reason="creation_type_not_allowed_in_area")

        self._tag_object_with_area(obj)

        heat_role_max = perms.max_heat_intensity
        if npc_record is not None:
            owner_perms = permissions_for(self.role_of(npc_record.owner_id))
            heat_role_max = owner_perms.max_heat_intensity

        law_check = validate_creation(
            obj,
            self.laws,
            creation_type=creation_type,
            role_max_heat=heat_role_max,
            state=self.world.state,
            is_founding_seed=is_founding_seed,
        )
        if not law_check.ok:
            return WorldSubmissionResult(
                False,
                object_id=obj.id,
                reason="law_violation",
                law_violations=law_check.codes,
            )

        if not bypass_consensus and not is_founding_seed:
            return self._submit_via_consensus(
                creator_id, obj,
                creation_type=creation_type,
                creativity_score=creativity_score,
            )

        result = self.world.submit_creation(
            creator_id, obj, creativity_score=creativity_score,
        )
        if result.ok and result.queued:
            self.world.advance_pulse(force=True)
            result.queued = False
        if result.ok:
            live = self.world.state.objects.get(obj.id)
            if live and not is_confirmed(live):
                ok, redeemed = self._finalize_confirmed_creation(
                    creator_id,
                    live,
                    creation_type=creation_type,
                    pre_spent=pre_spent_creation,
                    power_ledger_source=(
                        allied_home_area.power_ledger if is_allied else None
                    ),
                )
                if not ok:
                    self.world.state.objects.pop(obj.id, None)
                    result.ok = False
                    result.reason = "insufficient_creation_power"
                else:
                    result.penalty_redeemed = redeemed
                    if self._system_runtime is not None:
                        self._system_runtime.record_creation(creator_id)
        self._refresh_economy()
        return result

    def vote_on_creation(
        self,
        voter_id: str,
        proposal_id: str,
        *,
        approve: bool,
    ) -> VoteResult:
        if voter_id not in self.members:
            return VoteResult(False, proposal_id, reason="not_a_member")

        vote = self.consensus.vote(
            voter_id,
            proposal_id,
            approve=approve,
            member_count=len(self.members),
        )
        if not vote.ok:
            return vote

        if is_human_member(self, voter_id) and self.activity is not None:
            self.activity.record_consensus_vote(voter_id)

        if vote.approved:
            proposal = self.consensus.get_proposal(proposal_id)
            if proposal and proposal.status == ProposalStatus.APPROVED:
                commit = self._commit_proposal(proposal)
                if not commit.ok:
                    vote.ok = False
                    vote.reason = commit.reason
        return vote

    def pending_proposals(self) -> list[dict]:
        return [
            p.to_public_dict(self.consensus.policy, len(self.members))
            for p in self.consensus.pending_proposals()
        ]

    def _submit_via_consensus(
        self,
        creator_id: str,
        obj: CreativeObject,
        *,
        creation_type: str,
        creativity_score: float,
    ) -> WorldSubmissionResult:
        proposal = self.consensus.propose(
            creator_id,
            obj,
            creation_type=creation_type,
            creativity_score=creativity_score,
            member_count=len(self.members),
        )
        needed = self.consensus.policy.approvals_needed(len(self.members))

        if proposal.status == ProposalStatus.APPROVED:
            return self._commit_proposal(proposal)

        return WorldSubmissionResult(
            True,
            object_id=obj.id,
            reason="consensus_pending",
            proposal_id=proposal.proposal_id,
            consensus_pending=True,
            approvals_needed=needed,
            approvals_received=len(proposal.approvals),
        )

    def _commit_proposal(self, proposal: CreationProposal) -> WorldSubmissionResult:
        perms = permissions_for(self.role_of(proposal.proposer_id))
        law_check = validate_creation(
            proposal.obj,
            self.laws,
            creation_type=proposal.creation_type,
            role_max_heat=perms.max_heat_intensity,
            state=self.world.state,
            is_founding_seed=False,
        )
        if not law_check.ok:
            proposal.status = ProposalStatus.REJECTED
            return WorldSubmissionResult(
                False,
                object_id=proposal.obj.id,
                reason="law_violation_on_commit",
                law_violations=law_check.codes,
                proposal_id=proposal.proposal_id,
            )

        result = self.world.submit_creation(
            proposal.proposer_id,
            proposal.obj,
            creativity_score=proposal.creativity_score,
        )
        if result.ok and result.queued:
            self.world.advance_pulse(force=True)
            result.queued = False
        if result.ok:
            live = self.world.state.objects.get(proposal.obj.id)
            if live is None:
                result.ok = False
                result.reason = "commit_failed"
            ok, redeemed = self._finalize_confirmed_creation(
                proposal.proposer_id,
                live,
                creation_type=proposal.creation_type,
            )
            if not ok:
                self.world.state.objects.pop(proposal.obj.id, None)
                result.ok = False
                result.reason = "insufficient_creation_power"
            else:
                result.penalty_redeemed = redeemed
        self.consensus.pop_approved(proposal.proposal_id)
        self._refresh_economy()
        result.proposal_id = proposal.proposal_id
        result.consensus_pending = False
        result.reason = "consensus_approved" if result.ok else result.reason
        return result

    def submit_adventure(
        self,
        actor_id: str,
        action_type: str,
        *,
        target_object_id: str = "",
        label: str = "",
    ) -> AdventureResult:
        role = self.role_of(actor_id)
        perms = permissions_for(role)
        if not perms.can_adventure:
            return AdventureResult(False, action_type, reason="role_cannot_adventure")

        if self.mode == SimulationMode.CREATION:
            return AdventureResult(False, action_type, reason="creation_mode_no_adventure")

        state = self.world.state
        if action_type == "explore":
            state.entropy += 0.02
            state.action_log.append(ActionRecord(
                actor_id=actor_id,
                action_type="area_explore",
                payload={"area_id": self.area_id, "label": label or self.label},
            ))
            self._refresh_economy()
            return AdventureResult(
                True, action_type, reason="explored",
                energy_delta=0.5, tick=state.tick,
            )

        if action_type == "interact":
            if not target_object_id or target_object_id not in state.objects:
                return AdventureResult(False, action_type, reason="target_not_found")
            target = state.objects[target_object_id]
            heat = target.get_property("heat_intensity")
            delta = (heat.value * 0.01) if heat else 0.2
            state.energy_pool += delta
            state.action_log.append(ActionRecord(
                actor_id=actor_id,
                action_type="area_interact",
                payload={
                    "area_id": self.area_id,
                    "target_id": target_object_id,
                },
            ))
            self._refresh_economy()
            return AdventureResult(
                True, action_type, reason="interacted",
                energy_delta=delta, tick=state.tick,
            )

        if action_type == "contribute":
            if not perms.can_create_objects and role != ContributorRole.ADVENTURER:
                return AdventureResult(False, action_type, reason="cannot_contribute")
            small = create_heat_object(
                actor_id,
                label or "모험가의 불씨",
                heat_intensity=min(perms.max_heat_intensity, self.laws.heat_baseline + 10),
            )
            created = self.submit_creation(
                actor_id, small, creation_type="heat",
            )
            if not created.ok:
                return AdventureResult(False, action_type, reason=created.reason)
            if created.consensus_pending:
                return AdventureResult(
                    False, action_type,
                    reason="consensus_pending",
                )
            return AdventureResult(
                True, action_type, reason="contributed",
                tick=self.world.state.tick,
            )

        return AdventureResult(False, action_type, reason="unknown_adventure_action")

    def attempt_destroy(
        self,
        actor_id: str,
        object_id: str,
    ) -> MutationResult:
        """확정된 오브젝트 파괴 — 파괴력 ≥ 내구도 필요."""
        return self.submit_mutation(actor_id, object_id, "destroy")

    def defend_rift(
        self,
        actor_id: str,
        *,
        power_spend: float,
    ) -> DefendResult:
        if actor_id not in self.members:
            return DefendResult(False, reason="not_a_member")
        powers = self.power_ledger.get_or_create(actor_id)
        return attempt_defend_rift(powers, self.rift, power_spend=power_spend)

    def extract_core(self, actor_id: str) -> dict:
        """핵심 코어를 들고 다른 지역으로 이주·복원."""
        if actor_id not in self.members:
            return {"ok": False, "reason": "not_a_member"}

        core_id = None
        core_obj = None
        for oid, obj in self.world.state.objects.items():
            if is_core_facility(obj) and obj.get_property("area_seed"):
                core_id = oid
                core_obj = obj
                break

        if core_obj is None or core_id is None:
            return {"ok": False, "reason": "no_core_found"}

        powers = self.power_ledger.get_or_create(actor_id)
        carry_cost = get_durability(core_obj) * 0.5
        if powers.destruction_gauge < carry_cost:
            return {
                "ok": False,
                "reason": "insufficient_destruction_power_to_extract",
                "required": carry_cost,
            }

        powers.spend_destruction(carry_cost)
        heat = core_obj.get_property("heat_intensity")
        carried = CarriedCore(
            carrier_id=actor_id,
            source_area_id=self.area_id,
            label=core_obj.label,
            creation_investment=get_creation_investment(core_obj),
            durability=get_durability(core_obj),
            heat_baseline=heat.value if heat else self.laws.heat_baseline,
        )
        self.carried_cores[actor_id] = carried
        self.world.state.objects.pop(core_id)
        return {"ok": True, "reason": "core_extracted", "core": carried.to_dict()}

    def restore_core(
        self,
        actor_id: str,
        *,
        label: str | None = None,
    ) -> WorldSubmissionResult:
        """운반 중인 코어로 이 에리어에 심장 복원."""
        carried = self.carried_cores.get(actor_id)
        if carried is None:
            return WorldSubmissionResult(False, reason="no_carried_core")

        seed = create_heat_object(
            actor_id,
            label or f"{carried.label} (복원)",
            heat_intensity=carried.heat_baseline,
        )
        seed.properties.append(
            PropertyDef(name="area_seed", value=1.0, unit="founding_core")
        )
        result = self.submit_creation(
            actor_id, seed, creation_type="heat", bypass_consensus=True,
        )
        if result.ok:
            obj = self.world.state.objects.get(result.object_id)
            if obj:
                stamp_creation_powers(
                    obj, carried.creation_investment, is_core=True,
                )
            del self.carried_cores[actor_id]
            result.reason = "core_restored"
        return result

    def migrate_member(self, actor_id: str) -> dict:
        """균열이 크면 이주 권고 — 멤버를 에리어에서 빼고 코어 운반 가능."""
        if actor_id not in self.members:
            return {"ok": False, "reason": "not_a_member"}
        if not self.rift.to_dict().get("migration_recommended"):
            return {"ok": False, "reason": "migration_not_needed"}

        role = self.members.pop(actor_id)
        return {
            "ok": True,
            "reason": "migrated_out",
            "actor_id": actor_id,
            "former_role": role.value,
            "rift_level": self.rift.level,
            "carried_core_available": actor_id in self.carried_cores,
        }

    def member_powers(self, user_id: str) -> dict | None:
        p = self.power_ledger.members.get(user_id)
        return p.to_dict() if p else None

    def submit_mutation(
        self,
        actor_id: str,
        object_id: str,
        operation: str,
        *,
        property_name: str = "heat_intensity",
        value: float | None = None,
        factor: float = 1.0,
        delta: float = 0.0,
        text_value: str = "",
        creativity_score: float = 1.0,
    ) -> MutationResult:
        """구성원이 에리어 오브젝트를 변형 — 펄스에 맞춰 반영."""
        if actor_id not in self.members:
            return MutationResult(False, operation, object_id, reason="not_a_member")

        role = self.role_of(actor_id)
        perms = permissions_for(role)
        op = MutationOp.from_str(operation)

        if object_id not in self.world.state.objects:
            return MutationResult(False, operation, object_id, reason="object_not_found")

        target = self.world.state.objects[object_id]
        if not object_in_area(target, self.area_id):
            return MutationResult(False, operation, object_id, reason="object_not_in_area")

        allowed, reason = can_actor_mutate(actor_id, role, perms, target, op)
        if not allowed:
            return MutationResult(False, operation, object_id, reason=reason)

        mutation = PendingMutation(
            actor_id=actor_id,
            object_id=object_id,
            operation=op,
            property_name=property_name,
            value=value,
            factor=min(factor, perms.max_modify_factor) if op == MutationOp.GROW else factor,
            delta=delta,
            text_value=text_value,
            creativity_score=creativity_score,
        )

        if self.world.policy.pulse_interval_sec <= 0:
            return self._apply_mutation_now(mutation, perms)

        if not self.world._pending and self.world.policy.pulse_interval_sec > 0:
            self.world._pulse_anchor_at = self.world._clock()

        self._pending_mutations.append(mutation)
        return MutationResult(
            True,
            operation,
            object_id,
            reason="mutation_queued_for_pulse",
            queued=True,
        )

    def advance_pulse(self, *, force: bool = False) -> PulseResult:
        pulse = self.world.advance_pulse(force=force)
        if pulse.advanced and self.activity is not None:
            humans = {
                r.creator_id.split("|")[0]
                for r in pulse.results
                if r.ok and is_human_member(self, r.creator_id.split("|")[0])
            }
            self.activity.record_pulse_collab(humans)
        self._finalize_unconfirmed_objects()
        mutation_results = self._flush_mutations()
        if mutation_results or pulse.advanced:
            self._refresh_economy()
        if mutation_results:
            pulse.reason = f"{pulse.reason};mutations={len(mutation_results)}"
        return pulse

    def maybe_advance_pulse(self) -> PulseResult:
        pulse = self.world.maybe_advance_pulse()
        if pulse.advanced and self.activity is not None:
            humans = {
                r.creator_id.split("|")[0]
                for r in pulse.results
                if r.ok and is_human_member(self, r.creator_id.split("|")[0])
            }
            self.activity.record_pulse_collab(humans)
        self._finalize_unconfirmed_objects()
        mutation_results = self._flush_mutations()
        if pulse.advanced or mutation_results:
            self._refresh_economy()
        return pulse

    def to_public_dict(self) -> dict:
        world_pub = self.world.to_public_dict()
        return {
            "area_id": self.area_id,
            "label": self.label,
            "founder_id": self.founder_id,
            "mode": self.mode.value,
            "laws": self.laws.to_dict(),
            "economy": self.economy.to_dict(),
            "members": {k: v.value for k, v in self.members.items()},
            "member_count": len(self.members),
            "pending_mutations": len(self._pending_mutations),
            "pending_proposals": self.pending_proposals(),
            "consensus_policy": self.consensus.policy.to_dict(),
            "powers": self.power_ledger.to_dict(),
            "rift": self.rift.to_dict(),
            "carried_cores": {k: v.to_dict() for k, v in self.carried_cores.items()},
            "extent_bonus": round(self.extent_bonus, 2),
            "area_extent": round(self.area_extent(), 2),
            "npcs": {k: v.to_dict() for k, v in self.npcs.items()},
            "runtime_rules": (
                self._system_runtime.merged_rules().to_dict()
                if self._system_runtime is not None else {}
            ),
            "created_at": self.created_at,
            "world": world_pub,
        }

    def _mode_allows_creation(self, role: ContributorRole) -> bool:
        if self.mode == SimulationMode.ADVENTURE:
            return role in (ContributorRole.FOUNDER, ContributorRole.COLLABORATOR)
        if self.mode == SimulationMode.CREATION:
            return role in (ContributorRole.FOUNDER, ContributorRole.COLLABORATOR)
        return role != ContributorRole.OBSERVER

    def _tag_object_with_area(self, obj: CreativeObject) -> None:
        if obj.get_property("area_id") is None:
            obj.properties.append(
                PropertyDef(name="area_id", value=0.0, unit=self.area_id)
            )

    def _refresh_economy(self) -> None:
        self.economy.refresh(
            object_count=len(self.world.state.objects),
            contributor_count=len(self.members),
            energy_pool=self.world.state.energy_pool,
            tick=self.world.state.tick,
        )

    def _apply_mutation_now(
        self, mutation: PendingMutation, perms: RolePermissions,
    ) -> MutationResult:
        if mutation.operation == MutationOp.DESTROY:
            return self._apply_powered_destroy(mutation)

        result = apply_mutation(
            self.world.state,
            self.world.gate,
            mutation,
            self.laws,
            perms.max_heat_intensity,
            self.area_id,
        )
        if result.ok and result.operation != MutationOp.DESTROY.value:
            obj = self.world.state.objects.get(mutation.object_id)
            if obj:
                mark_co_creator(obj, mutation.actor_id)
        self._refresh_economy()
        return result

    def apply_cross_area_destroy(
        self,
        actor_id: str,
        object_id: str,
        *,
        attacker_area: CreatedArea,
        attacker_extent: float,
        target_extent: float,
        siege_cross_multiplier: float = 1.0,
    ) -> MutationResult:
        """적대 관계 — 타 에리어 오브젝트 파괴."""
        from cpow_engine.areas.dominance import dominance_ratio

        obj = self.world.state.objects.get(object_id)
        if obj is None:
            return MutationResult(
                False, "destroy", object_id, reason="object_not_found",
            )
        if not object_in_area(obj, self.area_id):
            return MutationResult(
                False, "destroy", object_id, reason="object_not_in_area",
            )

        ratio = dominance_ratio(attacker_extent, target_extent)
        cross_scale = (1.0 / max(ratio, 0.15)) * max(0.4, siege_cross_multiplier)
        runtime = self._system_runtime or attacker_area._system_runtime
        if runtime is not None:
            cross_scale *= runtime.cross_destroy_scale()
            destroy_check = runtime.check_destroy_allowed(actor_id)
            if not destroy_check.ok:
                return MutationResult(
                    False, "destroy", object_id, reason=destroy_check.reason,
                )

        powers = attacker_area.power_ledger.get_or_create(actor_id)
        penalty_mult = runtime.penalty_multiplier() if runtime is not None else 1.0
        attempt = attempt_powered_destroy(
            powers,
            obj,
            self.rift,
            area_extent=self.area_extent(),
            cross_area_scale=cross_scale,
            penalty_multiplier=penalty_mult,
        )
        if not attempt.ok:
            return MutationResult(
                False,
                "destroy",
                object_id,
                reason=attempt.reason,
                durability_required=attempt.durability_required,
            )

        released = apply_destroy(
            self.world.state,
            object_id,
            actor_id,
            self.area_id,
        )
        if runtime is not None:
            runtime.record_destroy(actor_id)
        self._refresh_economy()
        return MutationResult(
            True,
            "destroy",
            object_id,
            reason="cross_area_destroyed",
            energy_delta=released,
            durability_required=attempt.durability_required,
            destruction_spent=attempt.destruction_spent,
            penalty_applied=attempt.penalty_applied,
            rift_level=float(attempt.rift.get("rift_level", 0)) if attempt.rift else 0.0,
            monsters_attacking=attempt.monsters_attacking,
        )

    def _apply_powered_destroy(self, mutation: PendingMutation) -> MutationResult:
        obj = self.world.state.objects.get(mutation.object_id)
        if obj is None:
            return MutationResult(
                False, "destroy", mutation.object_id, reason="object_not_found",
            )

        if self._system_runtime is not None:
            destroy_check = self._system_runtime.check_destroy_allowed(mutation.actor_id)
            if not destroy_check.ok:
                return MutationResult(
                    False,
                    "destroy",
                    mutation.object_id,
                    reason=destroy_check.reason,
                )

        powers = self.power_ledger.get_or_create(mutation.actor_id)
        penalty_mult = (
            self._system_runtime.penalty_multiplier()
            if self._system_runtime is not None else 1.0
        )
        attempt = attempt_powered_destroy(
            powers,
            obj,
            self.rift,
            area_extent=self.area_extent(),
            penalty_multiplier=penalty_mult,
        )
        if not attempt.ok:
            return MutationResult(
                False,
                "destroy",
                mutation.object_id,
                reason=attempt.reason,
                durability_required=attempt.durability_required,
            )

        released = apply_destroy(
            self.world.state,
            mutation.object_id,
            mutation.actor_id,
            self.area_id,
        )
        if self._system_runtime is not None:
            self._system_runtime.record_destroy(mutation.actor_id)
        self._refresh_economy()
        return MutationResult(
            True,
            "destroy",
            mutation.object_id,
            reason="destroyed",
            energy_delta=released,
            durability_required=attempt.durability_required,
            destruction_spent=attempt.destruction_spent,
            penalty_applied=attempt.penalty_applied,
            rift_level=float(attempt.rift.get("rift_level", 0)) if attempt.rift else 0.0,
            monsters_attacking=attempt.monsters_attacking,
        )

    def _finalize_confirmed_creation(
        self,
        creator_id: str,
        obj: CreativeObject,
        *,
        creation_type: str,
        pre_spent: float | None = None,
        power_ledger_source: PowerLedger | None = None,
    ) -> tuple[bool, float]:
        ledger = power_ledger_source or self.power_ledger
        is_material = creation_type.lower() == "material"
        heat = obj.get_property("heat_intensity")
        heat_val = heat.value if heat else 0.0
        cost = creation_cost_for_object(heat_val, is_material=is_material)
        is_core = obj.get_property("area_seed") is not None
        is_facility = obj.get_property("is_core_facility") is not None

        if pre_spent is not None:
            spend = pre_spent
            redeemed = 0.0
        else:
            powers = ledger.get_or_create(creator_id)
            if not is_core:
                projected = compute_durability(
                    cost,
                    is_core=is_core,
                    is_facility=is_facility or is_core,
                    heat_intensity=heat_val,
                )
                gate = max_object_durability_gate(
                    extent=self.area_extent(),
                    destruction_gauge_max=powers.destruction_gauge_max,
                    creation_data_score=powers.creation_data_score,
                )
                if projected > gate + 1e-6:
                    return False, 0.0

            spend = powers.resolve_creation_spend(cost)
            if spend <= 0.0 or not powers.spend_creation(spend):
                return False, 0.0
            redeemed = powers.redeem_penalty_with_creation(spend)

        stamp_creation_powers(
            obj,
            spend,
            is_core=is_core,
            is_facility=is_facility or is_core,
        )
        self._record_creation_activity(
            creator_id,
            obj,
            invested=spend,
            is_npc_delegate=(
                creator_id in self.npcs or is_npc_creation(obj)
            ),
        )
        return True, redeemed

    def _record_creation_activity(
        self,
        creator_id: str,
        obj: CreativeObject,
        *,
        invested: float,
        is_npc_delegate: bool,
    ) -> None:
        if self.activity is None:
            self.activity = AreaActivityTracker(area_id=self.area_id)
        if is_npc_delegate or creator_id in self.npcs or is_npc_creation(obj):
            self.activity.record_npc_creation()
            return
        if not is_human_member(self, creator_id):
            return
        self.activity.record_human_creation(creator_id, invested=invested)
        if "|" in (obj.creator_id or ""):
            for part in obj.creator_id.split("|"):
                if part != creator_id and is_human_member(self, part):
                    self.activity.record_co_creation(part)

    def _finalize_unconfirmed_objects(self) -> None:
        for obj in list(self.world.state.objects.values()):
            if is_confirmed(obj):
                continue
            creator = (obj.creator_id or "unknown").split("|")[0]
            if creator not in self.members:
                continue
            ctype = "material" if obj.get_property("material_type") else "heat"
            if not self._finalize_confirmed_creation(
                creator, obj, creation_type=ctype,
            )[0]:
                self.world.state.objects.pop(obj.id, None)

    def _flush_mutations(self) -> list[MutationResult]:
        if not self._pending_mutations:
            return []
        results: list[MutationResult] = []
        pending = list(self._pending_mutations)
        self._pending_mutations.clear()
        for mutation in pending:
            perms = permissions_for(self.role_of(mutation.actor_id))
            results.append(self._apply_mutation_now(mutation, perms))
        return results


def found_area(
    founder_id: str,
    label: str,
    *,
    mode: SimulationMode = SimulationMode.CREATION_ADVENTURE,
    template: str | None = None,
    laws: AreaLawSet | None = None,
) -> CreatedArea:
    """초기 창조자가 새 에리어를 연다."""
    area_id = f"area_{uuid.uuid4().hex[:10]}"
    templates = load_area_templates()
    template_key = template or template_for_mode(mode)
    law_set = laws or templates.get(template_key, AreaLawSet(name=label))
    law_set = AreaLawSet.from_dict({**law_set.to_dict(), "name": label})

    policy = law_set.apply_collab_policy()
    world = CollaborativeWorld(area_id, policy=policy)
    area = CreatedArea(
        area_id=area_id,
        label=label,
        founder_id=founder_id,
        mode=mode,
        laws=law_set,
        world=world,
    )
    area.consensus = ConsensusGate(law_set.consensus)
    area.join(founder_id)

    seed = create_heat_object(
        founder_id,
        f"{label} 심장",
        heat_intensity=law_set.heat_baseline,
    )
    seed.properties.append(
        PropertyDef(name="area_seed", value=1.0, unit="founding_core")
    )
    area.submit_creation(founder_id, seed, creation_type="heat", bypass_consensus=True)
    area.world.advance_pulse(force=True)
    obj = next(iter(area.world.state.objects.values()), None)
    if obj:
        stamp_creation_powers(
            obj,
            creation_cost_for_object(law_set.heat_baseline),
            is_core=True,
        )
    area._refresh_economy()
    return area
