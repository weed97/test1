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


def _is_sovereign_holder(agent: dict[str, Any] | None, *, base_dir: str | Path) -> bool:
    if not agent:
        return False
    if agent.get("world_sovereign_holder"):
        return True
    sov = load_parallel_config(base_dir).get("sovereign_siege", {})
    holder = str(sov.get("holder_archetype_id", "npc_arthur_pendragon"))
    return str(agent.get("archetype_id", "")) == holder or str(agent.get("instance_id", "")) == holder


def _uses_precision_combat(actor: dict[str, Any], target: dict[str, Any]) -> bool:
    """Ecology 잡몹은 plan base_damage — 아서·정예·프리셋만 정밀 전투."""
    for agent in (actor, target):
        if agent.get("combatant_preset") or agent.get("world_apex_rank"):
            return True
        if agent.get("world_sovereign_holder") or agent.get("archetype_id") == "npc_arthur_pendragon":
            return True
    return False


def _pack_group_key(agent: dict[str, Any] | None, actor_id: str) -> str:
    if not agent:
        return f"solo:{actor_id}"
    pack = agent.get("pack") or {}
    pid = pack.get("pack_id")
    if pid:
        return f"pack:{pid}"
    return f"solo:{actor_id}"


def attach_presentation_schedule(
    plans: list[dict[str, Any]],
    agents_by_id: dict[str, dict[str, Any]],
    *,
    base_dir: str | Path,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Godot hints: same sim beat, staggered motion so agents do not feel lock-step."""
    pres = load_parallel_config(base_dir).get("presentation", {})
    min_ms = int(pres.get("stagger_ms_min", 0))
    max_ms = int(pres.get("stagger_ms_max", 480))
    slot_ms = int(pres.get("slot_ms", 72))
    jitter = int(pres.get("jitter_per_actor_ms", 40))
    combat_sync = int(pres.get("combat_sync_window_ms", 90))
    group_by_pack = bool(pres.get("group_by_pack", True))
    shuffle_waves = bool(pres.get("shuffle_wave_order", True))

    group_to_wave: dict[str, int] = {}
    wave_ids: list[int] = []
    for pl in plans:
        actor = agents_by_id.get(str(pl.get("actor_id", "")))
        gkey = _pack_group_key(actor, str(pl.get("actor_id", ""))) if group_by_pack else str(pl["actor_id"])
        if gkey not in group_to_wave:
            group_to_wave[gkey] = len(wave_ids)
            wave_ids.append(group_to_wave[gkey])

    wave_order = list(wave_ids)
    if shuffle_waves:
        rng.shuffle(wave_order)
    wave_slot = {w: i for i, w in enumerate(wave_order)}

    # Shared target → narrow combat band (hits feel simultaneous, not wander timing).
    target_band: dict[str, int] = {}
    combat_idx = 0
    for pl in plans:
        if pl.get("action") in ("attack", "skill") and pl.get("target_id"):
            tid = str(pl["target_id"])
            if tid not in target_band:
                target_band[tid] = combat_idx
                combat_idx += 1

    schedule: list[dict[str, Any]] = []
    for pl in plans:
        actor_id = str(pl["actor_id"])
        actor = agents_by_id.get(actor_id)
        gkey = _pack_group_key(actor, actor_id) if group_by_pack else actor_id
        wave = group_to_wave.get(gkey, 0)
        slot = wave_slot.get(wave, 0)
        delay = min(max_ms, min_ms + slot * slot_ms + rng.randint(0, max(0, jitter)))

        act = pl.get("action")
        if act in ("attack", "skill") and pl.get("target_id"):
            tid = str(pl["target_id"])
            band = target_band.get(tid, 0)
            delay = min(max_ms, min_ms + band * max(12, combat_sync // 4) + rng.randint(0, combat_sync))
            pl["presentation_group"] = f"combat:{tid}"
        else:
            pl["presentation_group"] = gkey

        pl["presentation_delay_ms"] = delay
        pl["presentation_wave"] = wave
        schedule.append(
            {
                "actor_id": actor_id,
                "action": act,
                "target_id": pl.get("target_id"),
                "delay_ms": delay,
                "wave": wave,
                "group": pl["presentation_group"],
            }
        )

    schedule.sort(key=lambda e: int(e.get("delay_ms", 0)))
    return schedule


def ecology_beat_presentation(state: dict[str, Any]) -> dict[str, Any] | None:
    """Last beat presentation schedule for clients (Godot tween offsets)."""
    eco = state.get("flags", {}).get("ecology", {})
    beat = eco.get("last_parallel_beat")
    if not isinstance(beat, dict):
        return None
    sched = beat.get("presentation_schedule")
    if not sched:
        return None
    return {
        "beat_mode": eco.get("beat_mode", "parallel"),
        "map_id": beat.get("map_id"),
        "duration_ms": beat.get("presentation_duration_ms"),
        "schedule": sched,
    }


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

    enemies_near = sum(
        1
        for o in others
        if o.get("instance_id") != agent.get("instance_id")
        and _manhattan(agent, o) <= 3
        and agent.get("relations", {}).get(o.get("instance_id"), "hostile") != "ally"
    )
    sk = _pick_skill(
        agent, target, base_dir=base_dir, distance=dist, enemy_count=max(1, enemies_near), rng=rng
    )
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
        sov_siege = pcfg.get("sovereign_siege", {})
        if not (
            _is_sovereign_holder(target, base_dir=base_dir)
            and sov_siege.get("no_attacker_cap")
        ):
            atk_plans = atk_plans[: int(fld.get("max_attackers_per_target", 4))]
        total = 0
        for pl in atk_plans:
            actor = agents_by_id.get(str(pl["actor_id"]))
            if not actor:
                continue
            tgt_label = pl.get("target_label", tid)
            alabel = pl.get("actor_label", pl["actor_id"])
            if pl["action"] == "skill":
                from utils.ecology_objects import skill_definition
                from utils.skill_effects import (
                    apply_buff_from_skill,
                    apply_damage_with_buffs,
                    is_buff_skill,
                )

                sk = str(pl["skill_id"])
                sdef = skill_definition(sk, base_dir=base_dir)
                dmg = preview_skill_damage(actor, target, sk, base_dir=base_dir, rng=rng)
                commit_skill_costs(actor, sk, base_dir=base_dir)
                if is_buff_skill(sdef):
                    apply_buff_from_skill(actor, sk, sdef, base_dir=base_dir)
                    strike_lines.append(f"[버프] {alabel} : {sk}")
                    continue
                strike_lines.append(
                    f"[스킬] {alabel} → {tgt_label} : {sk} ({dmg} 피해)"
                )
                total += dmg
            else:
                dmg = int(pl.get("base_damage", 5))
                if _uses_precision_combat(actor, target):
                    try:
                        from utils.combat_stats import agent_to_combatant, strike_damage_hp

                        dmg = strike_damage_hp(
                            agent_to_combatant(actor, base_dir=base_dir),
                            agent_to_combatant(target, base_dir=base_dir),
                            base_dir=base_dir,
                            rng=rng,
                        )
                    except (OSError, KeyError, ValueError):
                        dmg = int(pl.get("base_damage", 5))
                if dmg <= 0:
                    dmg = int(pl.get("base_damage", 5))
                total += dmg
                strike_lines.append(f"[전투] {alabel} → {tgt_label} : 타격 ({dmg})")
            mp_regen = 1 + _iq(actor) // 25
            actor["mp"] = min(int(actor.get("max_mp", 10)), int(actor.get("mp", 0)) + mp_regen)

        pending_damage[tid] = int(total * scale)

    from utils.skill_effects import apply_damage_with_buffs

    for tid, dmg in pending_damage.items():
        target = agents_by_id.get(tid)
        if not target:
            continue
        dealt = apply_damage_with_buffs(target, dmg, base_dir=base_dir)
        target["hp"] = int(target.get("hp", 1)) - dealt
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
    from utils.field_agents import ecology_rng, persist_ecology_rng

    r = ecology_rng(state, rng)
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
    lines: list[str] = []
    from utils.skill_effects import tick_agent_buffs

    for agent in list(agents_by_id.values()):
        lines.extend(tick_agent_buffs(agent, base_dir=base_dir))
    for agent in list(agents_by_id.values()):
        pl = plan_agent_beat(
            agent, agents_by_id, maps, base_dir=base_dir, rng=r, eco_cfg=eco_cfg
        )
        if pl:
            plans.append(pl)

    presentation = attach_presentation_schedule(
        plans, agents_by_id, base_dir=base_dir, rng=r
    )
    duration_ms = max((int(e["delay_ms"]) for e in presentation), default=0)

    lines.extend(
        resolve_and_commit_field_beat(
            plans,
            agents_by_id,
            maps,
            state=state,
            base_dir=base_dir,
            rng=r,
            eco_cfg=eco_cfg,
        )
    )
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    eco["last_parallel_beat"] = {
        "map_id": map_id,
        "plans": len(plans),
        "survivors": len(agents_by_id),
        "presentation_schedule": presentation,
        "presentation_duration_ms": duration_ms,
    }
    persist_ecology_rng(state, r)
    return lines


def run_macro_parallel_lanes(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    turn: int,
    rng: random.Random | None = None,
) -> list[str]:
    """Macro systems: disjoint state keys, same beat snapshot spirit."""
    from utils.field_agents import ecology_rng, persist_ecology_rng

    r = ecology_rng(state, rng)
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
    persist_ecology_rng(state, r)
    return lines


def run_world_parallel_beat(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    turn: int,
    rng: random.Random | None = None,
) -> list[str]:
    """Full ecology beat: field (parallel) + competition + macro lanes."""
    from utils.field_agents import ecology_rng, persist_ecology_rng, tick_field_ecology

    r = ecology_rng(state, rng)
    lines: list[str] = []
    lines.extend(tick_field_ecology(state, base_dir=base_dir, rng=r))
    lines.extend(run_macro_parallel_lanes(state, base_dir=base_dir, turn=turn, rng=r))
    persist_ecology_rng(state, r)
    world = state.get("world", {})
    zone = resolve_zone_from_world(world)
    if lines:
        state.setdefault("flags", {}).setdefault("ecology", {})["last_tick_zone"] = zone
        state["flags"]["ecology"]["beat_mode"] = "parallel"
    return lines
