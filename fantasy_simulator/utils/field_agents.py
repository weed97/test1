"""Field ecology — ecology_agent objects, intelligence, skills (Godot = sprites)."""

from __future__ import annotations

import random
import uuid
from pathlib import Path
from typing import Any

from utils.agent_mind import tick_agent_mind
from utils.monster_pack import refresh_pack_alphas
from utils.ecology_objects import (
    agent_object_manifest,
    build_ecology_agent,
    enrich_evolved_agent,
    load_ecology_config,
    normalize_agent,
)
from utils.progression import (
    can_spawn_agent,
    grant_evolution_xp,
    load_progression_config,
    spawn_evolved_monster,
)
from utils.agent_competition import attach_society, tick_agent_competition
from utils.spatial import load_world_maps, resolve_zone_from_world


def ecology_enabled(state: dict[str, Any]) -> bool:
    mode = state.get("flags", {}).get("game_mode", "story")
    return mode in ("ecology", "hybrid")


def get_agents(state: dict[str, Any]) -> list[dict[str, Any]]:
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    agents = eco.setdefault("agents", [])
    return agents  # type: ignore[return-value]


def agents_on_map(state: dict[str, Any], map_id: str) -> list[dict[str, Any]]:
    return [a for a in get_agents(state) if a.get("map_id") == map_id]


def get_agent_by_id(state: dict[str, Any], instance_id: str) -> dict[str, Any] | None:
    for a in get_agents(state):
        if a.get("instance_id") == instance_id:
            return a
    return None


def spawn_archetype(
    state: dict[str, Any],
    archetype_id: str,
    *,
    map_id: str,
    x: int,
    y: int,
    base_dir: str | Path,
) -> dict[str, Any] | None:
    cfg = load_ecology_config(base_dir)
    arch = cfg.get("archetypes", {}).get(archetype_id)
    if not arch:
        return None
    ok, _reason = can_spawn_agent(
        state,
        map_id=map_id,
        kind=str(arch.get("kind", "monster")),
        species_id=archetype_id,
        base_dir=base_dir,
    )
    if not ok:
        return None
    agent = build_ecology_agent(
        archetype_id=archetype_id,
        kind=str(arch.get("kind", "monster")),
        map_id=map_id,
        x=x,
        y=y,
        base_dir=base_dir,
        label=arch.get("label"),
        ai=arch.get("ai"),
        traits=list(arch.get("traits", [])),
    )
    if arch.get("kind") == "npc" and "settlement" in arch.get("traits", []):
        agent["goal"] = "build_hamlet"
        agent["settlement"] = {
            "site_x": x,
            "site_y": y,
            "stage": 0,
            "build_points": 0,
            "stage_id": "camp",
        }
    get_agents(state).append(agent)
    attach_society(agent, base_dir=base_dir)
    return agent


def ensure_ecology_seeds(state: dict[str, Any], *, base_dir: str | Path) -> None:
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    if eco.get("initialized"):
        return
    maps_cfg = load_world_maps(str(base_dir)).get("maps", {})
    if "forest_01" in maps_cfg:
        for gx, gy in ((28, 22), (35, 18), (22, 25)):
            spawn_evolved_monster(
                state,
                "goblin",
                map_id="forest_01",
                x=gx,
                y=gy,
                tier=1,
                base_dir=base_dir,
            )
        spawn_evolved_monster(
            state,
            "shadow_beast",
            map_id="forest_01",
            x=30,
            y=20,
            tier=1,
            base_dir=base_dir,
        )
        for a in agents_on_map(state, "forest_01"):
            if a.get("evolution_chain"):
                attach_society(a, base_dir=base_dir)
    if "ashpoint_01" in maps_cfg:
        spawn_archetype(
            state, "village_elder_builder", map_id="ashpoint_01", x=45, y=35, base_dir=base_dir
        )
        spawn_archetype(
            state, "innkeeper_civilian", map_id="ashpoint_01", x=38, y=32, base_dir=base_dir
        )
    eco["initialized"] = True


def tick_field_ecology(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> list[str]:
    if not ecology_enabled(state):
        return []
    r = rng or random.Random()
    ensure_ecology_seeds(state, base_dir=base_dir)
    cfg = load_ecology_config(base_dir)
    maps = load_world_maps(str(base_dir)).get("maps", {})
    world = state.get("world", {})
    map_id = world.get("map_id", "ashpoint_01")
    all_agents = get_agents(state)
    map_agents = [a for a in all_agents if a.get("map_id") == map_id]
    refresh_pack_alphas(map_agents, base_dir=base_dir)
    lines: list[str] = []

    for agent in list(map_agents):
        normalize_agent(agent, base_dir=base_dir)
        lines.extend(
            tick_agent_mind(
                agent,
                all_agents,
                maps,
                state=state,
                base_dir=base_dir,
                rng=r,
                eco_cfg=cfg,
            )
        )

    lines.extend(tick_agent_competition(state, map_id, base_dir=base_dir, rng=r))

    zone = resolve_zone_from_world(world)
    if lines:
        state.setdefault("flags", {}).setdefault("ecology", {})["last_tick_zone"] = zone
    return lines


def agents_manifest(
    state: dict[str, Any],
    map_id: str,
    *,
    base_dir: str | Path | None = None,
    instance_id: str | None = None,
) -> list[dict[str, Any]]:
    root = base_dir or Path(__file__).resolve().parent.parent
    out: list[dict[str, Any]] = []
    for a in agents_on_map(state, map_id):
        if instance_id and a.get("instance_id") != instance_id:
            continue
        normalize_agent(a, base_dir=root)
        out.append(agent_object_manifest(a))
    return out
