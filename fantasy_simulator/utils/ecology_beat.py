"""Unified ecology beat — field agents, macro systems, kingdom upkeep."""

from __future__ import annotations

import random
from typing import Any

from utils.field_agents import ecology_enabled, tick_field_ecology
from utils.parallel_beat import parallel_beat_enabled, run_world_parallel_beat
from utils.settlement_build import tick_player_build_projects


def run_ecology_beat(
    state: dict[str, Any],
    *,
    base_dir: Any,
    turn: int,
    rng: random.Random | None = None,
) -> list[str]:
    """One ecology beat: parallel lane when enabled, else sequential fan-out."""
    if not ecology_enabled(state):
        return []
    if parallel_beat_enabled(state, base_dir=base_dir):
        return run_world_parallel_beat(state, base_dir=base_dir, turn=turn, rng=rng)

    from utils.civilization_coupling import tick_civilization_coupling
    from utils.kingdom_system import tick_kingdom
    from utils.regional_resources import tick_regional_regen
    from utils.world_conflicts import tick_world_conflicts

    lines = list(tick_field_ecology(state, base_dir=base_dir, rng=rng))
    lines.extend(tick_regional_regen(state, base_dir=base_dir))
    lines.extend(tick_player_build_projects(state, base_dir=base_dir))
    lines.extend(tick_kingdom(state, base_dir=base_dir))
    lines.extend(tick_civilization_coupling(state, base_dir=base_dir, rng=rng))
    lines.extend(tick_world_conflicts(state, base_dir=base_dir, rng=rng))
    return lines
