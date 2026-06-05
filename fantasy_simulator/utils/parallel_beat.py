"""Parallel simulation beat — plan all agents, resolve together, commit once."""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any

from utils.agent_mind import (
    _iq,
    _manhattan,
    _pick_skill,
    _pick_target,
    _should_flee,
    commit_skill_costs,
    decay_skill_cooldowns,
    preview_skill_damage,
    update_relations,
)
from utils.ecology_objects import load_ecology_config, normalize_agent
from utils.field_agents import ecology_enabled, ensure_ecology_seeds, get_agents
from utils.monster_pack import refresh_pack_alphas
from utils.spatial import load_world_maps, resolve_zone_from_world


def load_parallel_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "parallel_beat.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parallel_beat_enabled(state: dict[str, Any], *, base_dir: str | Path) -> bool:
    eco = state.get("flags", {}).get("ecology", {})
    if "parallel_beat" in eco:
        return bool(eco["parallel_beat"])
    return bool(load_parallel_config(base_dir).get("enabled_by_default_in_ecology", True))


def _plan_priority(agent: dict[str, Any], *, base_dir: str | Path) -> int:
    pack = agent.get("pack", {})
    return _iq(agent) + int(pack.get("dominance", 0)) + int(agent.get("evolution_tier", 1)) * 5


def plan_agent_beat(
    agent: dict[str, Any],
    agents_by_id: dict[str, dict[str, Any]],
    maps: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random,
    eco_cfg: dict[str, Any],
) -> dict[str, Any] | None:
    """Plan only — no world mutation."""
    decay_skill_cooldowns(agent)
    others = [a for i, a in agents_by_id.items() if i != agent["instance_id"]]
    update_relations(agent, others, base_dir=base_dir, rng=rng)

    label = agent.get("label") or agent.get("archetype_id", "agent")
    plan: dict[str, Any] = {
        "actor_id": agent["instance_id"],
        "actor_label": label,
        "priority": _plan_priority(agent, base_dir=base_dir),
    }

    if _should_flee(agent, base_dir=base_dir):
        preds = [o for o in others if o.get("kind") == "monster"]
        if preds:
            p = preds[0]
            plan["action"] = "flee"
            plan["flee_from"] = p["instance_id"]
            return plan
        plan["action"] = "wander"
        return plan

    if agent.get("ai") == "builder" and agent.get("settlement"):
        plan["action"] = "build"
        return plan

    target = _pick_target(agent, others, base_dir=base_dir)
    if not target:
        plan["action"] = "wander"
        plan["dx"] = rng.choice([-1, 0, 1])
        plan["dy"] = rng.choice([-1, 0, 1])
        return plan

    dist = _manhattan(agent, target)
    plan["target_id"] = target["instance_id"]
    plan["target_label"] = target.get("label") or target.get("archetype_id", "target")

    if dist > 1:
        plan["action"] = "move"
        plan["move_to"] = [int(target["x"]), int(target["y"])]
        return plan

    sk = _pick_skill(agent, target, base_dir=base_dir, distance=dist)
    if sk:
        plan["action"] = "skill"
        plan["skill_id"] = sk
    else:
        plan["action"] = "attack"
        plan["base_damage"] = 8 + int(agent.get("stats", {}).get("str", 10) // 3)
        plan["base_damage"] += int(agent.get("plunder", {}).get("power_bonus", 0))
    return plan


def _apply_move(
    agent: dict[str, Any],
    tx: int,
    ty: int,
    maps: dict[str, Any],
    occupied: set[tuple[str, int, int]],
) -> tuple[int, int]:
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
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))
    key = (str(agent["map_id"]), x, y)
    if key in occupied:
        return int(agent["x"]), int(agent["y"])
    occupied.add(key)
    return x, y


