"""지역 경제·문명 — 에리어 성장에 따른 시스템."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


CIVILIZATION_STAGES: list[dict[str, str | int]] = [
    {"level": 0, "name": "wilderness", "label": "황야"},
    {"level": 1, "name": "campfire", "label": "모닥불 거점"},
    {"level": 2, "name": "workshop", "label": "작업장"},
    {"level": 3, "name": "settlement", "label": "정착지"},
    {"level": 4, "name": "trade_hub", "label": "교역 거점"},
    {"level": 5, "name": "civilization", "label": "문명 권역"},
]


@dataclass
class RegionalEconomy:
    """에리어 단위 에너지·문명 지표."""

    treasury: float = 0.0
    civilization_level: int = 0
    population: int = 0
    trade_volume: float = 0.0
    systems_unlocked: list[str] = field(default_factory=list)

    def refresh(
        self,
        *,
        object_count: int,
        contributor_count: int,
        energy_pool: float,
        tick: int,
    ) -> None:
        score = (
            math.log2(1 + object_count) * 1.2
            + contributor_count * 0.8
            + energy_pool / 400.0
            + tick * 0.05
        )
        self.civilization_level = min(5, int(score))
        self.population = max(contributor_count, object_count // 2)
        self.treasury += energy_pool * 0.02
        self.trade_volume = self.treasury * 0.1 * self.civilization_level
        self.systems_unlocked = self._systems_for_level(self.civilization_level)

    def _systems_for_level(self, level: int) -> list[str]:
        systems: list[str] = []
        if level >= 1:
            systems.append("energy_exchange")
        if level >= 2:
            systems.append("material_craft")
        if level >= 3:
            systems.append("collab_governance")
        if level >= 4:
            systems.append("regional_trade")
        if level >= 5:
            systems.append("civilization_protocol")
        return systems

    def stage(self) -> dict[str, str | int]:
        idx = min(self.civilization_level, len(CIVILIZATION_STAGES) - 1)
        return CIVILIZATION_STAGES[idx]

    def to_dict(self) -> dict:
        stage = self.stage()
        return {
            "treasury": round(self.treasury, 2),
            "civilization_level": self.civilization_level,
            "civilization_stage": stage["name"],
            "civilization_label": stage["label"],
            "population": self.population,
            "trade_volume": round(self.trade_volume, 2),
            "systems_unlocked": list(self.systems_unlocked),
        }
