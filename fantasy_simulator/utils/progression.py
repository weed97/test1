"""Character progression — jobs, skills, equipment, monster evolution, spawn caps."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from utils.config_loader import load_config

def _ecology_enabled(state: dict[str, Any]) -> bool:
    mode = state.get("flags", {}).get("game_mode", "story")
    return mode in ("ecology", "hybrid")


def _get_agents(state: dict[str, Any]) -> list[dict[str, Any]]:
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    agents = eco.setdefault("agents", [])
    return agents  # type: ignore[return-value]


def load_progression_config(base_dir: str | Path) -> dict[str, Any]:
    return load_config(base_dir, "progression.json")


def _eco_prog(state: dict[str, Any]) -> dict[str, Any]:
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    return eco.setdefault("progression", {})


def party_character_ids(state: dict[str, Any]) -> set[str]:
    party = list(state.get("party", []) or state.get("active_characters", []))
    prog = _eco_prog(state).get("heroes", {})
    return set(party) | set(prog.keys())


def get_hero_progress(
    state: dict[str, Any],
    character_id: str,
    *,
    base_dir: str | Path | None = None,
    create_if_missing: bool = True,
) -> dict[str, Any]:
    from utils.level_unlocks import normalize_hero_progress, sync_unlocked_skills

    prog = _eco_prog(state)
    heroes = prog.setdefault("heroes", {})
    if character_id not in heroes and not create_if_missing:
        raise KeyError(character_id)
    if character_id not in heroes:
        slots: list[str] = []
        cfg = load_progression_config(base_dir) if base_dir else {}
        if base_dir is not None:
            slots = list(cfg.get("equipment_slots", []))
        job_id = "wanderer"
        starter = list(cfg.get("jobs", {}).get(job_id, {}).get("starter_skills", ["scout"]))
        heroes[character_id] = {
            "active_job_id": job_id,
            "job_id": job_id,
            "character_level": 1,
            "character_xp": 0,
            "jobs": {job_id: {"level": 1, "xp": 0}},
            "weapon_masteries": {"one_handed_sword": {"level": 1, "xp": 0, "rank": "novice"}},
            "job_level": 1,
            "xp": 0,
            "skill_points": 0,
            "unlocked_skills": starter,
            "equipment": {s: None for s in slots},
            "equip_unlocks": {"milestones": [], "grades": ["common"]},
            "passive_slots": 1,
            "job_skill_enhance_tier": 1,
        }
    hero = heroes[character_id]
    if base_dir is not None:
        normalize_hero_progress(hero, base_dir=base_dir)
        sync_unlocked_skills(hero, base_dir=base_dir)
    return hero


def init_heroes_from_party(state: dict[str, Any], *, base_dir: str | Path) -> None:
    from utils.level_unlocks import sync_unlocked_skills

    cfg = load_progression_config(base_dir)
    party = state.get("party", []) or state.get("active_characters", [])
    for cid in party:
        h = get_hero_progress(state, cid, base_dir=base_dir)
        if cid == "gareth_ironshield" and h.get("job_id") == "wanderer":
            h["job_id"] = "knight"
            h["active_job_id"] = "knight"
            h["jobs"]["knight"] = dict(h["jobs"].get("knight") or {"level": 1, "xp": 0})
        if cid == "elara_moonwhisper" and h.get("job_id") == "wanderer":
            h["job_id"] = "arcane_apprentice"
            h["active_job_id"] = "arcane_apprentice"
            h["jobs"]["arcane_apprentice"] = dict(
                h["jobs"].get("arcane_apprentice") or {"level": 1, "xp": 0}
            )
        job_id = str(h.get("active_job_id") or h.get("job_id", "wanderer"))
        legacy = list(cfg.get("jobs", {}).get(job_id, {}).get("starter_skills", []))
        sync_unlocked_skills(h, base_dir=base_dir)
        merged = list(dict.fromkeys(legacy + list(h.get("unlocked_skills", []))))
        h["unlocked_skills"] = merged


def spawn_limits_for_map(cfg: dict[str, Any], map_id: str) -> dict[str, Any]:
    return cfg.get("map_spawn_limits", {}).get(
        map_id,
        {"max_total": 12, "max_monsters": 6, "max_npcs": 6, "species_caps": {}},
    )


def count_agents_on_map(state: dict[str, Any], map_id: str) -> dict[str, int]:
    agents = [a for a in _get_agents(state) if a.get("map_id") == map_id]
    counts = {
        "total": len(agents),
        "monsters": sum(1 for a in agents if a.get("kind") == "monster"),
        "npcs": sum(1 for a in agents if a.get("kind") == "npc"),
    }
    species: dict[str, int] = {}
    for a in agents:
        sid = a.get("species_id") or a.get("evolution_chain") or a.get("archetype_id", "unknown")
        species[sid] = species.get(sid, 0) + 1
    counts["species"] = species
    return counts


def can_spawn_agent(
    state: dict[str, Any],
    *,
    map_id: str,
    kind: str,
    species_id: str | None,
    base_dir: str | Path,
) -> tuple[bool, str]:
    cfg = load_progression_config(base_dir)
    limits = spawn_limits_for_map(cfg, map_id)
    counts = count_agents_on_map(state, map_id)
    if counts["total"] >= int(limits.get("max_total", 99)):
        return False, f"맵 개체 한도 ({limits['max_total']})"
    if kind == "monster" and counts["monsters"] >= int(limits.get("max_monsters", 99)):
        return False, "맵 몬스터 한도"
    if kind == "npc" and counts["npcs"] >= int(limits.get("max_npcs", 99)):
        return False, "맵 NPC 한도"
    if species_id:
        cap = int(limits.get("species_caps", {}).get(species_id, 99))
        if counts["species"].get(species_id, 0) >= cap:
            return False, f"{species_id} 종족 한도 ({cap})"
    return True, ""


def evolution_tier_def(cfg: dict[str, Any], chain_id: str, tier: int) -> dict[str, Any] | None:
    chain = cfg.get("evolution_chains", {}).get(chain_id, {})
    for t in chain.get("tiers", []):
        if int(t.get("tier", 0)) == tier:
            return t
    return None


def apply_evolution_tier_to_agent(agent: dict[str, Any], tier_def: dict[str, Any]) -> None:
    agent["evolution_id"] = tier_def.get("id")
    agent["evolution_tier"] = int(tier_def.get("tier", 1))
    agent["label"] = tier_def.get("label", agent.get("archetype_id"))
    agent["hp"] = int(tier_def.get("hp", agent.get("hp", 20)))
    agent["max_hp"] = int(tier_def.get("max_hp", agent["hp"]))
    agent["skills"] = list(tier_def.get("skills", []))
    agent["power_bonus"] = int(tier_def.get("power_bonus", 0))


def spawn_evolved_monster(
    state: dict[str, Any],
    chain_id: str,
    *,
    map_id: str,
    x: int,
    y: int,
    tier: int = 1,
    base_dir: str | Path,
) -> tuple[dict[str, Any] | None, str]:
    cfg = load_progression_config(base_dir)
    ok, reason = can_spawn_agent(
        state, map_id=map_id, kind="monster", species_id=chain_id, base_dir=base_dir
    )
    if not ok:
        return None, reason
    tdef = evolution_tier_def(cfg, chain_id, tier)
    if not tdef:
        return None, "unknown evolution tier"
    agent = {
        "instance_id": f"{chain_id}_{uuid.uuid4().hex[:8]}",
        "archetype_id": tdef.get("id", chain_id),
        "species_id": chain_id,
        "evolution_chain": chain_id,
        "kind": "monster",
        "map_id": map_id,
        "x": int(x),
        "y": int(y),
        "goal": "hunt_prey",
        "ai": "predator_patrol",
        "traits": ["plunder_growth"],
        "plunder": {"npc_victims": 0, "power_bonus": 0, "absorbed_skills": []},
        "evolution_xp": 0,
        "skill_cooldowns": {},
    }
    apply_evolution_tier_to_agent(agent, tdef)
    from utils.ecology_objects import enrich_evolved_agent

    agent = enrich_evolved_agent(agent, base_dir=base_dir)
    _get_agents(state).append(agent)
    from utils.agent_competition import attach_society

    attach_society(agent, base_dir=base_dir)
    return agent, ""


def grant_evolution_xp(agent: dict[str, Any], amount: int, *, base_dir: str | Path) -> list[str]:
    lines: list[str] = []
    chain_id = agent.get("evolution_chain") or agent.get("species_id")
    if not chain_id:
        return lines
    cfg = load_progression_config(base_dir)
    agent["evolution_xp"] = int(agent.get("evolution_xp", 0)) + amount
    tier = int(agent.get("evolution_tier", 1))
    tdef = evolution_tier_def(cfg, chain_id, tier)
    if not tdef or tdef.get("evolve_xp") is None:
        return lines
    need = int(tdef["evolve_xp"])
    if agent["evolution_xp"] < need:
        return lines
    nxt = evolution_tier_def(cfg, chain_id, tier + 1)
    if not nxt:
        return lines
    agent["evolution_xp"] = 0
    apply_evolution_tier_to_agent(agent, nxt)
    lines.append(f"[진화] {agent.get('label')} — {nxt.get('label')}!")
    return lines


def _job_level_from_xp(cfg: dict[str, Any], job_id: str, xp: int) -> int:
    job = cfg.get("jobs", {}).get(job_id, {})
    thresholds = job.get("level_xp", [0, 9999])
    level = 1
    for i, need in enumerate(thresholds):
        if xp >= int(need):
            level = i + 1
    return min(level, len(thresholds))


def grant_hero_xp(
    state: dict[str, Any],
    character_id: str,
    amount: int,
    *,
    base_dir: str | Path,
    reason: str = "explore",
) -> list[str]:
    from utils.level_unlocks import grant_axis_xp

    h = get_hero_progress(state, character_id, base_dir=base_dir)
    wclass = next(iter(h.get("weapon_masteries", {"one_handed_sword": {}})), "one_handed_sword")
    char_part = max(1, amount // 3)
    job_part = max(1, amount // 2)
    wpn_part = max(1, amount // 4)
    lines = grant_axis_xp(
        h,
        character_xp=char_part,
        job_xp=job_part,
        weapon_xp=wpn_part,
        weapon_class=wclass,
        base_dir=base_dir,
    )
    h["xp"] = int(h["jobs"].get(h["active_job_id"], {}).get("xp", h.get("xp", 0)))
    return lines


def on_explore_progression(state: dict[str, Any], *, base_dir: str | Path) -> list[str]:
    if not _ecology_enabled(state):
        return []
    cfg = load_progression_config(base_dir)
    xp = int(cfg.get("explore_xp", 8))
    lines: list[str] = []
    for cid in state.get("party", []):
        lines.extend(grant_hero_xp(state, cid, xp, base_dir=base_dir, reason="explore"))
    return lines


def unlock_skill(
    state: dict[str, Any], character_id: str, skill_id: str, *, base_dir: str | Path
) -> dict[str, Any]:
    from utils.level_unlocks import skills_available_for_hero
    from utils.skill_catalog import catalog_skill

    cfg = load_progression_config(base_dir)
    if skill_id not in cfg.get("skills", {}) and not catalog_skill(skill_id, base_dir=base_dir):
        return {"ok": False, "error": "unknown skill"}
    h = get_hero_progress(state, character_id, base_dir=base_dir)
    if int(h.get("skill_points", 0)) < 1:
        return {"ok": False, "error": "스킬 포인트 부족"}
    if skill_id in h.get("unlocked_skills", []):
        return {"ok": False, "error": "이미 해금됨"}
    eligible = set(skills_available_for_hero(h, base_dir=base_dir))
    legacy_ok = False
    if skill_id in cfg.get("skills", {}):
        job_id = str(h.get("active_job_id") or h.get("job_id", "wanderer"))
        jl = int(h.get("job_level", 1))
        job_cfg = cfg.get("jobs", {}).get(job_id, {})
        if skill_id in job_cfg.get("starter_skills", []):
            legacy_ok = True
        for need_lv, skills in job_cfg.get("skills_by_level", {}).items():
            if jl >= int(need_lv) and skill_id in skills:
                legacy_ok = True
                break
    if skill_id not in eligible and not legacy_ok:
        return {"ok": False, "error": "해금 조건 미달"}
    h["skill_points"] = int(h["skill_points"]) - 1
    h.setdefault("unlocked_skills", []).append(skill_id)
    return {"ok": True, "skill_id": skill_id}


def equip_item(
    state: dict[str, Any], character_id: str, item_id: str, *, base_dir: str | Path
) -> dict[str, Any]:
    from utils.item_catalog import get_item_def
    from utils.level_unlocks import can_wield_grade

    item = get_item_def(item_id, base_dir=base_dir)
    if not item or not item.get("equippable"):
        return {"ok": False, "error": "unknown item"}
    h = get_hero_progress(state, character_id, base_dir=base_dir)
    slot = item.get("slot", "weapon")
    if int(h.get("job_level", 1)) < int(item.get("min_job_level", 1)):
        return {"ok": False, "error": "직업 레벨 부족"}
    allowed = item.get("jobs")
    if allowed and h.get("job_id") not in allowed:
        return {"ok": False, "error": "직업 불일치"}
    grade = str(item.get("grade", "common"))
    wclass = str(item.get("weapon_class", h.get("weapon_class", "one_handed_sword")))
    ok, reason = can_wield_grade(h, grade, weapon_class=wclass, base_dir=base_dir)
    if not ok:
        return {"ok": False, "error": reason}
    inv = state.setdefault("inventory", {})
    owned = inv.setdefault("equipment_owned", [])
    if item_id not in owned and item_id not in inv.get("shared_items", []):
        owned.append(item_id)
    h.setdefault("equipment", {})[slot] = item_id
    return {"ok": True, "slot": slot, "item_id": item_id}


def grant_item(
    state: dict[str, Any], item_id: str, count: int = 1, *, base_dir: str | Path
) -> dict[str, Any]:
    from utils.item_catalog import get_item_def

    item = get_item_def(item_id, base_dir=base_dir)
    if not item:
        return {"ok": False, "error": "unknown item"}
    inv = state.setdefault("inventory", {})
    if item.get("consumable") or item.get("stackable"):
        stacks = inv.setdefault("consumables", {})
        stacks[item_id] = int(stacks.get(item_id, 0)) + max(1, count)
    else:
        owned = inv.setdefault("equipment_owned", [])
        if item_id not in owned:
            owned.append(item_id)
    return {"ok": True, "item_id": item_id, "count": count}


def use_item(
    state: dict[str, Any], character_id: str, item_id: str, *, base_dir: str | Path
) -> dict[str, Any]:
    from utils.item_catalog import get_item_def

    item = get_item_def(item_id, base_dir=base_dir)
    if not item or not item.get("consumable"):
        return {"ok": False, "error": "not consumable"}
    inv = state.setdefault("inventory", {})
    stacks = inv.setdefault("consumables", {})
    if int(stacks.get(item_id, 0)) < 1:
        return {"ok": False, "error": "아이템 없음"}
    stacks[item_id] = int(stacks[item_id]) - 1
    if stacks[item_id] <= 0:
        stacks.pop(item_id, None)
    h = get_hero_progress(state, character_id, base_dir=base_dir)
    effects: dict[str, Any] = {}
    hp_r = item.get("hp_restore")
    if hp_r is not None:
        max_hp = int(h.get("max_hp", 100))
        cur = int(h.get("hp", max_hp))
        restore = int(hp_r)
        if restore >= 9999:
            cur = max_hp
        else:
            cur = min(max_hp, cur + restore)
        h["hp"] = cur
        effects["hp"] = cur
    mp_r = item.get("mp_restore")
    if mp_r is not None:
        max_mp = int(h.get("max_mp", 50))
        cur = int(h.get("mp", max_mp))
        restore = int(mp_r)
        cur = min(max_mp, cur + restore)
        h["mp"] = cur
        effects["mp"] = cur
    if item.get("cure_poison"):
        h.pop("poisoned", None)
        effects["cure_poison"] = True
    for stat in ("str", "agi", "vit"):
        key = f"buff_{stat}"
        if item.get(key):
            h.setdefault("buffs", {})[stat] = int(h.get("buffs", {}).get(stat, 0)) + int(item[key])
            effects[key] = h["buffs"][stat]
    return {
        "ok": True,
        "item_id": item_id,
        "label": item.get("label", item_id),
        "effects": effects,
    }


def _catalog_items_summary(base_dir: str | Path) -> dict[str, Any]:
    from utils.item_catalog import catalog_counts

    return catalog_counts(base_dir=base_dir)


def progression_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    from utils.level_unlocks import unlock_status_for_hero
    from utils.skill_catalog import catalog_skill_count_for_job, load_progression_unlocks_config

    cfg = load_progression_config(base_dir)
    unlock_cfg = load_progression_unlocks_config(base_dir)
    map_id = state.get("world", {}).get("map_id", "ashpoint_01")
    heroes = {
        cid: get_hero_progress(state, cid, base_dir=base_dir)
        for cid in state.get("party", [])
    }
    unlock_views = {
        cid: unlock_status_for_hero(heroes[cid], base_dir=base_dir) for cid in heroes
    }
    return {
        "heroes": heroes,
        "unlock_status": unlock_views,
        "skill_catalog": {
            "skills_per_job": int(unlock_cfg["skill_catalog"]["skills_per_job"]),
            "skills_per_weapon_class": int(unlock_cfg["weapon_skill_catalog"]["skills_per_class"]),
            "jobs": {
                jid: catalog_skill_count_for_job(jid, base_dir=base_dir)
                for jid in unlock_cfg.get("jobs", [])
            },
        },
        "jobs": {
            jid: {"label": j.get("label"), "skills_by_level": j.get("skills_by_level")}
            for jid, j in cfg.get("jobs", {}).items()
        },
        "items": _catalog_items_summary(base_dir),
        "evolution_chains": list(cfg.get("evolution_chains", {}).keys()),
        "map_spawn": {
            "map_id": map_id,
            "limits": spawn_limits_for_map(cfg, map_id),
            "current": count_agents_on_map(state, map_id),
            "godot_hint_max": cfg.get("godot_recommended_max_sprites_per_map", 32),
        },
    }
