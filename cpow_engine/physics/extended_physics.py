"""확장 물리 상호작용 — 전기·유체·복사·구조 하중."""

from __future__ import annotations

from cpow_engine.models import CreativeObject, InteractionResult
from cpow_engine.physics.balance_config import PhysicsBalanceConfig, load_physics_balance_config
from cpow_engine.physics.extended_roles import (
    ChargeSource,
    FluidBody,
    RadiantSource,
    StructuralBody,
)
from cpow_engine.physics.properties import (
    charge_of,
    clamp_delta,
    fluid_pressure_of,
    mass_of,
    radiation_of,
    residual_of,
    set_prop,
    structural_stress_of,
    temperature_of,
)


class ExtendedPhysicsEngine:
    """기본 열·재료 외 속성 기반 상호작용."""

    def __init__(self, config: PhysicsBalanceConfig | None = None) -> None:
        self.cfg = config or load_physics_balance_config()

    def resolve(self, objects: dict[str, CreativeObject]) -> list[InteractionResult]:
        if not self.cfg.extended_physics_enabled or len(objects) < 2:
            return []

        results: list[InteractionResult] = []
        obj_list = list(objects.values())
        results.extend(self._electrostatic(obj_list, objects))
        results.extend(self._fluid_flow(obj_list, objects))
        results.extend(self._radiation(obj_list, objects))
        results.extend(self._structural_load(obj_list, objects))
        return results

    def _electrostatic(
        self,
        obj_list: list[CreativeObject],
        by_id: dict[str, CreativeObject],
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        charge_role = ChargeSource()
        for src in obj_list:
            if not charge_role.can_apply(src):
                continue
            for tgt_id in src.connections:
                if tgt_id not in by_id:
                    continue
                tgt = by_id[tgt_id]
                if not charge_role.can_apply(tgt):
                    continue
                q1 = charge_of(src)
                q2 = charge_of(tgt)
                if abs(q1) < 0.1 or abs(q2) < 0.1:
                    continue
                force = abs(q1 * q2) * self.cfg.electrostatic_coupling * 0.001
                repulse = (q1 * q2) > 0
                results.append(
                    InteractionResult(
                        source_id=src.id,
                        target_id=tgt.id,
                        effect_type="electrostatic",
                        magnitude=force,
                        energy_delta=force * (0.35 if repulse else 0.5),
                        metadata={
                            "repulsive": repulse,
                            "formula": "coulomb_like",
                        },
                    )
                )
        return results

    def _fluid_flow(
        self,
        obj_list: list[CreativeObject],
        by_id: dict[str, CreativeObject],
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        fluid = FluidBody()
        for src in obj_list:
            if not fluid.can_apply(src):
                continue
            src_data = fluid.extract(src)
            for tgt_id in src.connections:
                if tgt_id not in by_id:
                    continue
                tgt = by_id[tgt_id]
                if not fluid.can_apply(tgt):
                    continue
                tgt_data = fluid.extract(tgt)
                gradient = src_data["pressure"] - tgt_data["pressure"]
                if abs(gradient) < 0.5:
                    continue
                vis = (src_data["viscosity"] + tgt_data["viscosity"]) * 0.5
                flow = abs(gradient) * self.cfg.fluid_flow_factor / max(vis, 0.1)
                high, low = (src, tgt) if gradient > 0 else (tgt, src)
                results.append(
                    InteractionResult(
                        source_id=high.id,
                        target_id=low.id,
                        effect_type="fluid_flow",
                        magnitude=flow,
                        energy_delta=flow * 0.4,
                        metadata={"formula": "pressure_equalization"},
                    )
                )
        return results

    def _radiation(
        self,
        obj_list: list[CreativeObject],
        by_id: dict[str, CreativeObject],
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        rad = RadiantSource()
        for src in obj_list:
            if not rad.can_apply(src):
                continue
            intensity = radiation_of(src)
            if intensity < 1.0:
                continue
            for tgt in obj_list:
                if tgt.id == src.id:
                    continue
                if tgt.id not in src.connections and src.id not in tgt.connections:
                    # 1-hop 이웃만 직접 조사
                    shared = any(
                        n in by_id and src.id in by_id[n].connections
                        for n in tgt.connections
                    )
                    if not shared:
                        continue
                dose = intensity * self.cfg.radiation_coupling * 0.02
                results.append(
                    InteractionResult(
                        source_id=src.id,
                        target_id=tgt.id,
                        effect_type="radiation",
                        magnitude=dose,
                        energy_delta=dose * 0.25,
                        metadata={"formula": "radiant_transfer"},
                    )
                )
        return results

    def _structural_load(
        self,
        obj_list: list[CreativeObject],
        by_id: dict[str, CreativeObject],
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        struct = StructuralBody()
        for beam in obj_list:
            if not struct.can_apply(beam):
                continue
            beam_mass = mass_of(beam)
            if beam_mass < 0.1:
                continue
            for sup_id in beam.connections:
                if sup_id not in by_id:
                    continue
                support = by_id[sup_id]
                if not struct.can_apply(support):
                    continue
                heat_load = temperature_of(beam) * 0.01
                load = (beam_mass + heat_load) * self.cfg.structural_load_factor
                results.append(
                    InteractionResult(
                        source_id=beam.id,
                        target_id=support.id,
                        effect_type="structural_load",
                        magnitude=load,
                        energy_delta=-load * 0.1,
                        metadata={"formula": "mass_heat_load"},
                    )
                )
        return results

    def apply_feedback(
        self,
        objects: dict[str, CreativeObject],
        interactions: list[InteractionResult],
    ) -> int:
        if not interactions:
            return 0
        cap = self.cfg.max_property_delta_per_tick
        n = 0
        for ix in interactions:
            if ix.effect_type == "electrostatic" and ix.target_id in objects:
                tgt = objects[ix.target_id]
                drift = ix.magnitude * 0.15
                if ix.metadata.get("repulsive"):
                    set_prop(
                        tgt,
                        "electric_charge",
                        charge_of(tgt) + clamp_delta(drift, cap),
                        unit="coulomb",
                    )
                else:
                    set_prop(
                        tgt,
                        "electric_charge",
                        charge_of(tgt) - clamp_delta(drift, cap),
                        unit="coulomb",
                    )
                n += 1
            if ix.effect_type == "fluid_flow" and ix.target_id in objects:
                tgt = objects[ix.target_id]
                set_prop(
                    tgt,
                    "fluid_pressure",
                    fluid_pressure_of(tgt) + clamp_delta(ix.magnitude * 0.5, cap),
                    unit="kpa",
                )
                n += 1
            if ix.effect_type == "radiation" and ix.target_id in objects:
                tgt = objects[ix.target_id]
                set_prop(
                    tgt,
                    "residual_heat",
                    residual_of(tgt) + clamp_delta(ix.magnitude * 0.7, cap),
                    unit="joules",
                )
                n += 1
            if ix.effect_type == "structural_load" and ix.target_id in objects:
                sup = objects[ix.target_id]
                set_prop(
                    sup,
                    "structural_stress",
                    structural_stress_of(sup) + clamp_delta(ix.magnitude, cap),
                    unit="mpa",
                )
                n += 1
        return n
