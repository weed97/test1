"""균열·몬스터 반응 — 파괴가 세계에 미치는 영향."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


MIGRATION_RIFT_THRESHOLD = 35.0
MONSTER_ATTACK_THRESHOLD = 8.0


@dataclass
class RiftEvent:
    destroyer_id: str
    object_id: str
    durability_destroyed: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class RiftState:
    """파괴로 열린 균열 — 몬스터가 파괴자를 추적."""

    level: float = 0.0
    monster_threat: float = 0.0
    targeted_destroyers: list[str] = field(default_factory=list)
    events: list[RiftEvent] = field(default_factory=list)

    def on_destruction(
        self,
        destroyer_id: str,
        object_id: str,
        durability: float,
    ) -> dict[str, float | bool]:
        self.level += durability * 0.1
        self.monster_threat += durability * 0.07
        if destroyer_id not in self.targeted_destroyers:
            self.targeted_destroyers.append(destroyer_id)
        self.events.append(RiftEvent(destroyer_id, object_id, durability))
        if len(self.events) > 50:
            self.events.pop(0)
        return {
            "rift_level": self.level,
            "monster_threat": self.monster_threat,
            "monsters_attacking": self.monster_threat >= MONSTER_ATTACK_THRESHOLD,
            "migration_recommended": self.level >= MIGRATION_RIFT_THRESHOLD,
        }

    def defend(self, defender_id: str, power_spent: float) -> float:
        """파괴력으로 균열·몬스터 위협을 억제."""
        reduction = power_spent * 1.4
        self.monster_threat = max(0.0, self.monster_threat - reduction)
        self.level = max(0.0, self.level - power_spent * 0.05)
        if self.monster_threat < MONSTER_ATTACK_THRESHOLD * 0.5:
            self.targeted_destroyers.clear()
        return reduction

    def to_dict(self) -> dict:
        return {
            "level": round(self.level, 2),
            "monster_threat": round(self.monster_threat, 2),
            "monsters_attacking": self.monster_threat >= MONSTER_ATTACK_THRESHOLD,
            "migration_recommended": self.level >= MIGRATION_RIFT_THRESHOLD,
            "targeted_destroyers": list(self.targeted_destroyers),
            "recent_events": len(self.events),
        }


@dataclass
class CarriedCore:
    """핵심 코어를 다른 지역으로 옮겨 복원."""

    carrier_id: str
    source_area_id: str
    label: str
    creation_investment: float
    durability: float
    heat_baseline: float

    def to_dict(self) -> dict:
        return {
            "carrier_id": self.carrier_id,
            "source_area_id": self.source_area_id,
            "label": self.label,
            "creation_investment": self.creation_investment,
            "durability": self.durability,
            "heat_baseline": self.heat_baseline,
        }
