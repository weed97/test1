"""노이즈 게이트 — 과도한 변화 감쇄·거부."""

from __future__ import annotations

import copy
from dataclasses import dataclass

from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.models import CreativeObject, PropertyDef, SimulationState


@dataclass
class ChangeVerdict:
    accepted: bool
    object: CreativeObject | None
    magnitude: float
    applied_damping: float
    reason: str = ""


class NoiseGate:
    """창조/수정의 '변화량'을 측정하고 감쇄."""

    def __init__(self, policy: CollabPolicy) -> None:
        self.policy = policy

    def evaluate_new(
        self, obj: CreativeObject, state: SimulationState
    ) -> ChangeVerdict:
        magnitude = self._new_object_magnitude(obj, state)
        damp = self.policy.effective_damp(magnitude)
        damped = self._damp_new_object(obj, damp, state)
        return ChangeVerdict(
            True, damped, magnitude, damp,
            reason="new_object_damped" if magnitude > self.policy.noise_threshold else "ok",
        )

    def evaluate_update(
        self,
        existing: CreativeObject,
        incoming: CreativeObject,
        *,
        creativity_score: float = 1.0,
    ) -> ChangeVerdict:
        magnitude = self._update_magnitude(existing, incoming)
        if magnitude > self.policy.noise_threshold:
            if creativity_score < self.policy.min_creativity_for_large_change:
                damp = self.policy.effective_damp(magnitude) * 0.5
            else:
                damp = self.policy.effective_damp(magnitude)
        else:
            damp = self.policy.damp_factor

        merged = self._damp_merge(existing, incoming, damp)
        if magnitude > self.policy.large_change_multiplier:
            return ChangeVerdict(
                False, None, magnitude, damp,
                reason="change_too_extreme",
            )
        return ChangeVerdict(
            True, merged, magnitude, damp,
            reason="update_damped" if magnitude > self.policy.noise_threshold else "ok",
        )

    def _new_object_magnitude(
        self, obj: CreativeObject, state: SimulationState
    ) -> float:
        scores: list[float] = []
        for prop in obj.properties:
            if prop.name == "heat_intensity":
                baseline = self._world_avg_heat(state)
                delta = abs(prop.value - baseline)
                scores.append(
                    min(1.0, delta / max(self.policy.max_absolute_heat_delta * 2, 1.0))
                )
            else:
                scores.append(min(1.0, abs(prop.value) / 200.0))
        if not scores:
            return 0.2
        return max(scores)

    def _update_magnitude(
        self, existing: CreativeObject, incoming: CreativeObject
    ) -> float:
        max_ratio = 0.0
        existing_map = {p.name: p.value for p in existing.properties}
        for prop in incoming.properties:
            old = existing_map.get(prop.name, 0.0)
            if old == 0.0:
                rel = min(1.0, abs(prop.value) / max(self.policy.max_absolute_heat_delta, 1.0))
            else:
                rel = abs(prop.value - old) / abs(old)
            max_ratio = max(max_ratio, rel)
        return min(1.0, max_ratio / self.policy.max_relative_change)

    def _world_avg_heat(self, state: SimulationState) -> float:
        heats = [
            p.value
            for o in state.objects.values()
            for p in o.properties
            if p.name == "heat_intensity"
        ]
        if not heats:
            return 50.0
        return sum(heats) / len(heats)

    def _damp_new_object(
        self, obj: CreativeObject, damp: float, state: SimulationState
    ) -> CreativeObject:
        result = copy.deepcopy(obj)
        baseline_heat = self._world_avg_heat(state)
        for prop in result.properties:
            if prop.name == "heat_intensity":
                target = prop.value
                prop.value = baseline_heat + (target - baseline_heat) * damp
                prop.value = self._clamp_heat_delta(baseline_heat, prop.value)
        return result

    def _damp_merge(
        self, existing: CreativeObject, incoming: CreativeObject, damp: float
    ) -> CreativeObject:
        prop_map: dict[str, float] = {p.name: p.value for p in existing.properties}
        unit_map: dict[str, str] = {p.name: p.unit for p in existing.properties}

        for prop in incoming.properties:
            old = prop_map.get(prop.name, 0.0)
            prop_map[prop.name] = old + (prop.value - old) * damp
            unit_map[prop.name] = prop.unit
            if prop.name == "heat_intensity":
                prop_map[prop.name] = self._clamp_heat_delta(old, prop_map[prop.name])

        merged_props = [
            PropertyDef(name=n, value=v, unit=unit_map.get(n, ""))
            for n, v in prop_map.items()
        ]
        creators = {existing.creator_id, incoming.creator_id} - {""}
        return CreativeObject(
            id=existing.id,
            creator_id="|".join(sorted(creators)),
            label=incoming.label or existing.label,
            properties=merged_props,
            connections=list(set(existing.connections) | set(incoming.connections)),
        )

    def _clamp_heat_delta(self, base: float, new_val: float) -> float:
        max_d = self.policy.max_absolute_heat_delta
        return max(base - max_d, min(base + max_d, new_val))
