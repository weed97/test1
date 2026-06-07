"""Per-turn world simulation hooks — tension drift and main story tick."""

from __future__ import annotations

import random
from typing import Any

from utils.faction_engine import FactionEngine
from utils.main_story_engine import MainStoryEngine
from utils.field_agents import ecology_enabled, tick_field_ecology
from utils.settlement_build import tick_player_build_projects
from utils.world_tension import passive_drift


def tick_world_systems(
    state: dict[str, Any],
    *,
    base_dir: Any,
    turn: int,
    rng: random.Random | None = None,
    temporal_mode: str = "classic",
    minutes_advanced: int = 0,
) -> list[str]:
    """Run lightweight end-of-turn world updates."""
    lines: list[str] = []
    FactionEngine(base_dir).ensure_initialized(state)

    _, tension_note = passive_drift(state, rng=rng)
    if tension_note:
        lines.append(tension_note)

    main = MainStoryEngine(base_dir)
    lines.extend(main.tick(state, turn=turn))
    if ecology_enabled(state):
        from utils.parallel_beat import parallel_beat_enabled, run_world_parallel_beat

        if parallel_beat_enabled(state, base_dir=base_dir):
            lines.extend(
                run_world_parallel_beat(state, base_dir=base_dir, turn=turn, rng=rng)
            )
        else:
            lines.extend(tick_field_ecology(state, base_dir=base_dir, rng=rng))
            lines.extend(tick_player_build_projects(state, base_dir=base_dir))
            from utils.civilization_coupling import tick_civilization_coupling
            from utils.world_conflicts import tick_world_conflicts

            lines.extend(tick_civilization_coupling(state, base_dir=base_dir, rng=rng))
            lines.extend(tick_world_conflicts(state, base_dir=base_dir, rng=rng))
    else:
        lines.extend(tick_field_ecology(state, base_dir=base_dir, rng=rng))

    from utils.kingdom_war import simulate_kingdom_wars_for_turn

    siege = simulate_kingdom_wars_for_turn(
        state,
        turn=turn,
        temporal_mode=temporal_mode,
        minutes_advanced=minutes_advanced,
        base_dir=base_dir,
        rng=rng,
    )
    lines.extend(siege.get("lines", []))
    if siege.get("simulation"):
        state.setdefault("flags", {}).setdefault("ecology", {})["_last_siege_sim"] = siege[
            "simulation"
        ]
    return lines
