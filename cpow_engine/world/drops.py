"""월드 좌표 드롭 — 채굴 위치 시각화·줍기."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class WorldDrop:
    drop_id: str
    ore_id: str
    amount: float
    x: float
    z: float
    actor_id: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "drop_id": self.drop_id,
            "ore_id": self.ore_id,
            "amount": round(self.amount, 3),
            "x": round(self.x, 2),
            "z": round(self.z, 2),
            "actor_id": self.actor_id,
            "created_at": self.created_at,
        }


@dataclass
class DropRegistry:
    _drops: dict[str, WorldDrop] = field(default_factory=dict)
    max_drops: int = 512

    def spawn(
        self,
        ore_id: str,
        amount: float,
        x: float,
        z: float,
        actor_id: str,
    ) -> WorldDrop:
        while len(self._drops) >= self.max_drops:
            oldest = min(self._drops.values(), key=lambda d: d.created_at)
            self._drops.pop(oldest.drop_id, None)
        drop = WorldDrop(
            drop_id=f"drop_{uuid.uuid4().hex[:10]}",
            ore_id=ore_id,
            amount=amount,
            x=x,
            z=z,
            actor_id=actor_id,
        )
        self._drops[drop.drop_id] = drop
        return drop

    def get(self, drop_id: str) -> WorldDrop | None:
        return self._drops.get(drop_id)

    def remove(self, drop_id: str) -> WorldDrop | None:
        return self._drops.pop(drop_id, None)

    def count(self) -> int:
        return len(self._drops)

    def in_radius(self, x: float, z: float, radius: float) -> list[WorldDrop]:
        r2 = radius * radius
        out: list[WorldDrop] = []
        for drop in self._drops.values():
            dx = drop.x - x
            dz = drop.z - z
            if dx * dx + dz * dz <= r2:
                out.append(drop)
        return out

    def to_dict(self) -> dict:
        return {
            "count": len(self._drops),
            "drops": [d.to_dict() for d in self._drops.values()],
        }
