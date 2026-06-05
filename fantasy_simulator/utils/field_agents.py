"""Field ecology — living NPCs/monsters on the spatial grid (ecology game mode)."""

from __future__ import annotations

import copy
import random
import uuid
from pathlib import Path
from typing import Any

from utils.spatial import load_world_maps, pois_at_tile, resolve_zone_from_world


def load_ecology_config(base_dir: str | Path) -> dict[str, Any]:
    import json

    path = Path(base_dir) / "config" / "field_ecology.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def ecology_enabled(state: dict[str, Any]) -> bool:
    mode = state.get("flags", {}).get("game_mode", "story")
    return mode in ("ecology", "hybrid")


def get_agents(state: dict[str, Any]) -> list[dict[str, Any]]:
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    agents = eco.setdefault("agents", [])
    return agents  # type: ignore[return-value]


def agents_on_map(state: dict[str, Any], map_id: str) -> list[dict[str, Any]]:
    return [a for a in get_agents(state) if a.get("map_id") == map_id]


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
    instance = {
        "instance_id": f"{archetype_id}_{uuid.uuid4().hex[:8]}",
        "archetype_id": archetype_id,
        "kind": arch.get("kind", "monster"),
        "map_id": map_id,
        "x": int(x),
        "y": int(y),
        "hp": 40,
        "max_hp": 40,
        "goal": "patrol",
        "skills": list(arch.get("skills", [])),
        "skill_cooldowns": {},
        "traits": list(arch.get("traits", [])),
        "ai": arch.get("ai", "patrol"),
        "plunder": {"npc_victims": 0, "power_bonus": 0, "absorbed_skills": []},
    }
    if arch.get("kind") == "monster" and "plunder_growth" in arch.get("traits", []):
        instance["goal"] = "hunt_prey"
    if arch.get("kind") == "npc" and "settlement" in arch.get("traits", []):
        instance["goal"] = "build_hamlet"
        instance["settlement"] = {
            "site_x": x,
            "site_y": y,
            "stage": 0,
            "build_points": 0,
            "stage_id": "camp",
        }
    get_agents(state).append(instance)
    return instance


def ensure_ecology_seeds(state: dict[str, Any], *, base_dir: str | Path) -> None:
    """Spawn starter agents once per session in ecology mode."""
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    if eco.get("initialized"):
        return
    cfg = load_ecology_config(base_dir)
    maps_cfg = load_world_maps(str(base_dir)).get("maps", {})
    if "forest_01" in maps_cfg:
        m = maps_cfg["forest_01"]
        spawn_archetype(
            state, "shadow_predator", map_id="forest_01", x=30, y=20, base_dir=base_dir
        )
    if "ashpoint_01" in maps_cfg:
        spawn_archetype(
            state, "village_elder_builder", map_id="ashpoint_01", x=45, y=35, base_dir=base_dir
        )
        spawn_archetype(
            state, "innkeeper_civilian", map_id="ashpoint_01", x=38, y=32, base_dir=base_dir
        )
    eco["initialized"] = True


def _manhattan(a: dict[str, Any], b: dict[str, Any]) -> int:
    return abs(int(a["x"]) - int(b["x"])) + abs(int(a["y"]) - int(b["y"]))


def _move_toward(agent: dict[str, Any], tx: int, ty: int, maps: dict[str, Any]) -> None:
    m = maps.get(agent["map_id"], {})
    w, h = int(m.get("width", 1)), int(m.get("height", 1))
    x, y = int(agent["x"]), int(agent["y"])
    if x < tx:
        x += 1
    elif x > tx:
        x -= 1
    if y < ty:
        y += 1
    elif y > ty:
        y -= 1
    agent["x"] = max(0, min(w - 1, x))
    agent["y"] = max(0, min(h - 1, y))


