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
) -> list[str]:
    """Run lightweight end-of-turn world updates."""
    lines: list[str] = []
    FactionEngine(base_dir).ensure_initialized(state)

    _, tension_note = passive_drift(state, rng=rng)
    if tension_note:
        lines.append(tension_note)

    main = MainStoryEngine(base_dir)
    lines.extend(main.tick(state, turn=turn))
    lines.extend(tick_field_ecology(state, base_dir=base_dir, rng=rng))
    if ecology_enabled(state):
        lines.extend(tick_player_build_projects(state, base_dir=base_dir))
    return lines
