"""Character progression — jobs, skills, equipment, monster evolution, spawn caps."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

def _ecology_enabled(state: dict[str, Any]) -> bool:
    mode = state.get("flags", {}).get("game_mode", "story")
    return mode in ("ecology", "hybrid")


def _get_agents(state: dict[str, Any]) -> list[dict[str, Any]]:
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    agents = eco.setdefault("agents", [])
    return agents  # type: ignore[return-value]


def load_progression_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "progression.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _eco_prog(state: dict[str, Any]) -> dict[str, Any]:
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    return eco.setdefault("progression", {})


def get_hero_progress(
    state: dict[str, Any],
    character_id: str,
    *,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    prog = _eco_prog(state)
    heroes = prog.setdefault("heroes", {})
    if character_id not in heroes:
        slots: list[str] = []
        if base_dir is not None:
            slots = list(load_progression_config(base_dir).get("equipment_slots", []))
        heroes[character_id] = {
            "job_id": "wanderer",
            "job_level": 1,
            "xp": 0,
            "skill_points": 0,
            "unlocked_skills": ["scout"],
            "equipment": {s: None for s in slots},
        }
    return heroes[character_id]


def init_heroes_from_party(state: dict[str, Any], *, base_dir: str | Path) -> None:
    cfg = load_progression_config(base_dir)
    party = state.get("party", []) or state.get("active_characters", [])
    for cid in party:
        h = get_hero_progress(state, cid, base_dir=base_dir)
        if cid == "gareth_ironshield" and h.get("job_id") == "wanderer":
            h["job_id"] = "knight"
            h["unlocked_skills"] = list(cfg["jobs"]["knight"]["starter_skills"])
        if cid == "elara_moonwhisper" and h.get("job_id") == "wanderer":
            h["job_id"] = "arcane_apprentice"
            h["unlocked_skills"] = list(cfg["jobs"]["arcane_apprentice"]["starter_skills"])


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
    lines: list[str] = []
    cfg = load_progression_config(base_dir)
    h = get_hero_progress(state, character_id, base_dir=base_dir)
    old_lvl = int(h.get("job_level", 1))
    h["xp"] = int(h.get("xp", 0)) + amount
    new_lvl = _job_level_from_xp(cfg, h["job_id"], h["xp"])
    h["job_level"] = new_lvl
    if new_lvl > old_lvl:
        h["skill_points"] = int(h.get("skill_points", 0)) + 1
        job = cfg["jobs"].get(h["job_id"], {})
        auto = job.get("skills_by_level", {}).get(str(new_lvl))
        if auto:
            for sk in auto:
                if sk not in h["unlocked_skills"]:
                    h["unlocked_skills"].append(sk)
                    lines.append(f"[성장] {character_id} 스킬 해금: {sk}")
        lines.append(f"[성장] {character_id} 직업 Lv{new_lvl} ({job.get('label', h['job_id'])})")
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
    cfg = load_progression_config(base_dir)
    if skill_id not in cfg.get("skills", {}):
        return {"ok": False, "error": "unknown skill"}
    h = get_hero_progress(state, character_id, base_dir=base_dir)
    if int(h.get("skill_points", 0)) < 1:
        return {"ok": False, "error": "스킬 포인트 부족"}
    if skill_id in h.get("unlocked_skills", []):
        return {"ok": False, "error": "이미 해금됨"}
    h["skill_points"] = int(h["skill_points"]) - 1
    h.setdefault("unlocked_skills", []).append(skill_id)
    return {"ok": True, "skill_id": skill_id}


def equip_item(
    state: dict[str, Any], character_id: str, item_id: str, *, base_dir: str | Path
) -> dict[str, Any]:
    cfg = load_progression_config(base_dir)
    item = cfg.get("items", {}).get(item_id)
    if not item:
        return {"ok": False, "error": "unknown item"}
    h = get_hero_progress(state, character_id, base_dir=base_dir)
    slot = item.get("slot", "weapon")
    if int(h.get("job_level", 1)) < int(item.get("min_job_level", 1)):
        return {"ok": False, "error": "직업 레벨 부족"}
    allowed = item.get("jobs")
    if allowed and h.get("job_id") not in allowed:
        return {"ok": False, "error": "직업 불일치"}
    inv = state.setdefault("inventory", {})
    owned = inv.setdefault("equipment_owned", [])
    if item_id not in owned and item_id not in inv.get("shared_items", []):
        owned.append(item_id)
    h.setdefault("equipment", {})[slot] = item_id
    return {"ok": True, "slot": slot, "item_id": item_id}


def progression_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    cfg = load_progression_config(base_dir)
    map_id = state.get("world", {}).get("map_id", "ashpoint_01")
    heroes = {
        cid: get_hero_progress(state, cid, base_dir=base_dir)
        for cid in state.get("party", [])
    }
    return {
        "heroes": heroes,
        "jobs": {
            jid: {"label": j.get("label"), "skills_by_level": j.get("skills_by_level")}
            for jid, j in cfg.get("jobs", {}).items()
        },
        "items": cfg.get("items", {}),
        "evolution_chains": list(cfg.get("evolution_chains", {}).keys()),
        "map_spawn": {
            "map_id": map_id,
            "limits": spawn_limits_for_map(cfg, map_id),
            "current": count_agents_on_map(state, map_id),
            "godot_hint_max": cfg.get("godot_recommended_max_sprites_per_map", 32),
        },
    }
