"""CPoW Engine — Action Data + World Delta → 에너지·경제 점수."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cpow_engine.cpow.scoring_config import ScoringWeights, load_scoring_weights
from cpow_engine.models import (
    ActionRecord,
    CreativeObject,
    SimulationState,
    WorldDelta,
)


@dataclass
class CPoWScore:
    """창조성 증명 점수 결과."""

    energy: float
    economic_value: float
    creativity_score: float
    entropy_bonus: float
    complexity_score: float
    repetition_penalty: float
    bot_risk: float
    breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, float]:
        return {
            "energy": self.energy,
            "economic_value": self.economic_value,
            "creativity_score": self.creativity_score,
            "entropy_bonus": self.entropy_bonus,
            "complexity_score": self.complexity_score,
            "repetition_penalty": self.repetition_penalty,
            "bot_risk": self.bot_risk,
            **self.breakdown,
        }


class CPoWEngine:
    """엔트로피·복잡도 기반 보상 — 봇 억제 휴리스틱 내장."""

    def __init__(
        self,
        *,
        weights: ScoringWeights | None = None,
        config_path: Path | None = None,
        base_energy_rate: float | None = None,
        uniqueness_weight: float | None = None,
        repetition_decay: float | None = None,
        bot_threshold: float | None = None,
    ) -> None:
        self.w = weights or load_scoring_weights(config_path)
        self.base_energy_rate = (
            base_energy_rate
            if base_energy_rate is not None
            else self.w.base_energy_rate
        )
        self.uniqueness_weight = (
            uniqueness_weight
            if uniqueness_weight is not None
            else self.w.uniqueness_weight
        )
        self.repetition_decay = (
            repetition_decay
            if repetition_decay is not None
            else self.w.repetition_decay
        )
        self.bot_threshold = (
            bot_threshold if bot_threshold is not None else self.w.bot_threshold
        )
        self._action_history: list[ActionRecord] = []
        self._fingerprint_counts: Counter[str] = Counter()

    def score_action(
        self,
        action: ActionRecord,
        delta: WorldDelta,
        state: SimulationState,
    ) -> CPoWScore:
        self._action_history.append(action)

        raw_energy = self._compute_raw_energy(delta, state)
        creativity = self._creativity_score(action, state)
        entropy_bonus = self._entropy_bonus(state)
        complexity = self._complexity_score(action, delta, state)
        repetition_penalty = self._repetition_penalty(action)
        bot_risk = self._bot_risk_score(action)

        adjusted_energy = (
            raw_energy
            * creativity
            * (1.0 + entropy_bonus)
            * (1.0 + complexity)
            * repetition_penalty
            * (1.0 - bot_risk * 0.8)
        )
        economic = adjusted_energy * self.uniqueness_weight

        return CPoWScore(
            energy=round(adjusted_energy, 4),
            economic_value=round(economic, 4),
            creativity_score=round(creativity, 4),
            entropy_bonus=round(entropy_bonus, 4),
            complexity_score=round(complexity, 4),
            repetition_penalty=round(repetition_penalty, 4),
            bot_risk=round(bot_risk, 4),
            breakdown={
                "raw_energy": round(raw_energy, 4),
                "interaction_count": float(len(delta.interactions)),
                "object_count": float(len(state.objects)),
            },
        )

    def _compute_raw_energy(
        self, delta: WorldDelta, state: SimulationState
    ) -> float:
        interaction_energy = sum(
            abs(i.energy_delta) for i in delta.interactions
        )
        creation_bonus = (
            len(delta.objects_added) * self.w.creation_bonus_per_object
        )
        density_bonus = min(
            len(delta.interactions) * 0.5,
            len(state.objects) * 0.1,
        )
        return (
            interaction_energy + creation_bonus + density_bonus
        ) * self.base_energy_rate

    def _creativity_score(
        self, action: ActionRecord, state: SimulationState
    ) -> float:
        obj_id = action.payload.get("object_id")
        if not obj_id or obj_id not in state.objects:
            return 1.0

        obj = state.objects[obj_id]
        fp = obj.creativity_fingerprint
        count = self._fingerprint_counts[fp]
        self._fingerprint_counts[fp] += 1

        if count == 0:
            prop_bonus = min(
                len(obj.properties) * self.w.property_bonus_per_prop,
                self.w.max_property_bonus,
            )
            return self.w.first_fingerprint_bonus + prop_bonus
        return max(
            self.w.duplicate_fingerprint_floor,
            1.0 / (1.0 + count * self.w.duplicate_fingerprint_decay),
        )

    def _entropy_bonus(self, state: SimulationState) -> float:
        if not state.objects:
            return 0.0
        fingerprints = {o.creativity_fingerprint for o in state.objects.values()}
        diversity = len(fingerprints) / len(state.objects)
        connection_density = sum(
            len(o.connections) for o in state.objects.values()
        ) / max(len(state.objects), 1)
        raw = (
            diversity * self.w.entropy_diversity
            + connection_density * self.w.entropy_connections
        )
        return min(self.w.entropy_cap, raw)

    def _complexity_score(
        self,
        action: ActionRecord,
        delta: WorldDelta,
        state: SimulationState,
    ) -> float:
        obj_id = action.payload.get("object_id")
        prop_factor = 0.0
        conn_factor = 0.0
        if obj_id and obj_id in state.objects:
            obj = state.objects[obj_id]
            prop_factor = min(1.0, len(obj.properties) / 8.0)
            conn_factor = min(1.0, len(obj.connections) / 4.0)

        interaction_factor = min(1.0, len(delta.interactions) / 6.0)
        raw = (
            prop_factor * self.w.complexity_properties
            + conn_factor * self.w.complexity_connections
            + interaction_factor * self.w.complexity_interactions
        )
        return min(self.w.complexity_cap, raw)

    def _repetition_penalty(self, action: ActionRecord) -> float:
        recent = self._action_history[-self.w.repetition_window :]
        if len(recent) < 3:
            return 1.0

        same_type = sum(1 for a in recent if a.action_type == action.action_type)
        ratio = same_type / len(recent)

        if ratio > self.w.repetition_same_type_threshold:
            return self.repetition_decay ** (same_type - 2)
        return 1.0

    def _bot_risk_score(self, action: ActionRecord) -> float:
        """봇 흔적 탐지: 균일한 간격, 동일 payload, 단조 행동."""
        recent = self._action_history[-self.w.bot_history_window :]
        if len(recent) < self.w.bot_min_history:
            return 0.0

        intervals = [
            recent[i].timestamp - recent[i - 1].timestamp
            for i in range(1, len(recent))
        ]
        if not intervals:
            return 0.0

        mean_interval = sum(intervals) / len(intervals)
        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(
            intervals
        )
        interval_uniformity = 1.0 / (1.0 + math.sqrt(variance) * 10)

        payload_hashes = [str(sorted(a.payload.items())) for a in recent]
        unique_payloads = len(set(payload_hashes)) / len(payload_hashes)

        action_types = [a.action_type for a in recent]
        type_entropy = len(set(action_types)) / len(action_types)

        bot_signal = (
            interval_uniformity * self.w.interval_uniformity
            + (1.0 - unique_payloads) * self.w.payload_repetition
            + (1.0 - type_entropy) * self.w.action_monotony
        )
        return min(1.0, max(0.0, bot_signal))

    def is_likely_bot(self, action: ActionRecord) -> bool:
        return self._bot_risk_score(action) >= self.bot_threshold

    def vulnerability_report(self) -> dict[str, Any]:
        """봇 시뮬 분석용 — 최근 행동 통계."""
        recent = self._action_history[-self.w.bot_history_window :]
        if not recent:
            return {"actions": 0}
        intervals = [
            recent[i].timestamp - recent[i - 1].timestamp
            for i in range(1, len(recent))
        ]
        types = [a.action_type for a in recent]
        return {
            "actions": len(recent),
            "unique_action_types": len(set(types)),
            "mean_interval": sum(intervals) / len(intervals) if intervals else 0,
            "fingerprint_variety": len(self._fingerprint_counts),
        }
