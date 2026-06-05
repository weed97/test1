"""Ecology agents as simulation objects — stats, HP/MP, skills (Godot = sprites only)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from utils.progression import load_progression_config


def load_ecology_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "field_ecology.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_intelligence_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "agent_intelligence.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def skill_definition(skill_id: str, *, base_dir: str | Path) -> dict[str, Any]:
    eco = load_ecology_config(base_dir)
    if skill_id in eco.get("skills", {}):
        return dict(eco["skills"][skill_id])
    prog = load_progression_config(base_dir)
    sk = prog.get("skills", {}).get(skill_id, {})
    return {
        "power": int(sk.get("power", 5)),
        "mana_cost": int(sk.get("mana", 0)),
        "range_tiles": 1,
        "cooldown_beats": 2,
        "element": sk.get("element", ""),
        "tags": list(sk.get("tags", [])),
    }


def _default_intelligence(
    agent: dict[str, Any], *, base_dir: str | Path
) -> dict[str, Any]:
    icfg = load_intelligence_config(base_dir)
    ai = agent.get("ai", "")
    kind = agent.get("kind", "monster")
    defaults = icfg.get("default_by_ai", {}).get(ai)
    if not defaults:
        defaults = icfg.get("default_monster" if kind == "monster" else "default_npc", {})
    return {
        "iq": int(defaults.get("iq", 50)),
        "strategy": str(defaults.get("strategy", "predator_pack")),
        "disposition": "hostile" if kind == "monster" else "neutral",
    }


def _stats_from_archetype(arch: dict[str, Any], kind: str) -> dict[str, int]:
    base = arch.get("stats") or {}
    if kind == "monster":
        return {
            "str": int(base.get("str", 12)),
            "agi": int(base.get("agi", 10)),
            "int": int(base.get("int", 6)),
            "vit": int(base.get("vit", 10)),
        }
    return {
        "str": int(base.get("str", 8)),
        "agi": int(base.get("agi", 9)),
        "int": int(base.get("int", 12)),
        "vit": int(base.get("vit", 9)),
    }


def build_ecology_agent(
    *,
    archetype_id: str | None = None,
    kind: str,
    map_id: str,
    x: int,
    y: int,
    base_dir: str | Path,
    instance_id: str | None = None,
    label: str | None = None,
    skills: list[str] | None = None,
    hp: int | None = None,
    max_hp: int | None = None,
    mp: int | None = None,
    max_mp: int | None = None,
    stats: dict[str, int] | None = None,
    ai: str | None = None,
    traits: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a full simulation object from archetype or explicit fields."""
    eco_cfg = load_ecology_config(base_dir)
    arch = eco_cfg.get("archetypes", {}).get(archetype_id or "", {}) if archetype_id else {}
    aid = archetype_id or (extra or {}).get("evolution_id", kind)
    iid = instance_id or f"{aid}_{uuid.uuid4().hex[:8]}"
    sk = skills if skills is not None else list(arch.get("skills", []))
    st = stats if stats is not None else _stats_from_archetype(arch, kind)
    mhp = int(max_hp if max_hp is not None else hp if hp is not None else 30 + st["vit"] * 2)
    hp_v = int(hp if hp is not None else mhp)
    mmp = int(max_mp if max_mp is not None else mp if mp is not None else 10 + st["int"] * 2)
    mp_v = int(mp if mp is not None else mmp)

    agent: dict[str, Any] = {
        "object_type": "ecology_agent",
        "instance_id": iid,
        "archetype_id": archetype_id or aid,
        "kind": kind,
        "label": label or arch.get("label") or aid,
        "map_id": map_id,
        "x": int(x),
        "y": int(y),
        "stats": st,
        "hp": hp_v,
        "max_hp": mhp,
        "mp": mp_v,
        "max_mp": mmp,
        "skills": sk,
        "skill_cooldowns": {s: 0 for s in sk},
        "traits": list(traits if traits is not None else arch.get("traits", [])),
        "ai": ai or arch.get("ai", "patrol"),
        "goal": "patrol",
        "relations": {},
        "intelligence": {},
        "plunder": {"npc_victims": 0, "power_bonus": 0, "absorbed_skills": []},
    }
    if kind == "monster" and "plunder_growth" in agent["traits"]:
        agent["goal"] = "hunt_prey"
    if extra:
        agent.update(extra)
    agent["intelligence"] = _default_intelligence(agent, base_dir=base_dir)
    if extra and extra.get("intelligence"):
        agent["intelligence"].update(extra["intelligence"])
    return agent


