"""Combat stats — build snapshots, resolve strikes (single entry for sim + API)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.combat_precision import (
    fixed_scale,
    from_milli,
    load_combat_precision_config,
    resolve_strike_damage_milli,
    to_milli,
)

_GRADE_ORDER = (
    "common",
    "high",
    "rare",
    "hero",
    "legend",
    "mythic",
    "demigod",
)


def _read_json(base_dir: str | Path, rel: str) -> dict[str, Any]:
    path = Path(base_dir) / rel
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=4)
def _config_bundle(base_dir: str) -> dict[str, Any]:
    root = str(Path(base_dir).resolve())
    return {
        "precision": load_combat_precision_config(root),
        "stats": _read_json(root, "config/combat_stats.json"),
        "tiers": _read_json(root, "config/power_tiers.json"),
        "grades": _read_json(root, "config/item_grades.json"),
        "equipment": _read_json(root, "config/equipment_templates.json"),
        "jobs": _read_json(root, "config/job_stat_routes.json"),
        "mastery": _read_json(root, "config/weapon_mastery.json"),
        "combatants": _read_json(root, "config/combatants.json"),
        "coalition": _read_json(root, "config/arthur_coalition.json"),
    }


def load_combat_bundle(base_dir: str | Path) -> dict[str, Any]:
    return _config_bundle(str(Path(base_dir).resolve()))


def grade_index(grade: str) -> int:
    g = grade.lower()
    return _GRADE_ORDER.index(g) if g in _GRADE_ORDER else 0


def compute_primary_stats(
    job_id: str,
    *,
    character_level: int,
    job_level: int,
    jobs_cfg: dict[str, Any],
) -> dict[str, int]:
    job = jobs_cfg.get("jobs", {}).get(job_id, jobs_cfg.get("jobs", {}).get("wanderer", {}))
    stats: dict[str, int] = {}
    for key in jobs_cfg.get("stats", ["str", "agi", "vit", "int", "dex", "luck"]):
        jl = float(job.get("growth_per_job_level", {}).get(key, 0))
        cl = float(job.get("growth_per_character_level", {}).get(key, 0))
        stats[key] = max(1, int(jl * job_level + cl * character_level))
    return stats


def _weapon_template(equipment_cfg: dict[str, Any], weapon_id: str | None) -> dict[str, Any]:
    if not weapon_id:
        return {}
    return equipment_cfg.get("weapons", {}).get(weapon_id, {})


def _armor_template(equipment_cfg: dict[str, Any], armor_id: str | None) -> dict[str, Any]:
    if not armor_id:
        return {}
    return equipment_cfg.get("armor", {}).get(armor_id, {})


def hp_cap_milli_for(tier: str, *, bundle: dict[str, Any]) -> int:
    tiers = bundle["tiers"].get("tiers", {})
    if tier == "demigod":
        return int(tiers.get("demigod", {}).get("hp_cap_milli", 1_000_000_000))
    if tier == "apex_mortal":
        return int(tiers.get("apex_mortal", {}).get("hp_cap_milli", 99_999_000))
    pools = bundle["stats"].get("hp_pools", {})
    return int(pools.get("default_mortal_cap_milli", 50_000_000))


def build_combatant_snapshot(
    *,
    base_dir: str | Path,
    preset_id: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full combatant for strike resolution (milli stats)."""
    bundle = load_combat_bundle(base_dir)
    cfg = bundle["precision"]
    data: dict[str, Any] = {}
    if preset_id:
        data.update(bundle["combatants"].get(preset_id, {}))
    if overrides:
        data.update(overrides)

    char_lv = int(data.get("character_level", 1))
    job_id = str(data.get("job_id", "wanderer"))
    job_lv = int(data.get("job_level", 1))
    wclass = str(data.get("weapon_class", "two_handed_sword"))
    wpn_lv = int(data.get("weapon_mastery_level", 1))
    tier = str(data.get("tier", "mortal"))
    equip = data.get("equipment") or {}

    prim = compute_primary_stats(
        job_id, character_level=char_lv, job_level=job_lv, jobs_cfg=bundle["jobs"]
    )
    wpn = _weapon_template(bundle["equipment"], equip.get("weapon"))
    arm = _armor_template(bundle["equipment"], equip.get("armor"))
    wconst = bundle["stats"].get("weapon_constants", {}).get(
        wpn.get("weapon_class", wclass),
        bundle["stats"].get("weapon_constants", {}).get("two_handed_sword", {}),
    )
    if equip.get("weapon") == "excalibur_sovereign_blade":
        wconst = bundle["stats"].get("weapon_constants", {}).get(
            "excalibur_sovereign_blade", wconst
        )

    w_grade = str(wpn.get("grade", "common"))
    scale = fixed_scale(cfg)
    phys_k = int(wconst.get("phys_constant_milli", 1000)) / scale
    str_m = to_milli(prim["str"] * 0.42 + prim["dex"] * 0.18, cfg=cfg)
    wpn_atk = to_milli(float(wpn.get("attack", 10)), cfg=cfg)
    mastery_bonus = to_milli(wpn_lv * 0.95, cfg=cfg)
    attack_milli = int((str_m + wpn_atk + mastery_bonus) * phys_k)
    attack_milli = min(attack_milli, int(cfg.get("raw_damage_soft_cap_milli", 100_000_000)))

    def_m = to_milli(float(arm.get("defense", prim["vit"] * 0.35)), cfg=cfg)
    if tier == "demigod":
        def_m = max(def_m, int(cfg.get("mitigation", {}).get("sovereign_defense_floor_milli", 100_000_000)))

    vit_hp = to_milli(prim["vit"] * 8.5 + char_lv * 2.2, cfg=cfg)
    hp_milli = min(hp_cap_milli_for(tier, bundle=bundle), max(vit_hp, 5_000))

    snap: dict[str, Any] = {
        "id": preset_id or data.get("id", "custom"),
        "label": data.get("label", preset_id or "combatant"),
        "tier": tier,
        "character_level": char_lv,
        "weapon_mastery_level": wpn_lv,
        "item_grade_index": grade_index(w_grade),
        "attack_milli": attack_milli,
        "defense_milli": def_m,
        "hp_milli": hp_milli,
        "phys_attack_milli": attack_milli,
        "phys_defense_milli": def_m,
        "primary": prim,
        "weapon_class": wclass,
        "armor_pierce": bool(data.get("armor_pierce") or data.get("excalibur_bound")),
        "excalibur_bound": bool(data.get("excalibur_bound")),
        "world_sovereign": bool(data.get("world_sovereign")),
    }
    if tier == "demigod" and bundle["coalition"].get("world_sovereign", {}).get("hp_milli"):
        snap["hp_milli"] = int(bundle["coalition"]["world_sovereign"]["hp_milli"])
    return snap


