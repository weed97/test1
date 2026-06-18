"""협동 월드 정책 — 변화량 상한·감쇄 계수."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CollabPolicy:
    """오픈월드 협동 규칙 — 너무 큰 창조는 감쇄."""

    max_relative_change: float = 0.15
    max_absolute_heat_delta: float = 30.0
    max_creations_per_tick: int = 12
    max_patches_per_batch: int = 48
    damp_factor: float = 0.35
    noise_threshold: float = 0.65
    min_creativity_for_large_change: float = 0.45
    large_change_multiplier: float = 2.0
    pulse_interval_sec: float = 8.0
    min_creator_cooldown_sec: float = 4.0
    max_creations_per_creator_per_pulse: int = 1

    def effective_damp(self, magnitude: float) -> float:
        """변화가 클수록 더 강하게 감쇄."""
        if magnitude <= self.noise_threshold:
            return self.damp_factor
        excess = (magnitude - self.noise_threshold) / max(1.0 - self.noise_threshold, 0.01)
        return max(0.05, self.damp_factor * (1.0 - excess * 0.8))

    def to_dict(self) -> dict[str, float | int]:
        return {
            "max_relative_change": self.max_relative_change,
            "max_absolute_heat_delta": self.max_absolute_heat_delta,
            "max_creations_per_tick": self.max_creations_per_tick,
            "max_patches_per_batch": self.max_patches_per_batch,
            "damp_factor": self.damp_factor,
            "noise_threshold": self.noise_threshold,
            "min_creativity_for_large_change": self.min_creativity_for_large_change,
            "large_change_multiplier": self.large_change_multiplier,
            "pulse_interval_sec": self.pulse_interval_sec,
            "min_creator_cooldown_sec": self.min_creator_cooldown_sec,
            "max_creations_per_creator_per_pulse": (
                self.max_creations_per_creator_per_pulse
            ),
        }


def load_collab_policy(path: Path | None = None) -> CollabPolicy:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config" / "collab_world.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    p = data.get("policy", data)
    return CollabPolicy(
        max_relative_change=float(p.get("max_relative_change", 0.15)),
        max_absolute_heat_delta=float(p.get("max_absolute_heat_delta", 30.0)),
        max_creations_per_tick=int(p.get("max_creations_per_tick", 12)),
        max_patches_per_batch=int(p.get("max_patches_per_batch", 48)),
        damp_factor=float(p.get("damp_factor", 0.35)),
        noise_threshold=float(p.get("noise_threshold", 0.65)),
        min_creativity_for_large_change=float(
            p.get("min_creativity_for_large_change", 0.45)
        ),
        large_change_multiplier=float(p.get("large_change_multiplier", 2.0)),
        pulse_interval_sec=float(p.get("pulse_interval_sec", 8.0)),
        min_creator_cooldown_sec=float(p.get("min_creator_cooldown_sec", 4.0)),
        max_creations_per_creator_per_pulse=int(
            p.get("max_creations_per_creator_per_pulse", 1)
        ),
    )