def resolve_and_commit_field_beat(
    plans: list[dict[str, Any]],
    agents_by_id: dict[str, dict[str, Any]],
    maps: dict[str, Any],
    *,
    state: dict[str, Any],
    base_dir: str | Path,
    rng: random.Random,
    eco_cfg: dict[str, Any],
) -> list[str]:
    pcfg = load_parallel_config(base_dir)
    fld = pcfg.get("field", {})
    scale = float(fld.get("simultaneous_damage_scale", 1.0))
    lines: list[str] = []
    occupied: set[tuple[str, int, int]] = set()

    # --- Resolve combat (simultaneous strikes on shared targets) ---
    by_target: dict[str, list[dict[str, Any]]] = {}
    for pl in plans:
        if pl.get("action") in ("attack", "skill") and pl.get("target_id"):
            by_target.setdefault(str(pl["target_id"]), []).append(pl)

    pending_damage: dict[str, int] = {}
    strike_lines: list[str] = []
    kills: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for tid, atk_plans in by_target.items():
        target = agents_by_id.get(tid)
        if not target:
            continue
        atk_plans.sort(key=lambda p: -int(p.get("priority", 0)))
        atk_plans = atk_plans[: int(fld.get("max_attackers_per_target", 4))]
        total = 0
        for pl in atk_plans:
            actor = agents_by_id.get(str(pl["actor_id"]))
            if not actor:
                continue
            tgt_label = pl.get("target_label", tid)
            alabel = pl.get("actor_label", pl["actor_id"])
            if pl["action"] == "skill":
                sk = str(pl["skill_id"])
                dmg = preview_skill_damage(actor, target, sk, base_dir=base_dir, rng=rng)
                commit_skill_costs(actor, sk, base_dir=base_dir)
                strike_lines.append(
                    f"[스킬] {alabel} → {tgt_label} : {sk} ({dmg} 피해)"
                )
                total += dmg
            else:
                dmg = int(pl.get("base_damage", 5))
                total += dmg
                strike_lines.append(f"[전투] {alabel} → {tgt_label} : 타격 ({dmg})")
            mp_regen = 1 + _iq(actor) // 25
            actor["mp"] = min(int(actor.get("max_mp", 10)), int(actor.get("mp", 0)) + mp_regen)

        pending_damage[tid] = int(total * scale)

    for tid, dmg in pending_damage.items():
        target = agents_by_id.get(tid)
        if not target:
            continue
        target["hp"] = int(target.get("hp", 1)) - dmg
        if int(target["hp"]) <= 0:
            tgt_label = target.get("label") or tid
            strike_lines.append(f"[전투] {tgt_label} 쓰러짐.")
            for pl in by_target.get(tid, []):
                actor = agents_by_id.get(str(pl["actor_id"]))
                if actor:
                    kills.append((actor, target))

    lines.extend(strike_lines)

    from utils.monster_pack import apply_monster_kill_growth
    from utils.progression import grant_evolution_xp, load_progression_config

    prog_cfg = load_progression_config(base_dir)
    all_agents = list(agents_by_id.values())
    dead_ids = {t["instance_id"] for _, t in kills}

    for actor, target in kills:
        if actor.get("kind") == "monster" and target.get("kind") == "monster":
            lines.extend(
                apply_monster_kill_growth(
                    actor, target, all_agents, base_dir=base_dir, state=state
                )
            )
            lines.extend(
                grant_evolution_xp(
                    actor, int(prog_cfg.get("evolution_xp_per_plunder", 15)), base_dir=base_dir
                )
            )
        elif actor.get("kind") == "monster" and target.get("kind") == "npc":
            pl = actor.setdefault("plunder", {})
            pl["npc_victims"] = int(pl.get("npc_victims", 0)) + 1
            pl["power_bonus"] = int(pl.get("power_bonus", 0)) + 3
            lines.extend(
                grant_evolution_xp(
                    actor, int(prog_cfg.get("evolution_xp_per_plunder", 15)), base_dir=base_dir
                )
            )
            state.setdefault("flags", {}).setdefault("ecology", {})[
                "last_predator_npc_kill"
            ] = True

    for iid in dead_ids:
        agents_by_id.pop(iid, None)

    # --- Movement & other plans (priority order) ---
    non_combat = sorted(
        [p for p in plans if p.get("action") not in ("attack", "skill")],
        key=lambda p: -int(p.get("priority", 0)),
    )
    for pl in non_combat:
        actor = agents_by_id.get(str(pl["actor_id"]))
        if not actor:
            continue
        label = pl.get("actor_label", pl["actor_id"])
        act = pl["action"]
        if act == "flee":
            fid = pl.get("flee_from")
            foe = agents_by_id.get(str(fid)) if fid else None
            if foe:
                tx = int(actor["x"]) - (int(foe["x"]) - int(actor["x"]))
                ty = int(actor["y"])
                x, y = _apply_move(actor, tx, ty, maps, occupied)
                actor["x"], actor["y"] = x, y
                lines.append(f"[지성] {label} — 위협을 피해 후퇴.")
        elif act == "move" and pl.get("move_to"):
            mt = pl["move_to"]
            x, y = _apply_move(actor, int(mt[0]), int(mt[1]), maps, occupied)
            actor["x"], actor["y"] = x, y
        elif act == "build":
            settle = actor.get("settlement")
            if settle:
                settle["build_points"] = int(settle.get("build_points", 0)) + 5 + _iq(actor) // 20
                for st in eco_cfg.get("settlement_stages", []):
                    if int(settle["build_points"]) >= int(st.get("build_points", 9999)):
                        settle["stage_id"] = st["id"]
                lines.append(
                    f"[필드] 건설 {settle.get('stage_id')} ({settle['build_points']}pt)"
                )
        elif act == "wander":
            dx = int(pl.get("dx", 0))
            dy = int(pl.get("dy", 0))
            x, y = _apply_move(
                actor, int(actor["x"]) + dx, int(actor["y"]) + dy, maps, occupied
            )
            actor["x"], actor["y"] = x, y

    state_agents = get_agents(state)
    state_agents[:] = list(agents_by_id.values())
    return lines


