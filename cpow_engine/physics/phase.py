"""상변화 — 용융·응고 피드백."""

from __future__ import annotations

from cpow_engine.models import CreativeObject, InteractionResult
from cpow_engine.physics.balance_config import PhysicsBalanceConfig, load_physics_balance_config
from cpow_engine.physics.properties import (
    phase_of,
    set_prop,
    temperature_of,
)


class PhaseChangePhysics:
    """재료 온도가 용융점을 넘으면 phase 속성 갱신."""

    def __init__(self, config: PhysicsBalanceConfig | None = None) -> None:
        self.cfg = config or load_physics_balance_config()

    def apply(
        self,
        objects: dict[str, CreativeObject],
        interactions: list[InteractionResult],
    ) -> list[InteractionResult]:
        if not self.cfg.phase_change_enabled:
            return []

        phase_events: list[InteractionResult] = []
        for obj in objects.values():
            mat_type = obj.get_property("material_type")
            melting = obj.get_property("melting_point")
            if mat_type is None or melting is None:
                continue

            temp = temperature_of(obj)
            for ix in interactions:
                if ix.target_id == obj.id and "temperature_delta" in ix.metadata:
                    temp += float(ix.metadata["temperature_delta"]) * 100.0

            current = phase_of(obj)
            if temp >= melting.value and current == "solid":
                set_prop(obj, "phase", 1.0, unit="liquid")
                phase_events.append(
                    InteractionResult(
                        source_id=obj.id,
                        target_id=None,
                        effect_type="phase_melt",
                        magnitude=temp - melting.value,
                        energy_delta=-(temp - melting.value) * 0.02,
                        metadata={"from": "solid", "to": "liquid"},
                    )
                )
            elif (
                temp < melting.value * self.cfg.freeze_ratio
                and current == "liquid"
            ):
                set_prop(obj, "phase", 1.0, unit="solid")
                phase_events.append(
                    InteractionResult(
                        source_id=obj.id,
                        target_id=None,
                        effect_type="phase_freeze",
                        magnitude=melting.value - temp,
                        energy_delta=0.0,
                        metadata={"from": "liquid", "to": "solid"},
                    )
                )
        return phase_events
