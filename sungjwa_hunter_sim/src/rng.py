"""예측 불가 변수가 풀(full)로 적용된 난수 엔진.

8개 변수가 어떻게 결과에 개입하는지 한 곳에 모아 둔다. 모든 확률/수치 판정은
이 엔진을 통과하며, 따라서 변수 변경이 즉시 시뮬레이션 전반에 반영된다.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, TypeVar

from .variables import VariableManager

T = TypeVar("T")


class ChaosRNG:
    def __init__(self, variables: VariableManager, seed: Optional[int] = None):
        self.vars = variables
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------ #
    def _u(self, key: str) -> float:
        return self.vars.uvar(key)

    # ------------------------------------------------------------------ #
    def jitter(self, base: float) -> float:
        """randomness_intensity 와 fate_deviation 으로 값을 흔든다.

        - randomness_intensity: 흔들림의 진폭(±)
        - fate_deviation: 결과를 행운/불운 방향으로 미는 편향
        """
        intensity = self._u("randomness_intensity")
        deviation = self._u("fate_deviation")
        noise = self._rng.uniform(-1.0, 1.0) * intensity * 0.25
        bias = deviation * 0.15
        return base * (1.0 + noise + bias)

    def roll(self, success_chance: float, *, lucky: bool = True) -> bool:
        """probability_distortion / luck_factor / constellation_mood 적용 성공 판정."""
        p = max(0.0, min(1.0, success_chance))
        distortion = self._u("probability_distortion")
        # 확률을 비선형으로 왜곡 (distortion>1 이면 중간확률이 양극단으로 벌어짐)
        p = p ** (1.0 / max(0.05, distortion))
        if lucky:
            p += (self._u("luck_factor") - 1.0) * 0.08
        p += self._u("constellation_mood") * 0.05
        p = max(0.0, min(1.0, p))
        return self._rng.random() < p

    def critical(self) -> bool:
        """luck_factor 기반 치명타/대성공 판정."""
        chance = 0.08 * self._u("luck_factor") + 0.04 * self._u("fate_deviation")
        return self._rng.random() < max(0.0, min(0.95, chance))

    def mutates(self) -> bool:
        """event_mutation_rate 기반 이벤트 돌연변이 판정."""
        rate = self._u("event_mutation_rate")
        rate += (self._u("randomness_intensity") - 1.0) * 0.03
        return self._rng.random() < max(0.0, min(1.0, rate))

    def chains(self) -> bool:
        """chaos_resonance 기반 연쇄 이벤트 판정."""
        chance = self._u("chaos_resonance") * 0.35
        return self._rng.random() < max(0.0, min(0.95, chance))

    def crisis_multiplier(self, turn: int) -> float:
        """turn 경과에 따른 위기 강도 배수 (crisis_escalation)."""
        return self._u("crisis_escalation") ** max(0, turn - 1) ** 0.5

    # ------------------------------------------------------------------ #
    def scaled_int(self, base: int, spread: float = 0.4) -> int:
        """기본값 주변에서 변수 영향을 받은 정수 산출 (최소 1 또는 base 부호 유지)."""
        val = self.jitter(base) * (1.0 + self._rng.uniform(-spread, spread))
        result = int(round(val))
        if base > 0:
            return max(1, result)
        if base < 0:
            return min(-1, result)
        return result

    def choice(self, seq: Sequence[T]) -> T:
        return self._rng.choice(list(seq))

    def weighted_choice(self, items: List[T], weights: List[float]) -> T:
        adj: List[float] = []
        mood = self._u("constellation_mood")
        for w in weights:
            adj.append(max(0.0001, w * (1.0 + mood * 0.2)))
        return self._rng.choices(items, weights=adj, k=1)[0]

    def snapshot(self) -> Dict[str, float]:
        return self.vars.uvars()
