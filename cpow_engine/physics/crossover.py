"""교차 물리 — 연결 그래프·허브·환경장을 통한 활발한 상호작용."""

from __future__ import annotations

from cpow_engine.models import CreativeObject, InteractionResult
from cpow_engine.physics import HeatSource, Material
from cpow_engine.physics.balance_config import PhysicsBalanceConfig, load_physics_balance_config
from cpow_engine.physics.properties import (
    charge_of,
    clamp_delta,
    heat_of,
    radiation_of,
    residual_of,
    set_prop,
)


class CrossoverPhysics:
    """직접 연결 외 교차 경로 — 허브 공명·2-hop·환경·전하·복사 결합."""

    def __init__(self, config: PhysicsBalanceConfig | None = None) -> None:
        self.cfg = config or load_physics_balance_config()

    def resolve(
        self,
        objects: dict[str, CreativeObject],
        *,
        energy_pool: float = 0.0,
    ) -> list[InteractionResult]:
        if not self.cfg.crossover_enabled or len(objects) < 2:
            return []

        results: list[InteractionResult] = []
        obj_list = list(objects.values())
        by_id = objects

        results.extend(self._hub_resonance(obj_list, by_id))
        results.extend(self._two_hop_bleed(obj_list, by_id))
        results.extend(self._charge_hub_resonance(obj_list, by_id))
        results.extend(self._radiant_bleed(obj_list, by_id))
        results.extend(self._ambient_coupling(obj_list, energy_pool))
        return results

    def _hub_resonance(
        self,
        obj_list: list[CreativeObject],
        by_id: dict[str, CreativeObject],
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        hub_to_peers: dict[str, list[str]] = {}

        for obj in obj_list:
            for conn_id in obj.connections:
                if conn_id not in by_id:
                    continue
                hub_to_peers.setdefault(conn_id, []).append(obj.id)

        for hub_id, peer_ids in hub_to_peers.items():
            unique = list(dict.fromkeys(peer_ids))
            if len(unique) < 2:
                continue
            hub = by_id[hub_id]
            hub_mat = Material().extract(hub) if Material().can_apply(hub) else None

            for i, src_id in enumerate(unique):
                for dst_id in unique[i + 1 :]:
                    src = by_id[src_id]
                    dst = by_id[dst_id]
                    src_heat = heat_of(src) + residual_of(src) * 0.5
                    dst_heat = heat_of(dst) + residual_of(dst) * 0.5
                    if src_heat < 1.0 and dst_heat < 1.0:
                        continue
                    gradient = src_heat - dst_heat
                    if abs(gradient) < 0.5:
                        continue
                    conductivity = 0.3
                    if hub_mat:
                        conductivity = float(hub_mat.get("conductivity", 0.3))
                    flow = abs(gradient) * self.cfg.hub_bleed_factor * conductivity * 0.01
                    hotter, cooler = (src, dst) if gradient > 0 else (dst, src)
                    results.append(
                        InteractionResult(
                            source_id=hotter.id,
                            target_id=cooler.id,
                            effect_type="hub_crossover",
                            magnitude=flow,
                            energy_delta=flow * 0.55,
                            metadata={"via_hub": hub_id, "path": "hub_resonance"},
                        )
                    )
        return results

    def _charge_hub_resonance(
        self,
        obj_list: list[CreativeObject],
        by_id: dict[str, CreativeObject],
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        hub_to_peers: dict[str, list[str]] = {}
        for obj in obj_list:
            for conn_id in obj.connections:
                if conn_id not in by_id:
                    continue
                hub_to_peers.setdefault(conn_id, []).append(obj.id)

        for hub_id, peer_ids in hub_to_peers.items():
            unique = list(dict.fromkeys(peer_ids))
            if len(unique) < 2:
                continue
            for i, a_id in enumerate(unique):
                for b_id in unique[i + 1 :]:
                    a, b = by_id[a_id], by_id[b_id]
                    qa, qb = charge_of(a), charge_of(b)
                    if abs(qa) < 0.5 and abs(qb) < 0.5:
                        continue
                    flow = abs(qa - qb) * self.cfg.charge_hub_bleed * 0.01
                    results.append(
                        InteractionResult(
                            source_id=a.id,
                            target_id=b.id,
                            effect_type="charge_crossover",
                            magnitude=flow,
                            energy_delta=flow * 0.4,
                            metadata={"via_hub": hub_id, "path": "charge_hub"},
                        )
                    )
        return results

    def _radiant_bleed(
        self,
        obj_list: list[CreativeObject],
        by_id: dict[str, CreativeObject],
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        for mid in obj_list:
            rad = radiation_of(mid)
            if rad < 2.0:
                continue
            for n_id in mid.connections:
                if n_id not in by_id:
                    continue
                n = by_id[n_id]
                bleed = rad * self.cfg.radiation_bleed_factor * 0.015
                results.append(
                    InteractionResult(
                        source_id=mid.id,
                        target_id=n.id,
                        effect_type="radiation_crossover",
                        magnitude=bleed,
                        energy_delta=bleed * 0.3,
                        metadata={"via_node": mid.id, "path": "radiant_bleed"},
                    )
                )
        return results

    def _two_hop_bleed(
        self,
        obj_list: list[CreativeObject],
        by_id: dict[str, CreativeObject],
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        for mid in obj_list:
            for n1_id in mid.connections:
                if n1_id not in by_id:
                    continue
                n1 = by_id[n1_id]
                for n2_id in mid.connections:
                    if n2_id == n1_id or n2_id not in by_id:
                        continue
                    n2 = by_id[n2_id]
                    if n2_id in n1.connections:
                        continue
                    h1 = heat_of(n1) + residual_of(n1) * 0.4
                    h2 = heat_of(n2) + residual_of(n2) * 0.4
                    grad = h1 - h2
                    if abs(grad) < 1.0:
                        continue
                    flow = abs(grad) * self.cfg.two_hop_bleed_factor * 0.008
                    hotter, cooler = (n1, n2) if grad > 0 else (n2, n1)
                    results.append(
                        InteractionResult(
                            source_id=hotter.id,
                            target_id=cooler.id,
                            effect_type="path_crossover",
                            magnitude=flow,
                            energy_delta=flow * 0.45,
                            metadata={"via_node": mid.id, "path": "two_hop"},
                        )
                    )
        return results

    def _ambient_coupling(
        self,
        obj_list: list[CreativeObject],
        energy_pool: float,
    ) -> list[InteractionResult]:
        if energy_pool <= 0 or not obj_list:
            return []
        results: list[InteractionResult] = []
        ambient = energy_pool / max(len(obj_list), 1)
        for obj in obj_list:
            if not HeatSource().can_apply(obj):
                continue
            heat = heat_of(obj)
            bias = (ambient - heat) * self.cfg.ambient_coupling * 0.01
            if abs(bias) < 0.05:
                continue
            results.append(
                InteractionResult(
                    source_id=obj.id,
                    target_id=None,
                    effect_type="ambient_coupling",
                    magnitude=abs(bias),
                    energy_delta=bias * 0.3,
                    metadata={"ambient_field": ambient, "path": "energy_pool"},
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
        mutations = 0

        for ix in interactions:
            if ix.target_id and ix.target_id in objects:
                gain = ix.magnitude * self.cfg.feedback_residual_gain
                tgt = objects[ix.target_id]
                set_prop(
                    tgt,
                    "residual_heat",
                    residual_of(tgt) + clamp_delta(gain, cap),
                    unit="joules",
                )
                mutations += 1

            if ix.source_id in objects and ix.effect_type in (
                "heat_transfer",
                "hub_crossover",
                "path_crossover",
                "conductive_transfer",
                "charge_crossover",
                "radiation_crossover",
            ):
                src = objects[ix.source_id]
                heat_prop = src.get_property("heat_intensity")
                if heat_prop is not None:
                    drain = ix.magnitude * self.cfg.feedback_heat_drain
                    heat_prop.value = max(
                        0.0,
                        heat_prop.value - clamp_delta(drain, cap),
                    )
                    mutations += 1

        return mutations
