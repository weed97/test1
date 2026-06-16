"""창조된 에리어 — 모드·역할·법칙·협동 월드 통합."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from cpow_engine.areas.economy import RegionalEconomy
from cpow_engine.areas.laws import AreaLawSet, load_area_templates, template_for_mode
from cpow_engine.areas.modes import SimulationMode
from cpow_engine.areas.roles import (
    ContributorRole,
    default_role_for_mode,
    permissions_for,
)
from cpow_engine.collab import CollaborativeWorld, WorldSubmissionResult
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
    ) -> WorldSubmissionResult:
        role = self.role_of(creator_id)
        perms = permissions_for(role)

        if not self._mode_allows_creation(role):
            return WorldSubmissionResult(False, reason="mode_blocks_creation")

        if not perms.can_create_objects and not (
            self.mode == SimulationMode.CREATION_ADVENTURE and perms.can_adventure
        ):
            return WorldSubmissionResult(False, reason="role_cannot_create")

        is_founding_seed = obj.get_property("area_seed") is not None
        if not is_founding_seed and not self.laws.allows_creation_type(creation_type):
            return WorldSubmissionResult(False, reason="creation_type_not_allowed_in_area")

        self._tag_object_with_area(obj)
        self._clamp_object_to_laws(obj, perms.max_heat_intensity)

        result = self.world.submit_creation(
            creator_id, obj, creativity_score=creativity_score,
        )
        self._refresh_economy()
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
            return AdventureResult(
                True, action_type, reason="contributed",
                tick=self.world.state.tick,
            )

        return AdventureResult(False, action_type, reason="unknown_adventure_action")

    def advance_pulse(self, *, force: bool = False) -> PulseResult:
        pulse = self.world.advance_pulse(force=force)
        if pulse.advanced:
            self._refresh_economy()
        return pulse

    def maybe_advance_pulse(self) -> PulseResult:
        pulse = self.world.maybe_advance_pulse()
        if pulse.advanced:
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

    def _clamp_object_to_laws(self, obj: CreativeObject, role_max: float) -> None:
        heat = obj.get_property("heat_intensity")
        if heat is not None:
            heat.value = self.laws.clamp_heat(heat.value, role_max)

    def _refresh_economy(self) -> None:
        self.economy.refresh(
            object_count=len(self.world.state.objects),
            contributor_count=len(self.members),
            energy_pool=self.world.state.energy_pool,
            tick=self.world.state.tick,
        )


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
    area.join(founder_id)

    seed = create_heat_object(
        founder_id,
        f"{label} 심장",
        heat_intensity=law_set.heat_baseline,
    )
    seed.properties.append(
        PropertyDef(name="area_seed", value=1.0, unit="founding_core")
    )
    area.submit_creation(founder_id, seed, creation_type="heat")
    area.world.advance_pulse(force=True)
    area._refresh_economy()
    return area
