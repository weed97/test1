"""공성·수성 — 고정 룰 없이 압력·요새·파괴가 자연스럽게 흐르는 교전."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from cpow_engine.areas.durability import get_durability, is_confirmed, is_core_facility
from cpow_engine.areas.imbue import get_imbued_destruction
from cpow_engine.models import CreativeObject

ASSAULT_DECAY_PER_TICK = 0.94
REPULSE_DECAY_PER_TICK = 0.97
MOMENTUM_PER_DURABILITY = 0.35
REPULSE_PER_POWER = 0.55


def object_fortification_contribution(obj: CreativeObject) -> float:
    """오브젝트 속성에서 수성 기여도 — 하드코딩된 '성벽' 클래스 없음."""
    if not is_confirmed(obj):
        return 0.0

    fort = obj.get_property("fortification_rating")
    if fort is not None:
        return max(0.0, fort.value)

    garrison = obj.get_property("garrison_heat")
    if garrison is not None:
        return max(0.0, garrison.value) * 0.08

    imbued = get_imbued_destruction(obj)
    if imbued > 0.0:
        return imbued * 0.12

    if is_core_facility(obj):
        return get_durability(obj) * 0.18

    durability = get_durability(obj)
    if durability > 40.0:
        return durability * 0.06
    return 0.0


def area_fortification_strength(objects: dict[str, CreativeObject]) -> float:
    return sum(object_fortification_contribution(o) for o in objects.values())


@dataclass
class SiegeEvent:
    kind: str
    actor_id: str
    magnitude: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "actor_id": self.actor_id,
            "magnitude": round(self.magnitude, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class SiegeContest:
    """한 방향 공성 — attacker → defender. 페이즈 없이 연속 압력."""

    attacker_area_id: str
    defender_area_id: str
    assault_momentum: float = 0.0
    repulse_reserve: float = 0.0
    durability_breached: float = 0.0
    last_assault_at: float = 0.0
    last_repulse_at: float = 0.0
    events: list[SiegeEvent] = field(default_factory=list)

    def record(self, kind: str, actor_id: str, magnitude: float) -> None:
        self.events.append(SiegeEvent(kind, actor_id, magnitude))
        if len(self.events) > 40:
            self.events.pop(0)

    def to_dict(self, *, fortification: float, dominance_ratio: float) -> dict[str, Any]:
        flow = emergent_flow(
            self.assault_momentum,
            fortification + self.repulse_reserve * 0.4,
            dominance_ratio,
        )
        return {
            "attacker_area_id": self.attacker_area_id,
            "defender_area_id": self.defender_area_id,
            "assault_momentum": round(self.assault_momentum, 3),
            "repulse_reserve": round(self.repulse_reserve, 3),
            "durability_breached": round(self.durability_breached, 2),
            "fortification_strength": round(fortification, 2),
            "cross_scale_modifier": round(
                siege_cross_scale_modifier(
                    self.assault_momentum,
                    fortification,
                    self.repulse_reserve,
                ),
                3,
            ),
            "flow": flow,
            "recent_events": [e.to_dict() for e in self.events[-6:]],
        }


def siege_cross_scale_modifier(
    assault: float,
    fortification: float,
    repulse_reserve: float = 0.0,
) -> float:
    """
    교차 파괴 난이도 배율.
    >1 이면 공격자에게 더 어려움, <1 이면 공성 압력으로 방어가 약화됨.
    """
    defense = fortification + repulse_reserve * 0.45
    if assault <= 0.5:
        return 1.0 + defense * 0.012

    pressure = assault / max(1.0, defense)
    if pressure >= 1.2:
        return max(0.5, 1.0 / (1.0 + (pressure - 1.0) * 0.42))
    return 1.0 + max(0.0, defense - assault * 0.25) * 0.01


def emergent_flow(
    assault: float,
    effective_defense: float,
    dominance_ratio: float,
) -> dict[str, Any]:
    """연속 압력 → 흐름 설명. 고정 페이즈/턴 규칙 없음."""
    net = assault - effective_defense * 0.45
    pressure = assault / max(1.0, effective_defense + assault)

    if assault < 0.5 and effective_defense < 3.0:
        flow = "border_tension"
        label_ko = "국경 긴장 — 적대만 선언된 상태"
    elif net < -8.0:
        flow = "defenders_hold"
        label_ko = "수성 우세 — 요새·반격이 압력을 삼킴"
    elif net < 4.0:
        flow = "skirmish"
        label_ko = "접전 — 소규모 파괴와 방어가 오감"
    elif net < 18.0:
        flow = "siege_pressure"
        label_ko = "공성 압력 — 누적 공격이 방어를 마모"
    else:
        flow = "breach_window"
        label_ko = "突破口 — 방어 붕괴 구간, 파괴가 유리"

    if dominance_ratio < 0.45 and assault > 5.0:
        label_ko += " (소규모 에리어의 역공)"

    return {
        "pressure": round(pressure, 3),
        "net": round(net, 2),
        "flow": flow,
        "label": label_ko,
    }


@dataclass
class SiegeLedger:
    """에리어 쌍별 진행 중인 공성 압력."""

    _contests: dict[tuple[str, str], SiegeContest] = field(default_factory=dict)

    def _key(self, attacker_area_id: str, defender_area_id: str) -> tuple[str, str]:
        return (attacker_area_id, defender_area_id)

    def get(self, attacker_area_id: str, defender_area_id: str) -> SiegeContest | None:
        return self._contests.get(self._key(attacker_area_id, defender_area_id))

    def get_or_create(
        self, attacker_area_id: str, defender_area_id: str,
    ) -> SiegeContest:
        key = self._key(attacker_area_id, defender_area_id)
        if key not in self._contests:
            self._contests[key] = SiegeContest(attacker_area_id, defender_area_id)
        return self._contests[key]

    def on_assault(
        self,
        attacker_area_id: str,
        defender_area_id: str,
        actor_id: str,
        *,
        durability_destroyed: float,
    ) -> SiegeContest:
        contest = self.get_or_create(attacker_area_id, defender_area_id)
        gain = durability_destroyed * MOMENTUM_PER_DURABILITY
        contest.assault_momentum += gain
        contest.durability_breached += durability_destroyed
        contest.last_assault_at = time.time()
        contest.record("assault", actor_id, gain)
        return contest

    def on_repulse(
        self,
        attacker_area_id: str,
        defender_area_id: str,
        actor_id: str,
        *,
        power_spent: float,
    ) -> SiegeContest:
        contest = self.get_or_create(attacker_area_id, defender_area_id)
        relief = power_spent * REPULSE_PER_POWER
        contest.assault_momentum = max(0.0, contest.assault_momentum - relief)
        contest.repulse_reserve += power_spent * 0.35
        contest.last_repulse_at = time.time()
        contest.record("repulse", actor_id, relief)
        return contest

    def on_hostile_declared(
        self, area_a: str, area_b: str,
    ) -> list[SiegeContest]:
        """적대 선언 시 양방향 긴장 컨텍스트만 생성 — 별도 '시작' 없음."""
        return [
            self.get_or_create(area_a, area_b),
            self.get_or_create(area_b, area_a),
        ]

    def tick(self, fortifications: dict[str, float]) -> int:
        """압력 자연 감쇠 — 요새가 있으면 공성 모멘텀 추가 소모."""
        updated = 0
        for contest in self._contests.values():
            fort = fortifications.get(contest.defender_area_id, 0.0)
            before = contest.assault_momentum
            contest.assault_momentum *= ASSAULT_DECAY_PER_TICK
            if fort > 0 and contest.assault_momentum > 0:
                contest.assault_momentum = max(
                    0.0,
                    contest.assault_momentum - fort * 0.008,
                )
            contest.repulse_reserve *= REPULSE_DECAY_PER_TICK
            if abs(before - contest.assault_momentum) > 1e-6:
                updated += 1
        return updated

    def contests_for(self, area_id: str) -> list[SiegeContest]:
        out: list[SiegeContest] = []
        for contest in self._contests.values():
            if contest.attacker_area_id == area_id or contest.defender_area_id == area_id:
                if contest.assault_momentum > 0.01 or contest.repulse_reserve > 0.01:
                    out.append(contest)
                elif contest.durability_breached > 0:
                    out.append(contest)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {"active_pairs": len(self._contests)}