def tick_field_ecology_parallel(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> list[str]:
    """Plan → resolve → commit for all agents on active map."""
    r = rng or random.Random()
    ensure_ecology_seeds(state, base_dir=base_dir)
    eco_cfg = load_ecology_config(base_dir)
    maps = load_world_maps(str(base_dir)).get("maps", {})
    map_id = state.get("world", {}).get("map_id", "ashpoint_01")
    map_agents = [a for a in get_agents(state) if a.get("map_id") == map_id]

    for a in map_agents:
        normalize_agent(a, base_dir=base_dir)
    refresh_pack_alphas(map_agents, base_dir=base_dir)

    agents_by_id = {a["instance_id"]: a for a in map_agents}
    plans: list[dict[str, Any]] = []
    for agent in list(agents_by_id.values()):
        pl = plan_agent_beat(
            agent, agents_by_id, maps, base_dir=base_dir, rng=r, eco_cfg=eco_cfg
        )
        if pl:
            plans.append(pl)

    lines = resolve_and_commit_field_beat(
        plans,
        agents_by_id,
        maps,
        state=state,
        base_dir=base_dir,
        rng=r,
        eco_cfg=eco_cfg,
    )
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    eco["last_parallel_beat"] = {
        "map_id": map_id,
        "plans": len(plans),
        "survivors": len(agents_by_id),
    }
    return lines


def run_macro_parallel_lanes(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    turn: int,
    rng: random.Random | None = None,
) -> list[str]:
    """Macro systems: disjoint state keys, same beat snapshot spirit."""
    r = rng or random.Random()
    lines: list[str] = []
    civ_snapshot = copy.deepcopy(
        state.get("flags", {}).get("ecology", {}).get("civilizations", {})
    )

    from utils.settlement_build import tick_player_build_projects
    from utils.civilization_coupling import tick_civilization_coupling
    from utils.world_conflicts import tick_world_conflicts

    lines.extend(tick_player_build_projects(state, base_dir=base_dir))
    lines.extend(tick_civilization_coupling(state, base_dir=base_dir, rng=r))
    lines.extend(tick_world_conflicts(state, base_dir=base_dir, rng=r))

    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    eco["last_macro_parallel"] = {"lanes": 3, "civ_keys_at_plan": len(civ_snapshot)}
    return lines


def run_world_parallel_beat(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    turn: int,
    rng: random.Random | None = None,
) -> list[str]:
    """Full ecology beat: field (parallel) + competition + macro lanes."""
    from utils.field_agents import tick_field_ecology

    r = rng or random.Random()
    lines: list[str] = []
    lines.extend(tick_field_ecology(state, base_dir=base_dir, rng=r))
    lines.extend(run_macro_parallel_lanes(state, base_dir=base_dir, turn=turn, rng=r))
    world = state.get("world", {})
    zone = resolve_zone_from_world(world)
    if lines:
        state.setdefault("flags", {}).setdefault("ecology", {})["last_tick_zone"] = zone
        state["flags"]["ecology"]["beat_mode"] = "parallel"
    return lines
