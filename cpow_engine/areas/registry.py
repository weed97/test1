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
from cpow_engine.areas.modes import SimulationMode
from cpow_engine.areas.roles import ContributorRole
from cpow_engine.collab import WorldSubmissionResult
from cpow_engine.models import CreativeObject


class AreaRegistry:
    def __init__(self, *, governance_policy: GovernancePolicy | None = None) -> None:
        self._areas: dict[str, CreatedArea] = {}
        self.diplomacy: DiplomacyLedger = DiplomacyLedger()
        self.governance: GovernanceLedger = GovernanceLedger(governance_policy)

    def _sync_member_powers(self, area: CreatedArea, user_id: str) -> None:
        powers = area.power_ledger.members.get(user_id)
        if powers is not None:
            self.governance.sync_member(user_id, powers)

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
        if area.role_of(actor_id) != ContributorRole.FOUNDER:
            return {"ok": False, "reason": "founder_only"}
        parsed = DiplomaticStance.from_str(stance)
        link = self.diplomacy.declare(
            area_id,
            target_area_id,
            parsed,
            declared_by=actor_id,
        )
        resolved = self.diplomacy.resolved_stance(area_id, target_area_id)
        return {
            "ok": True,
            "link": link.to_dict(),
            "resolved_stance": resolved.value,
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
        )
        return {
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

    def refresh_governance_powers(self) -> None:
        for area in self._areas.values():
            for uid, powers in area.power_ledger.members.items():
                self.governance.sync_member(uid, powers)

    def draft_system_proposal(
        self,
        author_id: str,
        *,
        kind: str,
        title: str,
        spec: dict | None = None,
    ) -> dict:
        self.refresh_governance_powers()
        result = self.governance.draft_proposal(
            author_id, kind=kind, title=title, spec=spec,
        )
        return self._governance_response(result)

    def sign_system_composer(self, proposal_id: str, user_id: str) -> dict:
        self.refresh_governance_powers()
        return self._governance_response(
            self.governance.sign_composer(proposal_id, user_id),
        )

    def cosponsor_system_proposal(self, proposal_id: str, user_id: str) -> dict:
        self.refresh_governance_powers()
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
            "eligible_voters": self.governance.eligible_voter_count(),
            "pending": self.governance.pending_proposals(),
            "announcements": self.governance.announcements(),
            "enacted": self.governance.enacted_systems(),
        }

    def _governance_response(self, result) -> dict:
        out = {
            "ok": result.ok,
            "reason": result.reason,
            "proposal_id": result.proposal_id,
            "phase": result.phase,
            "enacted": result.enacted,
        }
        if result.proposal_id:
            proposal = self.governance.get_proposal(result.proposal_id)
            if proposal:
                out["proposal"] = proposal.to_public_dict(
                    self.governance.policy,
                    eligible_voters=self.governance.eligible_voter_count(),
                )
        out["governance"] = {
            "announcements": self.governance.announcements(),
            "enacted": self.governance.enacted_systems(),
        }
        return out
