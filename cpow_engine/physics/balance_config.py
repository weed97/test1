"""Physics balance tuning — crossover activity + equilibrium."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "physics_balance.json"


@dataclass(frozen=True)
class PhysicsBalanceConfig:
    crossover_enabled: bool = True
    hub_bleed_factor: float = 0.18
    two_hop_bleed_factor: float = 0.08
    ambient_coupling: float = 0.04
    feedback_heat_drain: float = 0.12
    feedback_residual_gain: float = 0.65
    max_property_delta_per_tick: float = 25.0
    equilibrium_enabled: bool = True
    target_energy_per_object: float = 18.0
    pool_dissipation_rate: float = 0.22
    pool_injection_rate: float = 0.06
    pool_injection_floor: float = 0.15
    heat_pull_to_ambient: float = 0.08
    residual_decay: float = 0.35
    balance_smoothing: float = 0.4
    extended_physics_enabled: bool = True
    field_physics_enabled: bool = True
    phase_change_enabled: bool = True
    electrostatic_coupling: float = 1.0
    fluid_flow_factor: float = 0.35
    radiation_coupling: float = 0.8
    structural_load_factor: float = 0.12
    gravity_strength: float = 9.8
    wind_strength: float = 0.5
    ambient_pressure_base: float = 101.3
    pressure_coupling: float = 0.06
    charge_hub_bleed: float = 0.14
    radiation_bleed_factor: float = 0.22
    freeze_ratio: float = 0.92

    @classmethod
    def from_dict(cls, data: dict) -> PhysicsBalanceConfig:
        return cls(
            crossover_enabled=bool(data.get("crossover_enabled", True)),
            hub_bleed_factor=float(data.get("hub_bleed_factor", 0.18)),
            two_hop_bleed_factor=float(data.get("two_hop_bleed_factor", 0.08)),
            ambient_coupling=float(data.get("ambient_coupling", 0.04)),
            feedback_heat_drain=float(data.get("feedback_heat_drain", 0.12)),
            feedback_residual_gain=float(data.get("feedback_residual_gain", 0.65)),
            max_property_delta_per_tick=float(
                data.get("max_property_delta_per_tick", 25.0)
            ),
            equilibrium_enabled=bool(data.get("equilibrium_enabled", True)),
            target_energy_per_object=float(
                data.get("target_energy_per_object", 18.0)
            ),
            pool_dissipation_rate=float(data.get("pool_dissipation_rate", 0.22)),
            pool_injection_rate=float(data.get("pool_injection_rate", 0.06)),
            pool_injection_floor=float(data.get("pool_injection_floor", 0.15)),
            heat_pull_to_ambient=float(data.get("heat_pull_to_ambient", 0.08)),
            residual_decay=float(data.get("residual_decay", 0.35)),
            balance_smoothing=float(data.get("balance_smoothing", 0.4)),
            extended_physics_enabled=bool(
                data.get("extended_physics_enabled", True)
            ),
            field_physics_enabled=bool(data.get("field_physics_enabled", True)),
            phase_change_enabled=bool(data.get("phase_change_enabled", True)),
            electrostatic_coupling=float(data.get("electrostatic_coupling", 1.0)),
            fluid_flow_factor=float(data.get("fluid_flow_factor", 0.35)),
            radiation_coupling=float(data.get("radiation_coupling", 0.8)),
            structural_load_factor=float(data.get("structural_load_factor", 0.12)),
            gravity_strength=float(data.get("gravity_strength", 9.8)),
            wind_strength=float(data.get("wind_strength", 0.5)),
            ambient_pressure_base=float(data.get("ambient_pressure_base", 101.3)),
            pressure_coupling=float(data.get("pressure_coupling", 0.06)),
            charge_hub_bleed=float(data.get("charge_hub_bleed", 0.14)),
            radiation_bleed_factor=float(data.get("radiation_bleed_factor", 0.22)),
            freeze_ratio=float(data.get("freeze_ratio", 0.92)),
        )


def load_physics_balance_config(
    path: Path | None = None,
) -> PhysicsBalanceConfig:
    cfg_path = path or _CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as fh:
        return PhysicsBalanceConfig.from_dict(json.load(fh))
