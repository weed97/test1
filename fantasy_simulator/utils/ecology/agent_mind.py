"""Agent intelligence — relations, strategy, skill combat."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from utils.ecology_objects import (
    load_ecology_config,
    load_intelligence_config,
    skill_definition,
)
from utils.monster_pack import (
    apply_monster_kill_growth,
    ensure_pack_block,
    load_pack_config,
    refresh_pack_alphas,
)
from utils.progression import grant_evolution_xp, load_progression_config


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


def decay_skill_cooldowns(agent: dict[str, Any]) -> None:
    cds = agent.setdefault("skill_cooldowns", {})
    for sk in list(cds.keys()):
        if int(cds[sk]) > 0:
            cds[sk] = int(cds[sk]) - 1


def update_relations(
    agent: dict[str, Any],
    others: list[dict[str, Any]],
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> None:
    icfg = load_intelligence_config(base_dir)
    pcfg = load_pack_config(base_dir)
    rel_cfg = pcfg.get("relations", {})
    rel = agent.setdefault("relations", {})
    my_civ = agent.get("civilization_id")
    rival_pairs = {
        tuple(sorted(p)) for p in icfg.get("civilization_relations", {}).get("rivals", [])
    }
    r = rng or random.Random()

    for o in others:
        if o["instance_id"] == agent["instance_id"]:
            continue
        oid = o["instance_id"]
        o_civ = o.get("civilization_id")

        if agent.get("kind") == "monster" and o.get("kind") == "monster":
            if my_civ and o_civ and my_civ == o_civ:
                mate_chance = float(rel_cfg.get("packmate_chance_same_civ", 0.07))
                if r.random() < mate_chance:
                    rel[oid] = "packmate"
                else:
                    rel[oid] = str(rel_cfg.get("same_civ_monster_default", "rival"))
            else:
                rel[oid] = "hostile"
            continue

        if my_civ and o_civ:
            if my_civ == o_civ and agent.get("kind") == "npc":
                rel[oid] = "ally"
                continue
            if tuple(sorted([my_civ, o_civ])) in rival_pairs:
                rel[oid] = "hostile"
                continue
        if agent.get("kind") == "monster" and o.get("kind") == "npc":
            rel[oid] = "hostile"
        elif agent.get("kind") == "npc" and o.get("kind") == "monster":
            rel[oid] = "hostile"
        else:
            rel.setdefault(oid, "neutral")


def _iq(agent: dict[str, Any]) -> int:
    return int(agent.get("intelligence", {}).get("iq", 50))


def _strategy_id(agent: dict[str, Any]) -> str:
    return str(agent.get("intelligence", {}).get("strategy", "predator_pack"))


def _pick_skill(
    agent: dict[str, Any],
    target: dict[str, Any],
    *,
    base_dir: str | Path,
    distance: int,
    enemy_count: int = 1,
    rng: random.Random | None = None,
) -> str | None:
    from utils.combat_skill_ai import pick_combat_skill

    merged = list(dict.fromkeys((agent.get("unlocked_skills") or []) + list(agent.get("skills", []))))
    agent = dict(agent)
    agent["skills"] = merged
    return pick_combat_skill(
        agent,
        target,
        base_dir=base_dir,
        distance=distance,
        rng=rng,
        enemy_count=enemy_count,
    )


def preview_skill_damage(
    attacker: dict[str, Any],
    target: dict[str, Any],
    skill_id: str,
    *,
    base_dir: str | Path,
    rng: random.Random,
) -> int:
    from utils.ecology_objects import is_sovereign_skill

    sdef = skill_definition(skill_id, base_dir=base_dir)
    if "build_progress" in sdef.get("tags", []):
        return 0
    if is_sovereign_skill(sdef) or attacker.get("world_sovereign_holder") or attacker.get(
        "archetype_id"
    ) == "npc_arthur_pendragon":
        try:
            from utils.combat_precision import from_milli, load_combat_precision_config
            from utils.combat_stats import agent_to_combatant, preview_arthur_skill_damage

            atk = agent_to_combatant(attacker, base_dir=base_dir)
            defn = agent_to_combatant(target, base_dir=base_dir)
            preview = preview_arthur_skill_damage(
                atk, defn, skill_id, base_dir=base_dir, rng=rng
            )
            cfg = load_combat_precision_config(base_dir)
            dmg_hp = int(
                round(from_milli(int(preview.get("damage_milli", 0)), cfg=cfg))
            )
            if preview.get("pipeline") != "world_edict":
                return max(0, dmg_hp)
            return 0
        except (OSError, KeyError, json.JSONDecodeError, TypeError, ValueError):
            pass
    try:
        from utils.combat_stats import agent_to_combatant, strike_damage_hp

        atk = agent_to_combatant(attacker, base_dir=base_dir)
        defn = agent_to_combatant(target, base_dir=base_dir)
        plunder = int(attacker.get("plunder", {}).get("power_bonus", 0))
        if sdef.get("combat_pipeline") == "catalog":
            from utils.level_unlocks import hero_level_snapshot
            from utils.skill_catalog import effective_skill_power

            snap = hero_level_snapshot(attacker, base_dir=base_dir)
            eff = effective_skill_power(sdef, hero_levels=snap)
            mult = eff / 10.0 + plunder * 0.02
        else:
            mult = float(sdef.get("power", 8)) / 10.0 + plunder * 0.02
        mult *= 0.9 + rng.uniform(0, 0.2) + _iq(attacker) / 500.0
        dmg = strike_damage_hp(atk, defn, base_dir=base_dir, rng=rng, skill_multiplier=mult)
        if dmg > 0:
            return dmg
    except (OSError, KeyError, json.JSONDecodeError, TypeError, ValueError):
        pass
    iq_bonus = 1.0 + (_iq(attacker) / 100.0) * 0.15
    plunder = int(attacker.get("plunder", {}).get("power_bonus", 0))
    base_pwr = float(sdef.get("power", 8)) + plunder * 0.5
    variance = rng.uniform(0.9, 1.1 + _iq(attacker) / 200.0)
    return max(1, int(base_pwr * iq_bonus * variance))


def commit_skill_costs(attacker: dict[str, Any], skill_id: str, *, base_dir: str | Path) -> None:
    sdef = skill_definition(skill_id, base_dir=base_dir)
    cost = int(sdef.get("mana_cost", 0))
    attacker["mp"] = max(0, int(attacker.get("mp", 0)) - cost)
    attacker.setdefault("skill_cooldowns", {})[skill_id] = int(
        sdef.get("cooldown_beats", 2)
    )


def use_skill(
    attacker: dict[str, Any],
    target: dict[str, Any],
    skill_id: str,
    *,
    base_dir: str | Path,
    rng: random.Random,
) -> tuple[int, str]:
    from utils.skill_effects import (
        apply_buff_from_skill,
        apply_damage_with_buffs,
        is_buff_skill,
    )

    sdef = skill_definition(skill_id, base_dir=base_dir)
    dmg = preview_skill_damage(attacker, target, skill_id, base_dir=base_dir, rng=rng)
    commit_skill_costs(attacker, skill_id, base_dir=base_dir)
    if is_buff_skill(sdef):
        apply_buff_from_skill(attacker, skill_id, sdef, base_dir=base_dir)
        return 0, skill_id
    if dmg > 0:
        dealt = apply_damage_with_buffs(target, dmg, base_dir=base_dir)
        target["hp"] = int(target.get("hp", 1)) - dealt
        return dealt, skill_id
    return dmg, skill_id


def _should_flee(agent: dict[str, Any], *, base_dir: str | Path) -> bool:
    icfg = load_intelligence_config(base_dir)
    strat = icfg.get("strategies", {}).get(_strategy_id(agent), {})
    ratio = float(strat.get("flee_below_hp_ratio", 0.2))
    mhp = max(1, int(agent.get("max_hp", 1)))
    return int(agent.get("hp", 0)) / mhp <= ratio


def _monster_greed(agent: dict[str, Any], *, base_dir: str | Path) -> int:
    if agent.get("kind") != "monster":
        return 0
    pack = ensure_pack_block(agent, base_dir=base_dir)
    return int(pack.get("greed", load_pack_config(base_dir)["greed"].get("default", 70)))


def _pick_target(
    agent: dict[str, Any],
    others: list[dict[str, Any]],
    *,
    base_dir: str | Path,
) -> dict[str, Any] | None:
    icfg = load_intelligence_config(base_dir)
    pcfg = load_pack_config(base_dir)
    gr = pcfg.get("greed", {})
    strat = icfg.get("strategies", {}).get(_strategy_id(agent), {})
    priorities = strat.get("target_priority", ["npc"])
    rel = agent.get("relations", {})
    candidates: list[dict[str, Any]] = []
    greed = _monster_greed(agent, base_dir=base_dir)

    for o in others:
        if o["instance_id"] == agent["instance_id"]:
            continue
        stance = rel.get(o["instance_id"], "neutral")
        if stance in ("ally", "packmate"):
            continue
        if agent.get("kind") == "monster":
            if o.get("kind") == "monster":
                candidates.append(o)
            elif o.get("kind") == "npc" and stance == "hostile":
                candidates.append(o)
        elif stance == "hostile":
            candidates.append(o)

    if not candidates:
        return None

    def score_target(t: dict[str, Any]) -> float:
        s = 100.0 - _manhattan(agent, t) * 5
        stance = rel.get(t["instance_id"], "neutral")
        if t.get("kind") == "monster":
            if t.get("civilization_id") != agent.get("civilization_id"):
                s += float(gr.get("target_weight_monster_rival", 28))
            elif stance in ("rival", "hostile"):
                s += float(gr.get("target_weight_same_pack_rival", 32))
            s += float(gr.get("target_weight_other_monster", 20))
            if "monster_rival" in priorities:
                s += 12
            if "same_pack_rival" in priorities:
                s += 14
        if t.get("kind") == "npc":
            s += float(gr.get("target_weight_npc", 16)) * max(0.3, 1.0 - greed / 120.0)
        if t.get("pack", {}).get("role") == "alpha":
            s += 8
        s += (100 - int(t.get("hp", 50))) * 0.2
        s += greed * 0.15 + _iq(agent) * 0.08
        return s

    return max(candidates, key=score_target)


def agent_plan_priority(agent: dict[str, Any]) -> int:
    pack = agent.get("pack", {})
    return _iq(agent) + int(pack.get("dominance", 0)) + int(agent.get("evolution_tier", 1)) * 5


def count_nearby_threats(
    agent: dict[str, Any], others: list[dict[str, Any]], *, radius: int = 3
) -> int:
    """Threats for skill selection — excludes allies and packmates."""
    return sum(
        1
        for o in others
        if o["instance_id"] != agent["instance_id"]
        and _manhattan(agent, o) <= radius
        and agent.get("relations", {}).get(o["instance_id"], "neutral")
        not in ("ally", "packmate")
    )


def _base_melee_damage(agent: dict[str, Any]) -> int:
    return (
        8
        + int(agent.get("stats", {}).get("str", 10) // 3)
        + int(agent.get("plunder", {}).get("power_bonus", 0))
    )


def _nearby_ally(
    agent: dict[str, Any], others: list[dict[str, Any]], *, max_dist: int = 3
) -> dict[str, Any] | None:
    for o in others:
        if agent.get("relations", {}).get(o["instance_id"]) == "ally":
            if _manhattan(agent, o) <= max_dist:
                return o
    return None


def plan_agent_action(
    agent: dict[str, Any],
    others: list[dict[str, Any]],
    *,
    base_dir: str | Path,
    rng: random.Random,
    priority: int | None = None,
) -> dict[str, Any]:
    """Decide the next agent action without mutating world state (shared by sequential + parallel)."""
    decay_skill_cooldowns(agent)
    update_relations(agent, others, base_dir=base_dir, rng=rng)

    label = agent.get("label") or agent.get("archetype_id", "agent")
    plan: dict[str, Any] = {
        "actor_id": agent["instance_id"],
        "actor_label": label,
        "priority": priority if priority is not None else agent_plan_priority(agent),
    }

    if _should_flee(agent, base_dir=base_dir):
        preds = [o for o in others if o.get("kind") == "monster"]
        if preds:
            plan["action"] = "flee"
            plan["flee_from"] = preds[0]["instance_id"]
            return plan
        plan["action"] = "wander"
        plan["dx"] = rng.choice([-1, 0, 1])
        plan["dy"] = rng.choice([-1, 0, 1])
        return plan

    if agent.get("ai") == "builder" and agent.get("settlement"):
        plan["action"] = "build"
        ally = _nearby_ally(agent, others)
        if ally:
            sk = _pick_skill(
                agent,
                ally,
                base_dir=base_dir,
                distance=_manhattan(agent, ally),
                rng=rng,
            )
            if sk:
                plan["builder_skill_id"] = sk
                plan["builder_ally_id"] = ally["instance_id"]
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

    sk = _pick_skill(
        agent,
        target,
        base_dir=base_dir,
        distance=dist,
        enemy_count=max(1, count_nearby_threats(agent, others)),
        rng=rng,
    )
    if sk:
        plan["action"] = "skill"
        plan["skill_id"] = sk
    else:
        plan["action"] = "attack"
        plan["base_damage"] = _base_melee_damage(agent)
    return plan


def _lines_after_kill(
    agent: dict[str, Any],
    target: dict[str, Any],
    others: list[dict[str, Any]],
    *,
    state: dict[str, Any],
    base_dir: str | Path,
    rng: random.Random,
    tgt_label: str,
) -> list[str]:
    lines = [f"[전투] {tgt_label} 쓰러짐."]
    if agent.get("kind") == "monster" and target.get("kind") == "monster":
        lines.extend(
            apply_monster_kill_growth(agent, target, others, base_dir=base_dir, state=state)
        )
        prog_cfg = load_progression_config(base_dir)
        xp = int(prog_cfg.get("evolution_xp_per_plunder", 15))
        lines.extend(grant_evolution_xp(agent, xp, base_dir=base_dir))
    elif agent.get("kind") == "monster" and target.get("kind") == "npc":
        pl = agent.setdefault("plunder", {})
        pl["npc_victims"] = int(pl.get("npc_victims", 0)) + 1
        pl["power_bonus"] = int(pl.get("power_bonus", 0)) + 3
        prog_cfg = load_progression_config(base_dir)
        xp = int(prog_cfg.get("evolution_xp_per_plunder", 15))
        lines.extend(grant_evolution_xp(agent, xp, base_dir=base_dir))
        from utils.agent_competition import get_civilization_state, load_civ_config

        civ_id = agent.get("civilization_id")
        if civ_id:
            ccfg = load_civ_config(base_dir)
            cdef = ccfg.get("civilizations", {}).get(civ_id, {})
            gain = int(cdef.get("prosperity_per_npc_plunder", 8))
            cs = get_civilization_state(state, civ_id)
            cs["prosperity"] = int(cs.get("prosperity", 0)) + gain
        state.setdefault("flags", {}).setdefault("ecology", {})["last_predator_npc_kill"] = True
    if target in others:
        others.remove(target)
    return lines


def execute_agent_plan_sequential(
    agent: dict[str, Any],
    plan: dict[str, Any],
    others: list[dict[str, Any]],
    maps: dict[str, Any],
    *,
    state: dict[str, Any],
    base_dir: str | Path,
    rng: random.Random,
    eco_cfg: dict[str, Any],
) -> list[str]:
    """Apply one agent plan immediately (sequential ecology tick)."""
    lines: list[str] = []
    label = plan.get("actor_label") or agent.get("label") or agent.get("archetype_id", "agent")
    action = plan.get("action")

    if action == "flee":
        foe_id = plan.get("flee_from")
        foe = next((o for o in others if o.get("instance_id") == foe_id), None)
        if foe is None:
            preds = [o for o in others if o.get("kind") == "monster"]
            foe = preds[0] if preds else None
        if foe:
            _move_toward(
                agent,
                int(agent["x"]) - (int(foe["x"]) - int(agent["x"])),
                int(agent["y"]),
                maps,
            )
            lines.append(f"[지성] {label} — 위협을 피해 후퇴 (HP 낮음).")
        return lines

    if action == "build":
        settle = agent.get("settlement")
        if settle:
            ally_id = plan.get("builder_ally_id")
            sk = plan.get("builder_skill_id")
            if sk and ally_id:
                ally = next((o for o in others if o.get("instance_id") == ally_id), None)
                if ally:
                    _, sid = use_skill(agent, ally, str(sk), base_dir=base_dir, rng=rng)
                    lines.append(f"[스킬] {label} → {ally.get('label', 'ally')} : {sid}")
            settle["build_points"] = int(settle.get("build_points", 0)) + 5 + _iq(agent) // 20
            for st in eco_cfg.get("settlement_stages", []):
                if int(settle["build_points"]) >= int(st.get("build_points", 9999)):
                    settle["stage_id"] = st["id"]
            lines.append(
                f"[필드] 건설 {settle.get('stage_id')} ({settle['build_points']}pt)"
            )
        return lines

    if action == "wander":
        dx = int(plan.get("dx", 0))
        dy = int(plan.get("dy", 0))
        if dx == 0 and dy == 0:
            dx = rng.choice([-1, 0, 1])
            dy = rng.choice([-1, 0, 1])
        agent["x"] = int(agent["x"]) + dx
        agent["y"] = int(agent["y"]) + dy
        return lines

    if action == "move" and plan.get("move_to"):
        mt = plan["move_to"]
        _move_toward(agent, int(mt[0]), int(mt[1]), maps)
        return lines

    target = next((o for o in others if o.get("instance_id") == plan.get("target_id")), None)
    if target is None:
        return lines

    tgt_label = plan.get("target_label") or target.get("label") or target.get("archetype_id", "target")

    if action == "skill" and plan.get("skill_id"):
        sk = str(plan["skill_id"])
        dmg, sid = use_skill(agent, target, sk, base_dir=base_dir, rng=rng)
        lines.append(
            f"[스킬] {label} → {tgt_label} : {sid} ({dmg} 피해, MP {agent.get('mp')})"
        )
    elif action == "attack":
        dmg = int(plan.get("base_damage", _base_melee_damage(agent)))
        target["hp"] = int(target.get("hp", 1)) - dmg
        lines.append(f"[전투] {label} → {tgt_label} : 타격 ({dmg})")

    if int(target.get("hp", 0)) <= 0:
        lines.extend(
            _lines_after_kill(
                agent,
                target,
                others,
                state=state,
                base_dir=base_dir,
                rng=rng,
                tgt_label=tgt_label,
            )
        )

    mp_regen = 1 + _iq(agent) // 25
    agent["mp"] = min(int(agent.get("max_mp", 10)), int(agent.get("mp", 0)) + mp_regen)
    return lines


def tick_agent_mind(
    agent: dict[str, Any],
    others: list[dict[str, Any]],
    maps: dict[str, Any],
    *,
    state: dict[str, Any],
    base_dir: str | Path,
    rng: random.Random,
    eco_cfg: dict[str, Any],
) -> list[str]:
    from utils.skill_effects import tick_agent_buffs

    lines = list(tick_agent_buffs(agent, base_dir=base_dir))
    plan = plan_agent_action(agent, others, base_dir=base_dir, rng=rng)
    lines.extend(
        execute_agent_plan_sequential(
            agent,
            plan,
            others,
            maps,
            state=state,
            base_dir=base_dir,
            rng=rng,
            eco_cfg=eco_cfg,
        )
    )
    return lines