def normalize_agent(agent: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    """Upgrade legacy agent dicts to full ecology objects."""
    if agent.get("object_type") == "ecology_agent" and agent.get("stats"):
        if not agent.get("intelligence"):
            agent["intelligence"] = _default_intelligence(agent, base_dir=base_dir)
        agent.setdefault("relations", {})
        agent.setdefault("skill_cooldowns", {s: 0 for s in agent.get("skills", [])})
        return agent

    kind = str(agent.get("kind", "monster"))
    st = agent.get("stats") or {
        "str": 10,
        "agi": 10,
        "int": 8,
        "vit": int(agent.get("max_hp", 40)) // 4,
    }
    mhp = int(agent.get("max_hp", agent.get("hp", 40)))
    agent["object_type"] = "ecology_agent"
    agent["stats"] = st
    agent["max_hp"] = mhp
    agent["hp"] = min(int(agent.get("hp", mhp)), mhp)
    agent["max_mp"] = int(agent.get("max_mp", 10 + st["int"] * 2))
    agent["mp"] = min(int(agent.get("mp", agent["max_mp"])), agent["max_mp"])
    agent.setdefault("relations", {})
    for sk in agent.get("skills", []):
        agent.setdefault("skill_cooldowns", {}).setdefault(sk, 0)
    agent["intelligence"] = agent.get("intelligence") or _default_intelligence(
        agent, base_dir=base_dir
    )
    return agent


def enrich_evolved_agent(agent: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    """Apply evolution tier fields to a full ecology object."""
    tier_hp = int(agent.get("max_hp", agent.get("hp", 28)))
    extra: dict[str, Any] = {
        k: agent[k]
        for k in (
            "species_id",
            "evolution_chain",
            "evolution_tier",
            "evolution_id",
            "label",
            "skills",
            "power_bonus",
            "evolution_xp",
        )
        if k in agent
    }
    extra["traits"] = list(agent.get("traits", ["plunder_growth"]))
    extra["ai"] = "predator_patrol"
    extra["goal"] = "hunt_prey"
    built = build_ecology_agent(
        archetype_id=str(agent.get("evolution_id") or agent.get("species_id", "monster")),
        kind="monster",
        map_id=str(agent["map_id"]),
        x=int(agent["x"]),
        y=int(agent["y"]),
        base_dir=base_dir,
        instance_id=str(agent["instance_id"]),
        label=agent.get("label"),
        skills=list(agent.get("skills", [])),
        hp=tier_hp,
        max_hp=tier_hp,
        extra=extra,
    )
    built["plunder"] = agent.get(
        "plunder",
        {
            "npc_victims": 0,
            "power_bonus": int(agent.get("power_bonus", 0)),
            "absorbed_skills": [],
        },
    )
    pb = int(built["plunder"].get("power_bonus", 0))
    if pb:
        built["intelligence"]["strategy"] = "rival_hunter"
        built["intelligence"]["iq"] = min(95, int(built["intelligence"]["iq"]) + pb)
    return built


def agent_object_manifest(agent: dict[str, Any]) -> dict[str, Any]:
    """API payload for Godot — simulation fields + sprite keys."""
    return {
        "object_type": agent.get("object_type", "ecology_agent"),
        "instance_id": agent.get("instance_id"),
        "archetype_id": agent.get("archetype_id"),
        "species_id": agent.get("species_id"),
        "evolution_chain": agent.get("evolution_chain"),
        "evolution_tier": agent.get("evolution_tier"),
        "evolution_id": agent.get("evolution_id"),
        "label": agent.get("label"),
        "kind": agent.get("kind"),
        "x": int(agent.get("x", 0)),
        "y": int(agent.get("y", 0)),
        "stats": agent.get("stats", {}),
        "hp": int(agent.get("hp", 1)),
        "max_hp": int(agent.get("max_hp", 1)),
        "mp": int(agent.get("mp", 0)),
        "max_mp": int(agent.get("max_mp", 0)),
        "skills": agent.get("skills", []),
        "skill_cooldowns": agent.get("skill_cooldowns", {}),
        "intelligence": agent.get("intelligence", {}),
        "relations": agent.get("relations", {}),
        "goal": agent.get("goal"),
        "settlement": agent.get("settlement"),
        "plunder": agent.get("plunder"),
        "civilization_id": agent.get("civilization_id"),
        "culture_tags": agent.get("culture_tags"),
        "godot_sprite_key": agent.get("evolution_id")
        or agent.get("archetype_id")
        or agent.get("species_id"),
    }
