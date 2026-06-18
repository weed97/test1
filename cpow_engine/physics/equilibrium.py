"""균형 조절 — 활발한 교차 뒤 에너지·열이 안정점으로 수렴."""

from __future__ import annotations

from dataclasses import dataclass, field

from cpow_engine.models import CreativeObject, InteractionResult, SimulationState
from cpow_engine.physics.balance_config import PhysicsBalanceConfig, load_physics_balance_config
from cpow_engine.physics.properties import heat_of, residual_of, set_prop


@dataclass
class EquilibriumReport:
    balance_index: float = 1.0
    target_pool: float = 0.0
    pool_delta: float = 0.0
    heat_adjustments: int = 0
    residual_decays: int = 0
    interaction_count: int = 0
    crossover_density: float = 0.0
    metadata: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "balance_index": round(self.balance_index, 4),
            "target_pool": round(self.target_pool, 3),
            "pool_delta": round(self.pool_delta, 3),
            "heat_adjustments": self.heat_adjustments,
            "residual_decays": self.residual_decays,
            "interaction_count": self.interaction_count,
            "crossover_density": round(self.crossover_density, 4),
            **{k: round(v, 4) for k, v in self.metadata.items()},
        }


class EquilibriumRegulator:
    """과열·침체를 자동 보정 — 세계를 죽이지 않고 균형 유지."""

    def __init__(self, config: PhysicsBalanceConfig | None = None) -> None:
        self.cfg = config or load_physics_balance_config()
        self._smoothed_balance: float = 1.0

    def regulate(
        self,
        state: SimulationState,
        interactions: list[InteractionResult],
    ) -> EquilibriumReport:
        if not self.cfg.equilibrium_enabled:
            return EquilibriumReport(interaction_count=len(interactions))

        n = max(len(state.objects), 1)
        target = n * self.cfg.target_energy_per_object
        report = EquilibriumReport(
            target_pool=target,
            interaction_count=len(interactions),
        )

        crossover = [
            i for i in interactions
            if i.effect_type in (
                "hub_crossover",
                "path_crossover",
                "ambient_coupling",
            )
        ]
        report.crossover_density = len(crossover) / max(len(interactions), 1)

        pool_delta = self._balance_energy_pool(state, target)
        report.pool_delta = pool_delta

        heat_adj, residual_dec = self._balance_object_fields(state.objects)
        report.heat_adjustments = heat_adj
        report.residual_decays = residual_dec

        raw_balance = self._compute_balance_index(
            state.energy_pool,
            target,
            state.objects,
            len(interactions),
        )
        alpha = self.cfg.balance_smoothing
        self._smoothed_balance = (
            alpha * raw_balance + (1.0 - alpha) * self._smoothed_balance
        )
        report.balance_index = self._smoothed_balance
        report.metadata = {
            "mean_heat": self._mean_heat(state.objects),
            "mean_residual": self._mean_residual(state.objects),
            "raw_balance": raw_balance,
        }
        return report

    def _balance_energy_pool(self, state: SimulationState, target: float) -> float:
        pool = state.energy_pool
        delta = 0.0

        if pool > target * 1.08:
            excess = pool - target
            delta = -excess * self.cfg.pool_dissipation_rate
            state.energy_pool = max(0.0, pool + delta)
        elif pool < target * self.cfg.pool_injection_floor and state.objects:
            deficit = target - pool
            delta = deficit * self.cfg.pool_injection_rate
            state.energy_pool = pool + delta

        return delta

    def _balance_object_fields(
        self,
        objects: dict[str, CreativeObject],
    ) -> tuple[int, int]:
        if not objects:
            return 0, 0

        mean_heat = self._mean_heat(objects)
        mean_residual = self._mean_residual(objects)
        heat_adj = 0
        residual_dec = 0

        for obj in objects.values():
            heat_prop = obj.get_property("heat_intensity")
            if heat_prop is not None:
                pull = (mean_heat - heat_prop.value) * self.cfg.heat_pull_to_ambient
                if abs(pull) > 0.01:
                    heat_prop.value = max(0.0, heat_prop.value + pull)
                    heat_adj += 1

            res = residual_of(obj)
            if res > 0.01:
                decayed = res * (1.0 - self.cfg.residual_decay)
                decayed += (mean_residual - res) * 0.05
                set_prop(obj, "residual_heat", max(0.0, decayed), unit="joules")
                residual_dec += 1

        return heat_adj, residual_dec

    def _mean_heat(self, objects: dict[str, CreativeObject]) -> float:
        heats = [heat_of(o) for o in objects.values() if o.get_property("heat_intensity")]
        return sum(heats) / len(heats) if heats else 0.0

    def _mean_residual(self, objects: dict[str, CreativeObject]) -> float:
        vals = [residual_of(o) for o in objects.values()]
        return sum(vals) / len(vals) if vals else 0.0

    def _compute_balance_index(
        self,
        energy_pool: float,
        target: float,
        objects: dict[str, CreativeObject],
        interaction_count: int,
    ) -> float:
        if target <= 0:
            return 1.0
        pool_err = abs(energy_pool - target) / target
        pool_score = max(0.0, 1.0 - min(1.0, pool_err))

        heats = [heat_of(o) for o in objects.values() if o.get_property("heat_intensity")]
        spread_score = 1.0
        if len(heats) >= 2:
            mean = sum(heats) / len(heats)
            variance = sum((h - mean) ** 2 for h in heats) / len(heats)
            spread_score = max(0.0, 1.0 - min(1.0, variance / max(mean * mean, 1.0)))

        activity = min(1.0, interaction_count / max(len(objects), 1))
        # 활발함(activity)과 안정(pool+spread)을 함께 높게 유지
        return 0.45 * pool_score + 0.35 * spread_score + 0.20 * activity
