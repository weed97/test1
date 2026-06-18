"""에리어 레지스트리 — 창조·모험 월드 목록."""

from __future__ import annotations

from cpow_engine.areas.area import CreatedArea, found_area
from cpow_engine.areas.diplomacy import (
    DiplomaticStance,
    DiplomacyLedger,
    can_cooperative_create,
    can_cross_area_combat,
    observer_can_intervene_cross_area,
)
from cpow_engine.areas.governance import GovernanceLedger, GovernancePolicy
from cpow_engine.areas.governance_eligibility import validate_governance_area_eligibility
from cpow_engine.areas.laws import AreaLawSet
from cpow_engine.areas.member_identity import MemberIdentityRegistry
from cpow_engine.areas.siege import (
    SiegeLedger,
    area_fortification_strength,
    siege_cross_scale_modifier,
)
from cpow_engine.areas.system_runtime import SystemRuntime
from cpow_engine.areas.modes import SimulationMode
from cpow_engine.areas.roles import ContributorRole
from cpow_engine.collab import WorldSubmissionResult
from cpow_engine.models import CreativeObject


class AreaRegistry:
    def __init__(self, *, governance_policy: GovernancePolicy | None = None) -> None:
        self._areas: dict[str, CreatedArea] = {}
        self.diplomacy: DiplomacyLedger = DiplomacyLedger()
        self.siege: SiegeLedger = SiegeLedger()
        self.system_runtime = SystemRuntime()
        resolved_policy = governance_policy or GovernancePolicy()
        self.identity = MemberIdentityRegistry(resolved_policy.identity)
        self.governance = GovernanceLedger(
            resolved_policy,
            runtime=self.system_runtime,
            on_enact=self._on_system_enacted,
            identity=self.identity,
        )

    def _on_system_enacted(self, system) -> None:
        self.system_runtime.register(system)
        for area in self._areas.values():
            area.refresh_runtime_policy()

    def _sync_member_powers(self, area: CreatedArea, user_id: str) -> None:
        powers = area.power_ledger.members.get(user_id)
        if powers is not None:
            self.governance.sync_member(user_id, powers, area.area_id)

    def found(
        self,
        founder_id: str,
        label: str,
        *,
        mode: SimulationMode = SimulationMode.CREATION_ADVENTURE,
        template: str | None = None,
        laws: AreaLawSet | None = None,
    ) -> CreatedArea:
        area = found_area(
            founder_id,
            label,
            mode=mode,
            template=template,
            laws=laws,
        )
        self._areas[area.area_id] = area
        area.attach_system_runtime(self.system_runtime)
        self._sync_member_powers(area, founder_id)
        return area

    def get(self, area_id: str) -> CreatedArea | None:
        return self._areas.get(area_id)

    def get_or_raise(self, area_id: str) -> CreatedArea:
        area = self.get(area_id)
        if area is None:
            raise KeyError(f"unknown area: {area_id}")
        return area

    def list_areas(self) -> list[CreatedArea]:
        return list(self._areas.values())

    def join(
        self,
        area_id: str,
        creator_id: str,
        *,
        role: ContributorRole | None = None,
    ) -> CreatedArea:
        area = self.get_or_raise(area_id)
        area.join(creator_id, requested_role=role)
        self._sync_member_powers(area, creator_id)
        area.maybe_advance_pulse()
        return area

    def dominance_between(self, area_id_a: str, area_id_b: str) -> dict:
        a = self.get_or_raise(area_id_a)
        b = self.get_or_raise(area_id_b)
        ratio_ab = a.dominance_vs(b)
        ratio_ba = b.dominance_vs(a)
        return {
            "area_a": area_id_a,
            "area_b": area_id_b,
            "extent_a": round(a.area_extent(), 2),
            "extent_b": round(b.area_extent(), 2),
            "a_vs_b": round(ratio_ab, 3),
            "b_vs_a": round(ratio_ba, 3),
            "a_dominated_by_b": ratio_ab < 0.65,
            "b_dominated_by_a": ratio_ba < 0.65,
        }

    def set_diplomatic_stance(
        self,
        area_id: str,
        target_area_id: str,
        stance: str,
        actor_id: str,
    ) -> dict:
        area = self.get_or_raise(area_id)
        self.get_or_raise(target_area_id)
        parsed = DiplomaticStance.from_str(stance)

        if parsed == DiplomaticStance.HOSTILE:
            if actor_id not in area.members:
                return {"ok": False, "reason": "not_a_member"}
            from cpow_engine.areas.area_activity import is_human_member

            if not is_human_member(area, actor_id):
                return {"ok": False, "reason": "npc_cannot_declare_hostile"}
            humans = [m for m in area.members if is_human_member(area, m)]
            if len(humans) < 2:
                return {"ok": False, "reason": "hostile_requires_multiple_humans"}
            pending_list = self.diplomacy.pending_hostile_for(area_id)
            already_pending = any(
                p.get("from_area_id") == area_id
                and p.get("to_area_id") == target_area_id
                for p in pending_list
            )
            if not already_pending and area.role_of(actor_id) != ContributorRole.FOUNDER:
                return {"ok": False, "reason": "founder_must_initiate_hostile"}
            confirmed, pending, reason = self.diplomacy.endorse_hostile(
                area_id,
                target_area_id,
                actor_id,
                min_endorsers=self.governance.policy.min_hostile_endorsers,
            )
            if not confirmed:
                return {
                    "ok": True,
                    "reason": reason,
                    "pending_hostile": pending.to_dict() if pending else None,
                    "resolved_stance": self.diplomacy.resolved_stance(
                        area_id, target_area_id,
                    ).value,
                }
            parsed = DiplomaticStance.HOSTILE
        elif area.role_of(actor_id) != ContributorRole.FOUNDER:
            return {"ok": False, "reason": "founder_only"}

        link = self.diplomacy.declare(
            area_id,
            target_area_id,
            parsed,
            declared_by=actor_id,
        )
        resolved = self.diplomacy.resolved_stance(area_id, target_area_id)
        if resolved == DiplomaticStance.HOSTILE:
            self.siege.on_hostile_declared(area_id, target_area_id)
        return {
            "ok": True,
            "link": link.to_dict(),
            "resolved_stance": resolved.value,
            "siege_active": resolved == DiplomaticStance.HOSTILE,
        }

    def diplomatic_status(self, area_id: str, target_area_id: str) -> dict:
        self.get_or_raise(area_id)
        self.get_or_raise(target_area_id)
        resolved = self.diplomacy.resolved_stance(area_id, target_area_id)
        return {
            "area_id": area_id,
            "target_area_id": target_area_id,
            "resolved_stance": resolved.value,
            "a_to_b": self.diplomacy.direct_stance(area_id, target_area_id).value,
            "b_to_a": self.diplomacy.direct_stance(target_area_id, area_id).value,
            "can_combat": can_cross_area_combat(resolved),
            "can_cooperate": resolved == DiplomaticStance.ALLIANCE,
            "competition_only": resolved == DiplomaticStance.NEUTRAL,
        }

    def cross_area_destroy(
        self,
        attacker_area_id: str,
        actor_id: str,
        target_area_id: str,
        object_id: str,
    ) -> dict:
        stance = self.diplomacy.resolved_stance(attacker_area_id, target_area_id)
        if not can_cross_area_combat(stance):
            return {"ok": False, "reason": "diplomacy_not_hostile"}

        attacker = self.get_or_raise(attacker_area_id)
        target = self.get_or_raise(target_area_id)
        if actor_id not in attacker.members:
            return {"ok": False, "reason": "not_a_member"}

        role = attacker.role_of(actor_id)
        if not observer_can_intervene_cross_area(stance, role):
            return {"ok": False, "reason": "observer_cannot_intervene"}

        result = target.apply_cross_area_destroy(
            actor_id,
            object_id,
            attacker_area=attacker,
            attacker_extent=attacker.area_extent(),
            target_extent=target.area_extent(),
            siege_cross_multiplier=self._siege_cross_multiplier(
                attacker_area_id, target_area_id, target,
            ),
        )
        out = {
            "ok": result.ok,
            "reason": result.reason,
            "operation": result.operation,
            "object_id": result.object_id,
            "durability_required": result.durability_required,
            "destruction_spent": result.destruction_spent,
            "penalty_applied": result.penalty_applied,
            "rift_level": result.rift_level,
            "resolved_stance": stance.value,
        }
        if result.ok:
            contest = self.siege.on_assault(
                attacker_area_id,
                target_area_id,
                actor_id,
                durability_destroyed=float(result.destruction_spent or 0),
            )
            fort = area_fortification_strength(target.world.state.objects)
            out["siege"] = contest.to_dict(
                fortification=fort,
                dominance_ratio=attacker.dominance_vs(target),
            )
        return out

    def _siege_cross_multiplier(
        self,
        attacker_area_id: str,
        defender_area_id: str,
        defender: CreatedArea,
    ) -> float:
        contest = self.siege.get(attacker_area_id, defender_area_id)
        fort = area_fortification_strength(defender.world.state.objects)
        if contest is None:
            return siege_cross_scale_modifier(0.0, fort, 0.0)
        return siege_cross_scale_modifier(
            contest.assault_momentum,
            fort,
            contest.repulse_reserve,
        )

    def repulse_siege(
        self,
        defender_area_id: str,
        attacker_area_id: str,
        actor_id: str,
        *,
        power_spend: float,
    ) -> dict:
        """수성 — 파괴력으로 공성 압력을 밀어냄."""
        stance = self.diplomacy.resolved_stance(attacker_area_id, defender_area_id)
        if not can_cross_area_combat(stance):
            return {"ok": False, "reason": "diplomacy_not_hostile"}

        defender = self.get_or_raise(defender_area_id)
        if actor_id not in defender.members:
            return {"ok": False, "reason": "not_a_member"}

        role = defender.role_of(actor_id)
        if not observer_can_intervene_cross_area(stance, role):
            return {"ok": False, "reason": "observer_cannot_intervene"}

        powers = defender.power_ledger.get_or_create(actor_id)
        if power_spend <= 0:
            return {"ok": False, "reason": "invalid_power_spend"}
        if powers.destruction_gauge < power_spend:
            return {"ok": False, "reason": "insufficient_destruction_power"}
        if not powers.spend_destruction(power_spend):
            return {"ok": False, "reason": "insufficient_destruction_power"}

        contest = self.siege.on_repulse(
            attacker_area_id,
            defender_area_id,
            actor_id,
            power_spent=power_spend,
        )
        fort = area_fortification_strength(defender.world.state.objects)
        attacker = self.get_or_raise(attacker_area_id)
        return {
            "ok": True,
            "reason": "repulsed",
            "power_spent": power_spend,
            "siege": contest.to_dict(
                fortification=fort,
                dominance_ratio=attacker.dominance_vs(defender),
            ),
            "powers": defender.member_powers(actor_id),
        }

    def siege_between(self, attacker_area_id: str, defender_area_id: str) -> dict:
        self.get_or_raise(attacker_area_id)
        defender = self.get_or_raise(defender_area_id)
        attacker = self.get_or_raise(attacker_area_id)
        contest = self.siege.get(attacker_area_id, defender_area_id)
        fort = area_fortification_strength(defender.world.state.objects)
        stance = self.diplomacy.resolved_stance(attacker_area_id, defender_area_id)
        if contest is None:
            flow_only = {
                "attacker_area_id": attacker_area_id,
                "defender_area_id": defender_area_id,
                "assault_momentum": 0.0,
                "fortification_strength": round(fort, 2),
                "resolved_stance": stance.value,
                "flow": {
                    "flow": "border_tension" if stance == DiplomaticStance.HOSTILE else "peace",
                    "pressure": 0.0,
                    "label": "적대 관계 — 교전 가능" if stance == DiplomaticStance.HOSTILE else "교전 없음",
                },
            }
            return {"ok": True, "siege": flow_only}
        return {
            "ok": True,
            "siege": contest.to_dict(
                fortification=fort,
                dominance_ratio=attacker.dominance_vs(defender),
            ),
            "resolved_stance": stance.value,
        }

    def active_sieges(self, area_id: str) -> dict:
        self.get_or_raise(area_id)
        self.tick_sieges()
        contests = self.siege.contests_for(area_id)
        entries: list[dict] = []
        for contest in contests:
            defender = self.get_or_raise(contest.defender_area_id)
            attacker = self.get_or_raise(contest.attacker_area_id)
            fort = area_fortification_strength(defender.world.state.objects)
            entries.append(
                contest.to_dict(
                    fortification=fort,
                    dominance_ratio=attacker.dominance_vs(defender),
                )
            )
        return {"ok": True, "area_id": area_id, "contests": entries, "count": len(entries)}

    def tick_sieges(self) -> int:
        forts = {
            aid: area_fortification_strength(a.world.state.objects)
            for aid, a in self._areas.items()
        }
        return self.siege.tick(forts)

    def allied_creation(
        self,
        home_area_id: str,
        target_area_id: str,
        creator_id: str,
        obj: CreativeObject,
        *,
        creation_type: str = "heat",
        creativity_score: float = 1.0,
    ) -> WorldSubmissionResult:
        stance = self.diplomacy.resolved_stance(home_area_id, target_area_id)
        home = self.get_or_raise(home_area_id)
        target = self.get_or_raise(target_area_id)

        if creator_id not in home.members:
            return WorldSubmissionResult(False, reason="not_a_member")

        role = home.role_of(creator_id)
        if not can_cooperative_create(stance, role):
            return WorldSubmissionResult(False, reason="diplomacy_not_allied")
        if not observer_can_intervene_cross_area(stance, role):
            return WorldSubmissionResult(False, reason="observer_cannot_intervene")

        return target.submit_creation(
            creator_id,
            obj,
            creation_type=creation_type,
            creativity_score=creativity_score,
            bypass_consensus=True,
            allied_home_area=home,
        )

    def register_member_identity(self, user_id: str, person_key: str) -> dict:
        result = self.identity.register(user_id, person_key)
        out = {
            "ok": result.ok,
            "reason": result.reason,
        }
        if result.codes:
            out["codes"] = list(result.codes)
        if result.binding is not None:
            out["identity"] = result.binding.to_public_dict()
        return out

    def member_identity_status(self, user_id: str) -> dict:
        binding = self.identity.binding_for(user_id)
        return {
            "ok": True,
            "verified": binding is not None,
            "identity": binding.to_public_dict() if binding else None,
        }

    def _proposal_participant_ids(self, proposal) -> set[str]:
        return (
            set(proposal.composers)
            | set(proposal.cosponsors)
            | set(proposal.approvals)
            | set(proposal.rejections)
        )

    def _validate_governance_participant(
        self,
        area_id: str,
        user_id: str,
        *,
        proposal=None,
    ) -> dict:
        id_check = self.identity.validate_for_governance(user_id)
        if not id_check.ok:
            return {
                "ok": False,
                "reason": id_check.reason,
                "codes": list(id_check.codes),
            }
        if proposal is not None:
            conflict = self.identity.proposal_person_conflict(
                user_id,
                self._proposal_participant_ids(proposal),
            )
            if not conflict.ok:
                return {
                    "ok": False,
                    "reason": conflict.reason,
                    "codes": list(conflict.codes),
                }
        return self._validate_governance_standing(area_id, user_id)

    def refresh_governance_powers(self) -> None:
        for area in self._areas.values():
            for uid, powers in area.power_ledger.members.items():
                self.governance.sync_member(uid, powers, area.area_id)

    def _validate_governance_standing(
        self,
        area_id: str,
        user_id: str,
    ) -> dict:
        area = self.get(area_id)
        if area is None:
            return {"ok": False, "reason": "unknown_area", "codes": ["area_not_found"]}
        if area.activity is None:
            from cpow_engine.areas.area_activity import AreaActivityTracker
            area.activity = AreaActivityTracker(area_id=area.area_id)
        check = validate_governance_area_eligibility(
            area,
            area.activity,
            user_id,
            policy=self.governance.policy.living_area,
        )
        if not check.ok:
            return {
                "ok": False,
                "reason": check.reason,
                "codes": list(check.codes),
                "vitality": check.vitality,
                "member": check.member,
            }
        return {
            "ok": True,
            "reason": check.reason,
            "vitality": check.vitality,
            "member": check.member,
        }

    def draft_system_proposal(
        self,
        author_id: str,
        *,
        kind: str,
        title: str,
        spec: dict | None = None,
        area_id: str = "",
    ) -> dict:
        self.refresh_governance_powers()
        standing = self._validate_governance_participant(area_id, author_id)
        if not standing["ok"]:
            return standing
        result = self.governance.draft_proposal(
            author_id,
            kind=kind,
            title=title,
            spec=spec,
            area_id=area_id,
        )
        return self._governance_response(result)

    def sign_system_composer(self, proposal_id: str, user_id: str) -> dict:
        self.refresh_governance_powers()
        proposal = self.governance.get_proposal(proposal_id)
        if proposal is None:
            return {"ok": False, "reason": "proposal_not_found", "proposal_id": proposal_id}
        standing = self._validate_governance_participant(
            proposal.origin_area_id, user_id, proposal=proposal,
        )
        if not standing["ok"]:
            return standing
        return self._governance_response(
            self.governance.sign_composer(proposal_id, user_id),
        )

    def cosponsor_system_proposal(self, proposal_id: str, user_id: str) -> dict:
        self.refresh_governance_powers()
        proposal = self.governance.get_proposal(proposal_id)
        if proposal is None:
            return {"ok": False, "reason": "proposal_not_found", "proposal_id": proposal_id}
        standing = self._validate_governance_participant(
            proposal.origin_area_id, user_id, proposal=proposal,
        )
        if not standing["ok"]:
            return standing
        return self._governance_response(
            self.governance.cosponsor(proposal_id, user_id),
        )

    def vote_system_proposal(
        self,
        proposal_id: str,
        user_id: str,
        *,
        approve: bool,
    ) -> dict:
        self.refresh_governance_powers()
        proposal = self.governance.get_proposal(proposal_id)
        if proposal is None:
            return {"ok": False, "reason": "proposal_not_found", "proposal_id": proposal_id}
        standing = self._validate_governance_participant(
            proposal.origin_area_id, user_id, proposal=proposal,
        )
        if not standing["ok"]:
            return standing
        member = standing.get("member", {})
        min_collab = self.governance.policy.min_collab_signals_for_vote
        collab = int(member.get("collab_signals", 0))
        if collab < min_collab:
            return {
                "ok": False,
                "reason": "insufficient_collab_for_vote",
                "codes": ["vote_requires_collaboration"],
                "required_collab_signals": min_collab,
            }
        result = self.governance.vote(proposal_id, user_id, approve=approve)
        return self._governance_response(result)

    def tick_governance(self) -> dict:
        changed = self.governance.tick()
        return {
            "ok": True,
            "phase_changes": changed,
            "announcements": self.governance.announcements(),
            "pending": self.governance.pending_proposals(),
        }

    def governance_state(self) -> dict:
        self.refresh_governance_powers()
        return {
            "ok": True,
            "policy": self.governance.policy.to_dict(),
            "member_count": self.governance.member_count(),
            "eligible_voters": sum(
                self.governance.eligible_voter_count(a.area_id)
                for a in self._areas.values()
            ),
            "pending": self.governance.pending_proposals(),
            "announcements": self.governance.announcements(),
            "enacted": self.governance.enacted_systems(),
            "runtime_rules": self.system_runtime.merged_rules().to_dict(),
            "runtime_enacted": self.system_runtime.enacted_systems(),
            "identity_verified_count": self.identity.verified_count(),
        }

    def _governance_response(self, result) -> dict:
        out = {
            "ok": result.ok,
            "reason": result.reason,
            "proposal_id": result.proposal_id,
            "phase": result.phase,
            "enacted": result.enacted,
        }
        if getattr(result, "codes", None):
            out["codes"] = list(result.codes)
        if result.proposal_id:
            proposal = self.governance.get_proposal(result.proposal_id)
            if proposal:
                out["proposal"] = proposal.to_public_dict(
                    self.governance.policy,
                    eligible_voters=self.governance.eligible_voter_count(
                        proposal.origin_area_id,
                    ),
                )
                out["proposal"]["unique_cosponsors_count"] = (
                    self.governance._unique_cosponsor_persons(proposal)
                )
        out["governance"] = {
            "announcements": self.governance.announcements(),
            "enacted": self.governance.enacted_systems(),
            "runtime_rules": self.system_runtime.merged_rules().to_dict(),
        }
        return out
