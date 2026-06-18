"""환경장 물리 — 중력·풍·전역 압력."""

from __future__ import annotations

from cpow_engine.models import CreativeObject, InteractionResult
from cpow_engine.physics.balance_config import PhysicsBalanceConfig, load_physics_balance_config
from cpow_engine.physics.properties import (
    clamp_delta,
    fluid_pressure_of,
    heat_of,
    mass_of,
    radiation_of,
    set_prop,
    structural_stress_of,
)


class FieldPhysics:
    """연결 그래프 밖 전역 장 효과."""

    def __init__(self, config: PhysicsBalanceConfig | None = None) -> None:
        self.cfg = config or load_physics_balance_config()

    def resolve(
        self,
        objects: dict[str, CreativeObject],
        *,
        energy_pool: float = 0.0,
    ) -> list[InteractionResult]:
        if not self.cfg.field_physics_enabled or not objects:
            return []

        results: list[InteractionResult] = []
        obj_list = list(objects.values())
        results.extend(self._gravity(obj_list))
        results.extend(self._wind(obj_list, energy_pool))
        results.extend(self._ambient_pressure(obj_list, energy_pool))
        return results

    def _gravity(self, obj_list: list[CreativeObject]) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        g = self.cfg.gravity_strength
        for obj in obj_list:
            mass = mass_of(obj)
            if mass < 0.01:
                continue
            load = mass * g
            results.append(
                InteractionResult(
                    source_id=obj.id,
                    target_id=None,
                    effect_type="gravity",
                    magnitude=load,
                    energy_delta=-load * 0.05,
                    metadata={"field": "gravity"},
                )
            )
        return results

    def _wind(
        self,
        obj_list: list[CreativeObject],
        energy_pool: float,
    ) -> list[InteractionResult]:
        if self.cfg.wind_strength <= 0:
            return []
        results: list[InteractionResult] = []
        bias = self.cfg.wind_strength * (1.0 + energy_pool * 0.0001)
        for obj in obj_list:
            if radiation_of(obj) < 1.0 and heat_of(obj) < 1.0:
                continue
            cooling = bias * 0.3
            results.append(
                InteractionResult(
                    source_id=obj.id,
                    target_id=None,
                    effect_type="wind_cooling",
                    magnitude=cooling,
                    energy_delta=-cooling * 0.2,
                    metadata={"field": "wind"},
                )
            )
        return results

    def _ambient_pressure(
        self,
        obj_list: list[CreativeObject],
        energy_pool: float,
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        ambient_p = self.cfg.ambient_pressure_base + energy_pool * 0.001
        for obj in obj_list:
            if obj.get_property("fluid_pressure") is None:
                continue
            current = fluid_pressure_of(obj)
            delta = (ambient_p - current) * self.cfg.pressure_coupling
            if abs(delta) < 0.05:
                continue
            results.append(
                InteractionResult(
                    source_id=obj.id,
                    target_id=None,
                    effect_type="ambient_pressure",
                    magnitude=abs(delta),
                    energy_delta=delta * 0.15,
                    metadata={"field": "pressure", "ambient": ambient_p},
                )
            )
        return results

    def apply_feedback(
        self,
        objects: dict[str, CreativeObject],
        interactions: list[InteractionResult],
    ) -> int:
        cap = self.cfg.max_property_delta_per_tick
        n = 0
        for ix in interactions:
            if ix.source_id not in objects:
                continue
            obj = objects[ix.source_id]
            if ix.effect_type == "gravity":
                set_prop(
                    obj,
                    "structural_stress",
                    structural_stress_of(obj) + clamp_delta(ix.magnitude, cap),
                    unit="mpa",
                )
                n += 1
            elif ix.effect_type == "wind_cooling":
                heat_prop = obj.get_property("heat_intensity")
                if heat_prop is not None:
                    heat_prop.value = max(
                        0.0,
                        heat_prop.value - clamp_delta(ix.magnitude, cap),
                    )
                    n += 1
            elif ix.effect_type == "ambient_pressure":
                set_prop(
                    obj,
                    "fluid_pressure",
                    fluid_pressure_of(obj) + clamp_delta(ix.energy_delta, cap),
                    unit="kpa",
                )
                n += 1
        return n
