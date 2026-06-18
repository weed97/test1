"""에리어 NPC — 창조력 위임·농사 등 작업 수행."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from cpow_engine.areas.powers import UserPowers, creation_cost_for_object
from cpow_engine.models import CreativeObject, PropertyDef
from cpow_engine.physics import create_heat_object


class NpcTask(str, Enum):
    IDLE = "idle"
    FARM = "farm"
    GUARD = "guard"

    @classmethod
    def from_str(cls, value: str) -> NpcTask:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.IDLE


ALLOWED_NPC_TASKS = frozenset({NpcTask.FARM, NpcTask.GUARD})


@dataclass
class AreaNpc:
    npc_id: str
    label: str
    owner_id: str
    task: NpcTask = NpcTask.IDLE
    creation_allocation: float = 0.0
    creation_gauge: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "label": self.label,
            "owner_id": self.owner_id,
            "task": self.task.value,
            "creation_allocation": round(self.creation_allocation, 2),
            "creation_gauge": round(self.creation_gauge, 2),
            "created_at": self.created_at,
        }


def new_npc_id() -> str:
    return f"npc_{uuid.uuid4().hex[:10]}"


def spawn_npc_record(owner_id: str, label: str) -> AreaNpc:
    return AreaNpc(npc_id=new_npc_id(), label=label, owner_id=owner_id)


def allocate_creation(npc: AreaNpc, owner_powers: UserPowers, amount: float) -> tuple[bool, str]:
    if amount <= 0.0:
        return False, "invalid_amount"
    if owner_powers.creation_gauge < amount:
        return False, "insufficient_creation_power"
    if not owner_powers.spend_creation(amount):
        return False, "insufficient_creation_power"
    npc.creation_allocation += amount
    npc.creation_gauge += amount
    return True, "allocated"


def withdraw_creation(npc: AreaNpc, owner_powers: UserPowers, amount: float) -> tuple[bool, str]:
    if amount <= 0.0:
        return False, "invalid_amount"
    if npc.creation_gauge < amount:
        return False, "insufficient_npc_gauge"
    npc.creation_gauge -= amount
    npc.creation_allocation = max(0.0, npc.creation_allocation - amount)
    owner_powers.creation_gauge = min(
        owner_powers.creation_gauge + amount,
        owner_powers.effective_creation_cap(),
        owner_powers.creation_gauge_max,
    )
    return True, "withdrawn"


def build_farm_plot(npc: AreaNpc) -> CreativeObject | None:
    """농사 작업 — 낮은 열의 작물 밭 오브젝트."""
    heat = 8.0
    cost = creation_cost_for_object(heat)
    if npc.creation_gauge < cost:
        return None
    plot = create_heat_object(npc.npc_id, f"{npc.label}의 밭", heat_intensity=heat)
    plot.properties.append(PropertyDef(name="crop_plot", value=1.0, unit="farm"))
    plot.properties.append(PropertyDef(name="is_npc_creation", value=1.0, unit="flag"))
    plot.properties.append(PropertyDef(name="npc_owner", value=0.0, unit=npc.owner_id))
    return plot


def spend_npc_creation(npc: AreaNpc, amount: float) -> bool:
    if amount > npc.creation_gauge:
        return False
    npc.creation_gauge -= amount
    return True


@dataclass
class NpcTickResult:
    ok: bool
    npc_id: str
    task: str = ""
    reason: str = ""
    object_id: str = ""
    creation_spent: float = 0.0


def tick_npc_farm(npc: AreaNpc) -> tuple[NpcTickResult, CreativeObject | None, float]:
    if npc.task != NpcTask.FARM:
        return NpcTickResult(False, npc.npc_id, reason="not_farming"), None, 0.0

    plot = build_farm_plot(npc)
    if plot is None:
        return NpcTickResult(False, npc.npc_id, task="farm", reason="insufficient_npc_gauge"), None, 0.0

    heat = plot.get_property("heat_intensity")
    heat_val = heat.value if heat else 8.0
    cost = creation_cost_for_object(heat_val)
    if not spend_npc_creation(npc, cost):
        return NpcTickResult(False, npc.npc_id, task="farm", reason="insufficient_npc_gauge"), None, 0.0

    return (
        NpcTickResult(
            True,
            npc.npc_id,
            task="farm",
            reason="farm_plot_ready",
            creation_spent=cost,
        ),
        plot,
        cost,
    )
