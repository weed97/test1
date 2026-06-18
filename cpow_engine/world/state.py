"""에리어 월드 런타임 상태."""

from __future__ import annotations

from dataclasses import dataclass, field

from cpow_engine.world.hazards import HazardState
from cpow_engine.world.mining import MiningProfile


@dataclass
class AreaWorldRuntime:
    area_id: str
    world_seed: str
    cell_hazards: dict[tuple[int, int], HazardState] = field(default_factory=dict)
    miners: dict[str, MiningProfile] = field(default_factory=dict)
    world_tick: int = 0

    def hazard_state_for(self, cell_x: int, cell_z: int) -> HazardState:
        key = (cell_x, cell_z)
        if key not in self.cell_hazards:
            self.cell_hazards[key] = HazardState()
        return self.cell_hazards[key]

    def miner_profile(self, user_id: str) -> MiningProfile:
        if user_id not in self.miners:
            self.miners[user_id] = MiningProfile(user_id=user_id)
        return self.miners[user_id]

    def to_dict(self) -> dict:
        return {
            "area_id": self.area_id,
            "world_seed": self.world_seed,
            "world_tick": self.world_tick,
            "miner_count": len(self.miners),
            "hazard_cells": len(self.cell_hazards),
        }
