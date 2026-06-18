"""Playtime ↔ simulation clock — realtime_scale drives in-world minutes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.config_loader import load_config

from utils.field_agents import ecology_enabled


def load_sim_clock_config(base_dir: str | Path) -> dict[str, Any]:
    return load_config(base_dir, "sim_clock.json")


def _sim_meta(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("meta", {}).setdefault("sim_clock", {})


def sim_clock_enabled(state: dict[str, Any], *, base_dir: str | Path) -> bool:
    """Continuous sim clock active (ecology + siege on dt, not explore turns)."""
    if not ecology_enabled(state):
        return False
    sc = state.get("meta", {}).get("sim_clock")
    if sc is None:
        return False
    return bool(sc.get("enabled", False))


def enable_sim_clock(state: dict[str, Any], *, base_dir: str | Path) -> None:
    cfg = load_sim_clock_config(base_dir)
    sc = _sim_meta(state)
    sc["enabled"] = True
    sc.setdefault("realtime_scale", float(cfg.get("realtime_scale", 12)))
    sc.setdefault("total_real_seconds", 0.0)
    sc.setdefault("total_sim_minutes", 0.0)
    sc.setdefault("minute_accum", 0.0)
    sc.setdefault("ecology_accum", 0.0)
    sc.setdefault("tension_accum", 0.0)
    sc.setdefault("story_accum", 0.0)
    sc.setdefault("siege_accum", 0.0)
    sc.setdefault("siege_t_cursor_ms", 0)


def sim_clock_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    cfg = load_sim_clock_config(base_dir)
    sc = _sim_meta(state)
    world = state.get("world", {})
    return {
        "enabled": sim_clock_enabled(state, base_dir=base_dir),
        "realtime_scale": float(sc.get("realtime_scale", cfg.get("realtime_scale", 12))),
        "total_sim_minutes": round(float(sc.get("total_sim_minutes", 0.0)), 2),
        "total_real_seconds": round(float(sc.get("total_real_seconds", 0.0)), 2),
        "minute_of_day": world.get("minute_of_day"),
        "day": world.get("day"),
        "time_of_day": world.get("time_of_day"),
    }
