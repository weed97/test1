"""Bot strategy simulation — where CPoW scoring is still vulnerable."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from cpow_engine.cpow import CPoWEngine, CPoWScore
from cpow_engine.models import ActionRecord, SimulationState, WorldDelta
from cpow_engine.physics import create_heat_object


@dataclass
class BotScenarioResult:
    name: str
    actions_simulated: int
    avg_energy: float
    avg_bot_risk: float
    flagged_bot_ratio: float
    avg_creativity: float
    vulnerability: str
    samples: list[dict[str, float]] = field(default_factory=list)


@dataclass
class BotSimulationReport:
    scenarios: list[BotScenarioResult] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": [
                {
                    "name": s.name,
                    "actions_simulated": s.actions_simulated,
                    "avg_energy": round(s.avg_energy, 4),
                    "avg_bot_risk": round(s.avg_bot_risk, 4),
                    "flagged_bot_ratio": round(s.flagged_bot_ratio, 4),
                    "avg_creativity": round(s.avg_creativity, 4),
                    "vulnerability": s.vulnerability,
                }
                for s in self.scenarios
            ],
            "recommendations": list(self.recommendations),
        }


def _run_scenario(
    name: str,
    vulnerability: str,
    action_factory: Callable[[int, SimulationState], tuple[ActionRecord, WorldDelta]],
    *,
    steps: int = 25,
) -> BotScenarioResult:
    cpow = CPoWEngine()
    state = SimulationState()
    scores: list[CPoWScore] = []
    flagged = 0

    for i in range(steps):
        action, delta = action_factory(i, state)
        obj_id = action.payload.get("object_id")
        if obj_id and obj_id not in state.objects:
            label = str(action.payload.get("label", f"obj_{i}"))
            heat = 30.0 + (i % 5) * 2.0
            state.objects[obj_id] = create_heat_object(
                action.actor_id, label, heat
            )
        score = cpow.score_action(action, delta, state)
        scores.append(score)
        if cpow.is_likely_bot(action):
            flagged += 1

    n = max(len(scores), 1)
    return BotScenarioResult(
        name=name,
        actions_simulated=steps,
        avg_energy=sum(s.energy for s in scores) / n,
        avg_bot_risk=sum(s.bot_risk for s in scores) / n,
        flagged_bot_ratio=flagged / n,
        avg_creativity=sum(s.creativity_score for s in scores) / n,
        vulnerability=vulnerability,
        samples=[s.to_dict() for s in scores[-3:]],
    )


def run_bot_simulation(*, steps: int = 25) -> BotSimulationReport:
    """Simulate common bot strategies against CPoW scoring."""
    report = BotSimulationReport()

    def macro_clicker(i: int, state: SimulationState) -> tuple[ActionRecord, WorldDelta]:
        base = time.time()
        action = ActionRecord(
            "macro_bot",
            "click",
            {"x": 1, "y": 2, "object_id": "macro_target"},
            timestamp=base + i * 1.0,
        )
        return action, WorldDelta(tick=i, interactions=[])

    def fingerprint_spam(i: int, state: SimulationState) -> tuple[ActionRecord, WorldDelta]:
        obj = create_heat_object("spam_bot", "same", 50.0)
        state.objects[obj.id] = obj
        action = ActionRecord(
            "spam_bot",
            "create_object",
            {"object_id": obj.id},
            timestamp=time.time() + i * 0.3,
        )
        return action, WorldDelta(tick=i, objects_added=[obj.id])

    def diversity_farmer(i: int, state: SimulationState) -> tuple[ActionRecord, WorldDelta]:
        obj = create_heat_object("farmer", f"unique_{i}", float(10 + i * 3))
        state.objects[obj.id] = obj
        kinds = ["explore", "craft", "connect", "mutate", "vote"]
        action = ActionRecord(
            "entropy_bot",
            kinds[i % len(kinds)],
            {"object_id": obj.id, "index": i},
            timestamp=time.time() + i * (0.5 + (i % 3) * 0.1),
        )
        interactions = []
        if i > 0 and len(state.objects) > 1:
            keys = list(state.objects.keys())
            from cpow_engine.models import InteractionResult

            interactions.append(
                InteractionResult(
                    source_id=keys[-1],
                    target_id=keys[0],
                    effect_type="heat_transfer",
                    magnitude=1.0,
                    energy_delta=2.0,
                )
            )
        return action, WorldDelta(tick=i, objects_added=[obj.id], interactions=interactions)

    report.scenarios.append(
        _run_scenario(
            "macro_clicker",
            "uniform_interval + identical payload — bot_risk 높음, 초기 에너지 일부 유출",
            macro_clicker,
            steps=steps,
        )
    )
    report.scenarios.append(
        _run_scenario(
            "fingerprint_spam",
            "동일 fingerprint 반복 — creativity_score 급락하지만 raw_energy는 남음",
            fingerprint_spam,
            steps=steps,
        )
    )
    report.scenarios.append(
        _run_scenario(
            "diversity_farmer",
            "행동·오브젝트 다양화 — bot_risk 우회, complexity/entropy 보너스 노림",
            diversity_farmer,
            steps=steps,
        )
    )

    farmer = report.scenarios[-1]
    macro = report.scenarios[0]
    if farmer.flagged_bot_ratio < 0.3 and farmer.avg_energy > macro.avg_energy * 0.5:
        report.recommendations.append(
            "diversity_farmer: 행동 타입 로테이션만으로 bot_risk 우회 가능 — "
            "창조 품질·에리어 활동 연동 강화 필요"
        )
    if report.scenarios[1].avg_energy > 0:
        report.recommendations.append(
            "fingerprint_spam: 중복 fingerprint는 creativity 감쇄되나 "
            "creation_bonus_per_object는 별도 — 펄스/합의 게이트 유지"
        )
    if macro.flagged_bot_ratio < 0.8:
        report.recommendations.append(
            "macro_clicker: bot_threshold 또는 interval_uniformity 가중치 상향 검토"
        )

    return report
