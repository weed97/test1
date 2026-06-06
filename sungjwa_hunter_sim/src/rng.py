"""예측 불가 변수가 풀(full)로 적용된 난수 엔진.

8개 변수가 어떻게 결과에 개입하는지 한 곳에 모아 둔다. 모든 확률/수치 판정은
이 엔진을 통과하며, 따라서 변수 변경이 즉시 시뮬레이션 전반에 반영된다.

게이트 몬스터의 예외 변수(exception_variables)는 exception_scope() 컨텍스트로
전투 동안에만 8개 변수 위에 덧씌워진다.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Sequence, TypeVar

import random

from .models import MonsterUnit
from .variables import VariableManager

T = TypeVar("T")

# 게이트 등급 난이도 순서 (낮음 → 높음)
GRADE_ORDER = ["F", "E", "D", "C", "B", "A", "S"]


class ChaosRNG:
    def __init__(self, variables: VariableManager, seed: Optional[int] = None):
        self.vars = variables
        self._rng = random.Random(seed)
        self._overrides: Dict[str, float] = {}
        self.monsters: List[MonsterUnit] = []

    # ------------------------------------------------------------------ #
    # 예외 변수 스코프
    # ------------------------------------------------------------------ #
    @contextmanager
    def exception_scope(self, overrides: Optional[Dict[str, float]]) -> Iterator[None]:
        """전투 등 한정된 구간에서만 8개 변수 일부를 덮어쓴다."""
        prev = self._overrides
        merged = dict(prev)
        if overrides:
            for k, v in overrides.items():
                merged[k] = float(v)
        self._overrides = merged
        try:
            yield
        finally:
            self._overrides = prev

    def active_overrides(self) -> Dict[str, float]:
        return dict(self._overrides)

    # ------------------------------------------------------------------ #
    def _u(self, key: str) -> float:
        if key in self._overrides:
            return self._overrides[key]
        return self.vars.uvar(key)

    # ------------------------------------------------------------------ #
    def jitter(self, base: float) -> float:
        """randomness_intensity 와 fate_deviation 으로 값을 흔든다."""
        intensity = self._u("randomness_intensity")
        deviation = self._u("fate_deviation")
        noise = self._rng.uniform(-1.0, 1.0) * intensity * 0.25
        bias = deviation * 0.15
        return base * (1.0 + noise + bias)

    def roll(self, success_chance: float, *, lucky: bool = True) -> bool:
        """probability_distortion / luck_factor / constellation_mood 적용 성공 판정."""
        p = max(0.0, min(1.0, success_chance))
        distortion = self._u("probability_distortion")
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

    # ------------------------------------------------------------------ #
    # 게이트 몬스터 선택 (턴이 진행될수록 고등급 출현 확률 상승)
    # ------------------------------------------------------------------ #
    def pick_monster(self, turn: int) -> Optional[MonsterUnit]:
        if not self.monsters:
            return None
        target = (turn - 1) * 0.6  # 목표 등급 인덱스 (turn 비례)
        weights: List[float] = []
        for m in self.monsters:
            gi = GRADE_ORDER.index(m.grade) if m.grade in GRADE_ORDER else 0
            base = 1.0 / (1.0 + abs(gi - target))
            # randomness_intensity 가 높으면 등급 분포가 평탄해진다(무엇이든 튀어나옴)
            flatten = (self._u("randomness_intensity") - 1.0) * 0.15
            weights.append(max(0.01, base + flatten))
        return self._rng.choices(self.monsters, weights=weights, k=1)[0]

    def snapshot(self) -> Dict[str, float]:
        """현재 8개 변수 값(예외 변수 적용 상태 반영)."""
        base = self.vars.uvars()
        base.update(self._overrides)
        return base
