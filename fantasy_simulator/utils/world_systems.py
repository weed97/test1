"""Per-turn world simulation hooks — tension drift and main story tick."""

from __future__ import annotations

import random
from typing import Any

from utils.ecology_beat import run_ecology_beat
from utils.faction_engine import FactionEngine
from utils.field_agents import ecology_enabled, tick_field_ecology
from utils.main_story_engine import MainStoryEngine
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

    try:
        from utils.sim_clock import sim_clock_enabled

        if sim_clock_enabled(state, base_dir=base_dir):
            return lines
    except ImportError:
        pass

    _, tension_note = passive_drift(state, rng=rng)
    if tension_note:
        lines.append(tension_note)

    main = MainStoryEngine(base_dir)
    lines.extend(main.tick(state, turn=turn))
    if ecology_enabled(state):
        lines.extend(run_ecology_beat(state, base_dir=base_dir, turn=turn, rng=rng))
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
    return lines