def agent_to_combatant(agent: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    """Map ecology_agent / field agent → combat snapshot."""
    preset = agent.get("combatant_preset")
    if preset:
        return build_combatant_snapshot(base_dir=base_dir, preset_id=str(preset))

    stats = agent.get("stats") or {}
    tier = str(agent.get("tier", "mortal"))
    if agent.get("world_sovereign_holder") or agent.get("archetype_id") == "npc_arthur_pendragon":
        return build_combatant_snapshot(base_dir=base_dir, preset_id="npc_arthur_pendragon")

    overrides = {
        "tier": tier,
        "character_level": int(agent.get("character_level", stats.get("level", 1))),
        "job_id": agent.get("job_id", "wanderer"),
        "job_level": int(agent.get("job_level", 1)),
        "weapon_class": agent.get("weapon_class", "one_handed_sword"),
        "weapon_mastery_level": int(agent.get("weapon_mastery_level", 1)),
        "label": agent.get("label") or agent.get("archetype_id", "agent"),
    }
    snap = build_combatant_snapshot(base_dir=base_dir, overrides=overrides)
    mhp = int(agent.get("max_hp", 0))
    if mhp > 0:
        snap["hp_milli"] = to_milli(float(mhp), cfg=load_combat_precision_config(base_dir))
    return snap


def strike_damage_milli(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: Any,
    skill_multiplier: float = 1.0,
    force_hit: bool | None = None,
    force_sovereign_through: bool | None = None,
) -> dict[str, Any]:
    bundle = load_combat_bundle(base_dir)
    cfg = bundle["precision"]
    atk = dict(attacker)
    if skill_multiplier != 1.0:
        atk["attack_milli"] = int(atk.get("attack_milli", 0) * skill_multiplier)
    return resolve_strike_damage_milli(
        atk,
        defender,
        cfg=cfg,
        rng=rng,
        force_hit=force_hit,
        force_sovereign_through=force_sovereign_through,
    )


def strike_damage_hp(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: Any,
    skill_multiplier: float = 1.0,
    minimum: int = 0,
) -> int:
    """Integer HP damage for field agents / rule engine."""
    r = strike_damage_milli(
        attacker,
        defender,
        base_dir=base_dir,
        rng=rng,
        skill_multiplier=skill_multiplier,
    )
    dmg = int(round(from_milli(int(r.get("damage_milli", 0)), cfg=load_combat_precision_config(base_dir))))
    if minimum > 0 and r.get("hit") and dmg < minimum and int(r.get("damage_milli", 0)) > 0:
        return minimum
    return max(0, dmg)


def combat_power_estimate(snapshot: dict[str, Any], *, base_dir: str | Path) -> int:
    """Simple 전투력 display number."""
    cfg = load_combat_precision_config(base_dir)
    atk = int(snapshot.get("attack_milli", 0))
    hp = int(snapshot.get("hp_milli", 0))
    defn = int(snapshot.get("defense_milli", 0))
    lv = int(snapshot.get("character_level", 1))
    wm = int(snapshot.get("weapon_mastery_level", 1))
    gr = int(snapshot.get("item_grade_index", 0))
    return (atk + defn + hp // fixed_scale(cfg)) // fixed_scale(cfg) + lv + wm + gr * 50


def sovereign_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    from utils.sovereign_siege import sovereign_siege_status

    arthur = build_combatant_snapshot(base_dir=base_dir, preset_id="npc_arthur_pendragon")
    status = sovereign_siege_status(state, base_dir=base_dir)
    status["arthur_snapshot"] = {
        "hp_milli": arthur["hp_milli"],
        "attack_milli": arthur["attack_milli"],
        "defense_milli": arthur["defense_milli"],
        "combat_power": combat_power_estimate(arthur, base_dir=base_dir),
    }
    return status
