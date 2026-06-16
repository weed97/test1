"""에리어 법칙 — 지역 물리·창조 규칙."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from cpow_engine.areas.modes import SimulationMode
from cpow_engine.collab.policy import CollabPolicy


@dataclass
class AreaLawSet:
    """창조된 에리어에만 적용되는 물리·협동 규칙."""

    name: str = "미정의 영역"
    physics_constants: dict[str, float] = field(default_factory=dict)
    heat_baseline: float = 50.0
    allowed_creation_types: list[str] = field(
        default_factory=lambda: ["heat", "material", "connection"]
    )
    collab_overrides: dict[str, float | int] = field(default_factory=dict)
    description: str = ""

    def apply_collab_policy(self, base: CollabPolicy | None = None) -> CollabPolicy:
        policy = base or CollabPolicy()
        if not self.collab_overrides:
            return policy
        data = policy.to_dict()
        data.update(self.collab_overrides)
        return CollabPolicy(
            max_relative_change=float(data["max_relative_change"]),
            max_absolute_heat_delta=float(data["max_absolute_heat_delta"]),
            max_creations_per_tick=int(data["max_creations_per_tick"]),
            max_patches_per_batch=int(data["max_patches_per_batch"]),
            damp_factor=float(data["damp_factor"]),
            noise_threshold=float(data["noise_threshold"]),
            min_creativity_for_large_change=float(
                data["min_creativity_for_large_change"]
            ),
            large_change_multiplier=float(data["large_change_multiplier"]),
            pulse_interval_sec=float(data["pulse_interval_sec"]),
            min_creator_cooldown_sec=float(data["min_creator_cooldown_sec"]),
            max_creations_per_creator_per_pulse=int(
                data["max_creations_per_creator_per_pulse"]
            ),
        )

    def allows_creation_type(self, creation_type: str) -> bool:
        return creation_type.lower() in [t.lower() for t in self.allowed_creation_types]

    def clamp_heat(self, requested: float, role_max: float) -> float:
        regional_max = self.physics_constants.get("max_heat_intensity", 300.0)
        return min(requested, role_max, regional_max)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "physics_constants": dict(self.physics_constants),
            "heat_baseline": self.heat_baseline,
            "allowed_creation_types": list(self.allowed_creation_types),
            "collab_overrides": dict(self.collab_overrides),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AreaLawSet:
        return cls(
            name=str(data.get("name", "미정의 영역")),
            physics_constants={
                k: float(v) for k, v in data.get("physics_constants", {}).items()
            },
            heat_baseline=float(data.get("heat_baseline", 50.0)),
            allowed_creation_types=list(
                data.get("allowed_creation_types", ["heat", "material", "connection"])
            ),
            collab_overrides=dict(data.get("collab_overrides", {})),
            description=str(data.get("description", "")),
        )


def load_area_templates(path: Path | None = None) -> dict[str, AreaLawSet]:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config" / "area_templates.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {
        key: AreaLawSet.from_dict(value)
        for key, value in data.get("templates", {}).items()
    }


def template_for_mode(mode: SimulationMode) -> str:
    if mode == SimulationMode.CREATION:
        return "foundry"
    if mode == SimulationMode.ADVENTURE:
        return "wilderness"
    return "settlement"