def _tick_predator(
    agent: dict[str, Any],
    others: list[dict[str, Any]],
    maps: dict[str, Any],
    rng: random.Random,
) -> list[str]:
    lines: list[str] = []
    prey = [o for o in others if o["instance_id"] != agent["instance_id"] and o.get("kind") == "npc"]
    if prey:
        target = min(prey, key=lambda p: _manhattan(agent, p))
        if _manhattan(agent, target) <= 1:
            dmg = 12 + int(agent.get("plunder", {}).get("power_bonus", 0))
            target["hp"] = int(target.get("hp", 30)) - dmg
            lines.append(
                f"[필드] {agent['archetype_id']}이(가) {target['archetype_id']}을(를) 습격했다."
            )
            if int(target["hp"]) <= 0:
                pl = agent.setdefault("plunder", {})
                pl["npc_victims"] = int(pl.get("npc_victims", 0)) + 1
                pl["power_bonus"] = int(pl.get("power_bonus", 0)) + 3
                lines.append(f"[필드] {target['archetype_id']}이(가) 쓰러졌다. 몬스터가 성장한다.")
                others.remove(target)
            return lines
        _move_toward(agent, int(target["x"]), int(target["y"]), maps)
        return lines
    agent["x"] = int(agent["x"]) + rng.choice([-1, 0, 1])
    agent["y"] = int(agent["y"]) + rng.choice([-1, 0, 1])
    return lines


def _tick_builder(agent: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    settle = agent.get("settlement")
    if not settle:
        return lines
    settle["build_points"] = int(settle.get("build_points", 0)) + 5
    stages = cfg.get("settlement_stages", [])
    for st in stages:
        if int(settle["build_points"]) >= int(st.get("build_points", 9999)):
            settle["stage_id"] = st["id"]
    lines.append(
        f"[필드] 건설 진행: {settle.get('stage_id')} ({settle['build_points']}pt) "
        f"@ ({settle.get('site_x')},{settle.get('site_y')})"
    )
    return lines


def tick_field_ecology(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> list[str]:
    """One ecology beat for current map zone — agents act, world may change."""
    if not ecology_enabled(state):
        return []
    r = rng or random.Random()
    ensure_ecology_seeds(state, base_dir=base_dir)
    cfg = load_ecology_config(base_dir)
    maps = load_world_maps(str(base_dir)).get("maps", {})
    world = state.get("world", {})
    map_id = world.get("map_id", "ashpoint_01")
    agents = [a for a in get_agents(state) if a.get("map_id") == map_id]
    lines: list[str] = []

    for agent in list(agents):
        ai = agent.get("ai", "")
        if ai == "predator_patrol":
            lines.extend(_tick_predator(agent, get_agents(state), maps, r))
        elif ai == "builder":
            lines.extend(_tick_builder(agent, cfg))
        elif ai == "flee_predator":
            preds = [a for a in get_agents(state) if a.get("ai") == "predator_patrol"]
            if preds:
                p = preds[0]
                _move_toward(agent, int(agent["x"]) - (int(p["x"]) - int(agent["x"])), int(agent["y"]), maps)

    zone = resolve_zone_from_world(world)
    if lines:
        state.setdefault("flags", {}).setdefault("ecology", {})["last_tick_zone"] = zone
    return lines


def agents_manifest(state: dict[str, Any], map_id: str) -> list[dict[str, Any]]:
    """Godot spawn list — positions in tiles + godot pixel hint."""
    out: list[dict[str, Any]] = []
    for a in agents_on_map(state, map_id):
        out.append(
            {
                "instance_id": a.get("instance_id"),
                "archetype_id": a.get("archetype_id"),
                "kind": a.get("kind"),
                "x": int(a.get("x", 0)),
                "y": int(a.get("y", 0)),
                "hp": int(a.get("hp", 1)),
                "max_hp": int(a.get("max_hp", 1)),
                "goal": a.get("goal"),
                "skills": a.get("skills", []),
                "settlement": a.get("settlement"),
                "plunder": a.get("plunder"),
            }
        )
    return out
