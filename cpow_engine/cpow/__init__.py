"""CPoW Engine — Action Data + World Delta → 에너지·경제 점수."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

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
    repetition_penalty: float
    bot_risk: float
    breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, float]:
        return {
            "energy": self.energy,
            "economic_value": self.economic_value,
            "creativity_score": self.creativity_score,
            "entropy_bonus": self.entropy_bonus,
            "repetition_penalty": self.repetition_penalty,
            "bot_risk": self.bot_risk,
            **self.breakdown,
        }


class CPoWEngine:
    """엔트로피 기반 보상 체계 — 봇 억제 휴리스틱 내장."""

    def __init__(
        self,
        *,
        base_energy_rate: float = 1.0,
        uniqueness_weight: float = 2.0,
        repetition_decay: float = 0.85,
        bot_threshold: float = 0.7,
    ) -> None:
        self.base_energy_rate = base_energy_rate
        self.uniqueness_weight = uniqueness_weight
        self.repetition_decay = repetition_decay
        self.bot_threshold = bot_threshold
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
        repetition_penalty = self._repetition_penalty(action)
        bot_risk = self._bot_risk_score(action)

        adjusted_energy = (
            raw_energy
            * creativity
            * (1.0 + entropy_bonus)
            * repetition_penalty
            * (1.0 - bot_risk * 0.8)
        )
        economic = adjusted_energy * self.uniqueness_weight

        return CPoWScore(
            energy=round(adjusted_energy, 4),
            economic_value=round(economic, 4),
            creativity_score=round(creativity, 4),
            entropy_bonus=round(entropy_bonus, 4),
            repetition_penalty=round(repetition_penalty, 4),
            bot_risk=round(bot_risk, 4),
            breakdown={
                "raw_energy": round(raw_energy, 4),
                "interaction_count": float(len(delta.interactions)),
            },
        )

    def _compute_raw_energy(
        self, delta: WorldDelta, state: SimulationState
    ) -> float:
        interaction_energy = sum(
            abs(i.energy_delta) for i in delta.interactions
        )
        creation_bonus = len(delta.objects_added) * 5.0
        return (interaction_energy + creation_bonus) * self.base_energy_rate

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
            return 1.5 + min(len(obj.properties) * 0.1, 0.5)
        return max(0.3, 1.0 / (1.0 + count * 0.5))

    def _entropy_bonus(self, state: SimulationState) -> float:
        if not state.objects:
            return 0.0
        fingerprints = {o.creativity_fingerprint for o in state.objects.values()}
        diversity = len(fingerprints) / len(state.objects)
        connection_density = sum(
            len(o.connections) for o in state.objects.values()
        ) / max(len(state.objects), 1)
        return min(0.5, diversity * 0.3 + connection_density * 0.05)

    def _repetition_penalty(self, action: ActionRecord) -> float:
        recent = self._action_history[-20:]
        if len(recent) < 3:
            return 1.0

        same_type = sum(1 for a in recent if a.action_type == action.action_type)
        ratio = same_type / len(recent)

        if ratio > 0.8:
            return self.repetition_decay ** (same_type - 2)
        return 1.0

    def _bot_risk_score(self, action: ActionRecord) -> float:
        """봇 흔적 탐지: 균일한 간격, 동일 payload, 단조 행동."""
        recent = self._action_history[-30:]
        if len(recent) < 5:
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

        payload_hashes = [
            str(sorted(a.payload.items())) for a in recent
        ]
        unique_payloads = len(set(payload_hashes)) / len(payload_hashes)

        action_types = [a.action_type for a in recent]
        type_entropy = len(set(action_types)) / len(action_types)

        bot_signal = (
            interval_uniformity * 0.4
            + (1.0 - unique_payloads) * 0.35
            + (1.0 - type_entropy) * 0.25
        )
        return min(1.0, max(0.0, bot_signal))

    def is_likely_bot(self, action: ActionRecord) -> bool:
        return self._bot_risk_score(action) >= self.bot_threshold
