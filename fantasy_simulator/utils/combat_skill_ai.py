"""Combat skill selection — catalog, sovereign Arthur, situational buff/debuff/move."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from utils.ecology_objects import skill_definition


def _hp_ratio(agent: dict[str, Any]) -> float:
    mhp = max(1, int(agent.get("max_hp", agent.get("hp", 1))))
    return int(agent.get("hp", mhp)) / mhp


def _usable_skills(
    agent: dict[str, Any],
    *,
    base_dir: str | Path,
    distance: int,
) -> list[tuple[str, dict[str, Any]]]:
    pool = list(dict.fromkeys(agent.get("unlocked_skills") or agent.get("skills") or []))
    out: list[tuple[str, dict[str, Any]]] = []
    for sk_id in pool:
        if int(agent.get("skill_cooldowns", {}).get(sk_id, 0)) > 0:
            continue
        sdef = skill_definition(sk_id, base_dir=base_dir)
        if sdef.get("type") == "passive":
            continue
        tags = set(sdef.get("tags", []))
        if "out_of_combat" in tags or sdef.get("combat_pipeline") == "world_edict":
            continue
        if int(agent.get("mp", 0)) < int(sdef.get("mana_cost", 0)):
            continue
        if distance > int(sdef.get("range_tiles", 1)):
            continue
        out.append((sk_id, sdef))
    return out


def _pick_arthur_skill(
    agent: dict[str, Any],
    target: dict[str, Any],
    *,
    base_dir: str | Path,
    distance: int,
    rng: random.Random,
    enemy_count: int,
) -> str | None:
    skills = {sk: skill_definition(sk, base_dir=base_dir) for sk in agent.get("skills", [])}
    hp_r = _hp_ratio(agent)
    usable = {sk: sd for sk, sd in _usable_skills(agent, base_dir=base_dir, distance=distance)}

    if hp_r <= 0.25 and "excalibur_sovereign_judgment" in usable and enemy_count >= 3:
        return "excalibur_sovereign_judgment"
    if hp_r <= 0.35 and "kings_aegis" in usable:
        return "kings_aegis"
    if enemy_count >= 2 and "sovereign_broad_cleave" in usable:
        return "sovereign_broad_cleave"
    if "sovereign_blade_combo" in usable:
        return "sovereign_blade_combo"
    if usable:
        return max(
            usable.items(),
            key=lambda x: float(x[1].get("power", 0)) + rng.uniform(0, 2),
        )[0]
    return None


def _score_skill(
    sk_id: str,
    sdef: dict[str, Any],
    *,
    agent: dict[str, Any],
    target: dict[str, Any],
    distance: int,
    hp_r: float,
    tgt_hp_r: float,
    preferred_tags: set[str],
    iq: int,
    rng: random.Random,
    base_dir: str | Path,
) -> float:
    tags = set(sdef.get("tags", []))
    cat = str(sdef.get("category", ""))
    score = float(sdef.get("power", 0))

    if sdef.get("combat_pipeline") == "catalog":
        from utils.level_unlocks import hero_level_snapshot
        from utils.skill_catalog import effective_skill_power

        snap = hero_level_snapshot(agent, base_dir=base_dir)
        score = effective_skill_power(sdef, hero_levels=snap)

    score += sum(3.0 for t in tags if t in preferred_tags)
    score += iq / 80.0

    if cat == "attack" or "attack" in tags:
        score += 12.0 + (1.0 - tgt_hp_r) * 8.0
    if cat == "debuff" or "debuff" in tags:
        score += 6.0 + tgt_hp_r * 10.0
    if cat == "buff" or "buff_self" in tags or "buff_ally" in tags:
        score += 4.0 + (1.0 - hp_r) * 18.0
    if cat == "move" or "move" in tags:
        score += max(0, distance - 1) * 14.0
    if cat == "support" or "support" in tags:
        score += 5.0 + iq / 50.0

    if sdef.get("signature"):
        score += 15.0
    if int(sdef.get("tier", 0)) >= 60:
        score += 4.0

    score += rng.uniform(0, 3.5)
    return score


def pick_combat_skill(
    agent: dict[str, Any],
    target: dict[str, Any] | None,
    *,
    base_dir: str | Path,
    distance: int,
    rng: random.Random | None = None,
    enemy_count: int = 1,
    preferred_tags: set[str] | None = None,
) -> str | None:
    """Pick best combat skill for agent vs target at Manhattan distance."""
    r = rng or random.Random()
    if not target:
        return None

    if agent.get("world_sovereign_holder") or agent.get("archetype_id") == "npc_arthur_pendragon":
        arthur_sk = _pick_arthur_skill(
            agent, target, base_dir=base_dir, distance=distance, rng=r, enemy_count=enemy_count
        )
        if arthur_sk:
            return arthur_sk

    from utils.ecology_objects import load_intelligence_config

    iq = int(agent.get("intelligence", {}).get("iq", 50))
    strat_id = str(agent.get("intelligence", {}).get("strategy", "predator_pack"))
    icfg = load_intelligence_config(base_dir)
    strat = icfg.get("strategies", {}).get(strat_id, {})
    pref = preferred_tags or set(strat.get("preferred_tags", []))
    hp_r = _hp_ratio(agent)
    tgt_hp_r = _hp_ratio(target)

    usable = _usable_skills(agent, base_dir=base_dir, distance=distance)
    if not usable:
        move_pool = [
            (sk, sd)
            for sk in agent.get("unlocked_skills") or agent.get("skills") or []
            for sd in [skill_definition(sk, base_dir=base_dir)]
            if "move" in sd.get("tags", []) or sd.get("category") == "move"
        ]
        if move_pool and distance > 1:
            return move_pool[0][0]
        return None

    best: tuple[float, str] | None = None
    for sk_id, sdef in usable:
        sc = _score_skill(
            sk_id,
            sdef,
            agent=agent,
            target=target,
            distance=distance,
            hp_r=hp_r,
            tgt_hp_r=tgt_hp_r,
            preferred_tags=pref,
            iq=iq,
            rng=r,
            base_dir=base_dir,
        )
        if best is None or sc > best[0]:
            best = (sc, sk_id)
    return best[1] if best else None
