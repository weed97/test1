"""액터 인벤토리 — SoA 스택 (대규모 경쟁용)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ActorInventory:
    """광물 id → 수량. 채굴 1회마다 오브젝트를 늘리지 않음."""

    actor_id: str
    stacks: dict[str, float] = field(default_factory=dict)

    def add(self, ore_id: str, amount: float) -> float:
        if amount <= 0.0:
            return self.stacks.get(ore_id, 0.0)
        total = round(self.stacks.get(ore_id, 0.0) + amount, 3)
        self.stacks[ore_id] = total
        return total

    def take(self, ore_id: str, amount: float) -> tuple[bool, float]:
        have = self.stacks.get(ore_id, 0.0)
        if amount > have + 1e-9:
            return False, have
        left = round(have - amount, 3)
        if left <= 0.0:
            self.stacks.pop(ore_id, None)
        else:
            self.stacks[ore_id] = left
        return True, left

    def get(self, ore_id: str) -> float:
        return self.stacks.get(ore_id, 0.0)

    def to_dict(self) -> dict:
        return {
            "actor_id": self.actor_id,
            "stacks": dict(sorted(self.stacks.items())),
            "slot_count": len(self.stacks),
        }


@dataclass
class InventoryLedger:
    """에리어 단위 인벤토리 저장소."""

    _actors: dict[str, ActorInventory] = field(default_factory=dict)

    def for_actor(self, actor_id: str) -> ActorInventory:
        if actor_id not in self._actors:
            self._actors[actor_id] = ActorInventory(actor_id=actor_id)
        return self._actors[actor_id]

    def to_public_dict(self, actor_id: str) -> dict:
        return {"ok": True, "inventory": self.for_actor(actor_id).to_dict()}
