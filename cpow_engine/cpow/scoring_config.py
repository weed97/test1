"""Load CPoW scoring weights from JSON config."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "cpow_scoring.json"


@dataclass(frozen=True)
class ScoringWeights:
    base_energy_rate: float = 1.0
    uniqueness_weight: float = 2.0
    repetition_decay: float = 0.85
    bot_threshold: float = 0.7
    creation_bonus_per_object: float = 5.0
    first_fingerprint_bonus: float = 1.5
    property_bonus_per_prop: float = 0.1
    max_property_bonus: float = 0.5
    duplicate_fingerprint_floor: float = 0.3
    duplicate_fingerprint_decay: float = 0.5
    entropy_diversity: float = 0.30
    entropy_connections: float = 0.05
    entropy_cap: float = 0.5
    complexity_properties: float = 0.12
    complexity_connections: float = 0.10
    complexity_interactions: float = 0.15
    complexity_cap: float = 0.6
    interval_uniformity: float = 0.4
    payload_repetition: float = 0.35
    action_monotony: float = 0.25
    repetition_window: int = 20
    repetition_same_type_threshold: float = 0.8
    bot_history_window: int = 30
    bot_min_history: int = 5

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoringWeights:
        weights = data.get("weights", {})
        bot = data.get("bot_signals", {})
        return cls(
            base_energy_rate=float(data.get("base_energy_rate", 1.0)),
            uniqueness_weight=float(data.get("uniqueness_weight", 2.0)),
            repetition_decay=float(data.get("repetition_decay", 0.85)),
            bot_threshold=float(data.get("bot_threshold", 0.7)),
            creation_bonus_per_object=float(
                data.get("creation_bonus_per_object", 5.0)
            ),
            first_fingerprint_bonus=float(
                data.get("first_fingerprint_bonus", 1.5)
            ),
            property_bonus_per_prop=float(
                data.get("property_bonus_per_prop", 0.1)
            ),
            max_property_bonus=float(data.get("max_property_bonus", 0.5)),
            duplicate_fingerprint_floor=float(
                data.get("duplicate_fingerprint_floor", 0.3)
            ),
            duplicate_fingerprint_decay=float(
                data.get("duplicate_fingerprint_decay", 0.5)
            ),
            entropy_diversity=float(weights.get("entropy_diversity", 0.30)),
            entropy_connections=float(weights.get("entropy_connections", 0.05)),
            entropy_cap=float(weights.get("entropy_cap", 0.5)),
            complexity_properties=float(
                weights.get("complexity_properties", 0.12)
            ),
            complexity_connections=float(
                weights.get("complexity_connections", 0.10)
            ),
            complexity_interactions=float(
                weights.get("complexity_interactions", 0.15)
            ),
            complexity_cap=float(weights.get("complexity_cap", 0.6)),
            interval_uniformity=float(bot.get("interval_uniformity", 0.4)),
            payload_repetition=float(bot.get("payload_repetition", 0.35)),
            action_monotony=float(bot.get("action_monotony", 0.25)),
            repetition_window=int(data.get("repetition_window", 20)),
            repetition_same_type_threshold=float(
                data.get("repetition_same_type_threshold", 0.8)
            ),
            bot_history_window=int(data.get("bot_history_window", 30)),
            bot_min_history=int(data.get("bot_min_history", 5)),
        )


def load_scoring_weights(path: Path | None = None) -> ScoringWeights:
    cfg_path = path or _CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as fh:
        return ScoringWeights.from_dict(json.load(fh))
