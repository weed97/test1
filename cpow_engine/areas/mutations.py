"""에리어 오브젝트 변형 — 구성원의 수정·성장·축소·파괴."""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from enum import Enum

from cpow_engine.areas.laws import AreaLawSet
from cpow_engine.areas.roles import ContributorRole, RolePermissions
from cpow_engine.collab.noise_gate import ChangeVerdict, NoiseGate
from cpow_engine.models import ActionRecord, CreativeObject, PropertyDef, SimulationState


class MutationOp(str, Enum):
    MODIFY = "modify"
    GROW = "grow"
    SHRINK = "shrink"
    SET = "set"
    DESTROY = "destroy"
    RENAME = "rename"

    @classmethod
    def from_str(cls, value: str) -> MutationOp:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.MODIFY


@dataclass
class PendingMutation:
    actor_id: str
    object_id: str
    operation: MutationOp
    property_name: str = "heat_intensity"
    value: float | None = None
    factor: float = 1.0
    delta: float = 0.0
    text_value: str = ""
    creativity_score: float = 1.0
    queued_at: float = field(default_factory=time.monotonic)


@dataclass
class MutationResult:
    ok: bool
    operation: str = ""
    object_id: str = ""
    reason: str = ""
    queued: bool = False
    previous_value: float | None = None
    new_value: float | None = None
    verdict: ChangeVerdict | None = None
    energy_delta: float = 0.0


def is_founding_core(obj: CreativeObject) -> bool:
    return obj.get_property("area_seed") is not None


def object_in_area(obj: CreativeObject, area_id: str) -> bool:
    area_prop = obj.get_property("area_id")
    if area_prop is None:
        return True
    return area_prop.unit == area_id or area_prop.name == area_id


def can_actor_mutate(
    actor_id: str,
    role: ContributorRole,
    perms: RolePermissions,
    obj: CreativeObject,
    operation: MutationOp,
) -> tuple[bool, str]:
    if not perms.can_modify_objects and operation != MutationOp.DESTROY:
        if not (perms.can_destroy_objects and operation == MutationOp.DESTROY):
            return False, "role_cannot_mutate"

    if operation == MutationOp.DESTROY:
        if not perms.can_destroy_objects:
            return False, "role_cannot_destroy"
        if is_founding_core(obj) and not perms.can_destroy_founding_core:
            return False, "cannot_destroy_founding_core"
        return True, "ok"

    if role == ContributorRole.ADVENTURER:
        owners = set(obj.creator_id.split("|")) if obj.creator_id else set()
        if actor_id not in owners:
            return False, "adventurer_can_only_mutate_own"

    return True, "ok"


def compute_new_value(
    current: float,
    operation: MutationOp,
    *,
    value: float | None = None,
    factor: float = 1.0,
    delta: float = 0.0,
    max_factor: float = 1.5,
    min_factor: float = 0.5,
) -> float:
    if operation == MutationOp.SET and value is not None:
        return value
    if operation == MutationOp.GROW:
        f = min(factor if factor != 1.0 else 1.15, max_factor)
        return current * f
    if operation == MutationOp.SHRINK:
        f = max(factor if factor != 1.0 else 0.85, min_factor)
        return current * f
    if operation == MutationOp.MODIFY:
        return current + delta
    return current


def build_mutated_object(
    existing: CreativeObject,
    mutation: PendingMutation,
    laws: AreaLawSet,
    role_max: float,
) -> CreativeObject | None:
    if mutation.operation == MutationOp.DESTROY:
        return None

    updated = copy.deepcopy(existing)

    if mutation.operation == MutationOp.RENAME:
        updated.label = mutation.text_value or updated.label
        return updated

    prop_name = mutation.property_name or "heat_intensity"
    prop = updated.get_property(prop_name)
    if prop is None:
        if prop_name == "scale":
            prop = PropertyDef(name="scale", value=1.0, unit="ratio")
            updated.properties.append(prop)
        else:
            return updated

    old_val = prop.value
    new_val = compute_new_value(
        old_val,
        mutation.operation,
        value=mutation.value,
        factor=mutation.factor,
        delta=mutation.delta,
    )

    if prop_name == "heat_intensity":
        new_val = laws.clamp_heat(new_val, role_max)
        new_val = max(0.0, new_val)

    prop.value = new_val
    return updated


def apply_destroy(
    state: SimulationState,
    object_id: str,
    actor_id: str,
    area_id: str,
) -> float:
    obj = state.objects.pop(object_id)
    for other in state.objects.values():
        if object_id in other.connections:
            other.connections.remove(object_id)

    released = 0.0
    heat = obj.get_property("heat_intensity")
    if heat:
        released = heat.value * 0.05
    scale = obj.get_property("scale")
    if scale:
        released += scale.value * 2.0

    state.energy_pool += released
    state.entropy += 0.01
    state.action_log.append(ActionRecord(
        actor_id=actor_id,
        action_type="area_destroy_object",
        payload={"area_id": area_id, "object_id": object_id, "label": obj.label},
    ))
    return released


def apply_mutation(
    state: SimulationState,
    gate: NoiseGate,
    mutation: PendingMutation,
    laws: AreaLawSet,
    role_max: float,
    area_id: str,
) -> MutationResult:
    if mutation.object_id not in state.objects:
        return MutationResult(
            False, mutation.operation.value, mutation.object_id,
            reason="object_not_found",
        )

    existing = state.objects[mutation.object_id]

    if mutation.operation == MutationOp.DESTROY:
        released = apply_destroy(state, mutation.object_id, mutation.actor_id, area_id)
        return MutationResult(
            True,
            mutation.operation.value,
            mutation.object_id,
            reason="destroyed",
            energy_delta=released,
        )

    mutated = build_mutated_object(existing, mutation, laws, role_max)
    if mutated is None:
        return MutationResult(
            False, mutation.operation.value, mutation.object_id,
            reason="mutation_failed",
        )

    prop_name = mutation.property_name or "heat_intensity"
    prev_prop = existing.get_property(prop_name)
    new_prop = mutated.get_property(prop_name)
    prev_val = prev_prop.value if prev_prop else None
    new_val = new_prop.value if new_prop else None
    verdict: ChangeVerdict | None = None

    if mutation.operation != MutationOp.RENAME:
        verdict = gate.evaluate_update(
            existing, mutated, creativity_score=mutation.creativity_score,
        )
        if not verdict.accepted or verdict.object is None:
            return MutationResult(
                False,
                mutation.operation.value,
                mutation.object_id,
                reason=verdict.reason,
                previous_value=prev_val,
                verdict=verdict,
            )
        mutated = verdict.object

    mark_co_creator(mutated, mutation.actor_id)
    state.objects[mutation.object_id] = mutated
    state.version += 1
    state.action_log.append(ActionRecord(
        actor_id=mutation.actor_id,
        action_type="area_mutate_object",
        payload={
            "area_id": area_id,
            "object_id": mutation.object_id,
            "operation": mutation.operation.value,
            "property": prop_name,
        },
    ))

    return MutationResult(
        True,
        mutation.operation.value,
        mutation.object_id,
        reason="mutated",
        previous_value=prev_val,
        new_value=new_val,
        verdict=verdict,
    )


def mark_co_creator(obj: CreativeObject, actor_id: str) -> None:
    creators = {c for c in obj.creator_id.split("|") if c}
    creators.add(actor_id)
    obj.creator_id = "|".join(sorted(creators))
