"""Continuous simulation tick — world clock, ecology, siege on real elapsed time."""

from __future__ import annotations

import random
from typing import Any

from utils.faction_engine import FactionEngine
from utils.field_agents import ecology_enabled, tick_field_ecology
from utils.main_story_engine import MainStoryEngine
from utils.parallel_beat import parallel_beat_enabled, run_world_parallel_beat
from utils.settlement_build import tick_player_build_projects
from utils.sim_clock import load_sim_clock_config, sim_clock_enabled
from utils.temporal import format_clock_line
from utils.world_clock import advance_world_minutes, ensure_world_clock
from utils.world_tension import passive_drift


def _run_ecology_beat(
    state: dict[str, Any],
    *,
    base_dir: Any,
    turn: int,
    rng: random.Random | None,
) -> list[str]:
    if not ecology_enabled(state):
        return []
    if parallel_beat_enabled(state, base_dir=base_dir):
        return run_world_parallel_beat(state, base_dir=base_dir, turn=turn, rng=rng)
    lines = list(tick_field_ecology(state, base_dir=base_dir, rng=rng))
    lines.extend(tick_player_build_projects(state, base_dir=base_dir))
    from utils.civilization_coupling import tick_civilization_coupling
    from utils.world_conflicts import tick_world_conflicts

    lines.extend(tick_civilization_coupling(state, base_dir=base_dir, rng=rng))
    lines.extend(tick_world_conflicts(state, base_dir=base_dir, rng=rng))
    return lines


def tick_simulation(
    state: dict[str, Any],
    *,
    dt_real_seconds: float,
    base_dir: Any,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Advance world systems by real elapsed seconds × realtime_scale."""
    empty: dict[str, Any] = {
        "ok": False,
        "lines": [],
        "sim_minutes": 0.0,
        "siege_simulation": None,
        "new_siege_events": [],
        "ecology_beat": False,
    }
    if not sim_clock_enabled(state, base_dir=base_dir):
        empty["error"] = "sim_clock disabled"
        return empty

    cfg = load_sim_clock_config(base_dir)
    sc = state.setdefault("meta", {}).setdefault("sim_clock", {})
    scale = float(sc.get("realtime_scale", cfg.get("realtime_scale", 12)))
    max_dt = float(cfg.get("max_tick_real_ms", 5000)) / 1000.0
    dt_real = min(max(0.0, float(dt_real_seconds)), max_dt)
    if dt_real <= 0:
        empty["ok"] = True
        empty["dt_real_seconds"] = 0.0
        empty["clock"] = format_clock_line(state.get("world", {}))
        return empty

    sim_minutes = (dt_real * scale) / 60.0
    sc["total_real_seconds"] = float(sc.get("total_real_seconds", 0.0)) + dt_real
    sc["total_sim_minutes"] = float(sc.get("total_sim_minutes", 0.0)) + sim_minutes

    ensure_world_clock(state["world"])
    sc["minute_accum"] = float(sc.get("minute_accum", 0.0)) + sim_minutes
    whole_minutes = int(sc["minute_accum"])
    sc["minute_accum"] = float(sc["minute_accum"]) - whole_minutes
    if whole_minutes > 0:
        advance_world_minutes(state["world"], whole_minutes)

    rng = rng or random.Random()
    FactionEngine(base_dir).ensure_initialized(state)
    lines: list[str] = []

    eco_interval = float(cfg.get("ecology_minutes_per_beat", 5))
    sc["ecology_accum"] = float(sc.get("ecology_accum", 0.0)) + sim_minutes
    ecology_beat = False
    turn = int(state.get("turn", 0))
    while sc["ecology_accum"] >= eco_interval:
        sc["ecology_accum"] -= eco_interval
        lines.extend(_run_ecology_beat(state, base_dir=base_dir, turn=turn, rng=rng))
        ecology_beat = True

    tension_interval = float(cfg.get("tension_drift_minutes", 30))
    sc["tension_accum"] = float(sc.get("tension_accum", 0.0)) + sim_minutes
    if sc["tension_accum"] >= tension_interval:
        sc["tension_accum"] = float(sc["tension_accum"]) % tension_interval
        _, tension_note = passive_drift(state, rng=rng)
        if tension_note:
            lines.append(tension_note)

    story_interval = float(cfg.get("main_story_tick_minutes", 60))
    sc["story_accum"] = float(sc.get("story_accum", 0.0)) + sim_minutes
    if sc["story_accum"] >= story_interval:
        sc["story_accum"] = float(sc["story_accum"]) % story_interval
        lines.extend(MainStoryEngine(base_dir).tick(state, turn=turn))

    from utils.kingdom_war import tick_siege_for_sim_minutes

    siege = tick_siege_for_sim_minutes(
        state,
        sim_minutes=sim_minutes,
        base_dir=base_dir,
        rng=rng,
        sim_clock_cfg=cfg,
    )
    lines.extend(siege.get("lines", []))

    return {
        "ok": True,
        "dt_real_seconds": dt_real,
        "sim_minutes": round(sim_minutes, 4),
        "whole_minutes": whole_minutes,
        "realtime_scale": scale,
        "clock": format_clock_line(state["world"]),
        "world": {
            "day": state["world"].get("day"),
            "time_of_day": state["world"].get("time_of_day"),
            "minute_of_day": state["world"].get("minute_of_day"),
            "tension": state["world"].get("tension"),
        },
        "lines": lines,
        "ecology_beat": ecology_beat,
        "siege_simulation": siege.get("simulation"),
        "new_siege_events": siege.get("new_events", []),
    }
