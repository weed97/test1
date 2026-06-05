"""Procedural skill catalog — ~300 skills/job, 60 skills/weapon class up to Lv999."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_ELEMENTS = ("", "fire", "ice", "light", "shadow", "earth", "wind")


def _read_json(base_dir: str | Path, rel: str) -> dict[str, Any]:
    with (Path(base_dir) / rel).open(encoding="utf-8") as f:
        return json.load(f)


def load_progression_unlocks_config(base_dir: str | Path) -> dict[str, Any]:
    return _read_json(base_dir, "config/progression_unlocks.json")


def _unlock_level_for_index(index: int, total: int, *, max_level: int = 999) -> int:
    if total <= 1:
        return 1
    return 1 + (index * (max_level - 1)) // (total - 1)


def _scaled_power(
    tier: int,
    unlock_level: int,
    scaling: dict[str, Any],
    *,
    extra_per_level: float = 0.0,
) -> int:
    base = float(scaling.get("base_power", 8))
    per_tier = float(scaling.get("power_per_tier", 0.35))
    per_ul = float(scaling.get("power_per_unlock_level", 0.015))
    raw = base + tier * per_tier + unlock_level * per_ul + tier * extra_per_level
    return max(1, int(round(raw)))


def _job_skill_kind(job_id: str, category: str, cat_cfg: dict[str, Any], unlocks: dict[str, Any]) -> str:
    overrides = unlocks.get("skill_catalog", {}).get("job_skill_kind_overrides", {})
    job_o = overrides.get(job_id, {})
    if category in job_o:
        return str(job_o[category])
    return str(cat_cfg.get("default_skill_kind", "melee_phys_single"))


def _build_job_skills(job_id: str, unlocks: dict[str, Any], jobs_cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    catalog = unlocks["skill_catalog"]
    scaling = catalog["scaling"]
    max_lv = int(unlocks.get("max_level", 999))
    job_label = jobs_cfg.get("jobs", {}).get(job_id, {}).get("label", job_id)
    preferred = jobs_cfg.get("jobs", {}).get(job_id, {}).get("preferred_weapon_classes", [])
    skills: dict[str, dict[str, Any]] = {}
    global_index = 0

    for cat_name, cat_cfg in catalog["categories"].items():
        count = int(cat_cfg["count"])
        prefix = str(cat_cfg["prefix"])
        axis = str(cat_cfg.get("unlock_axis", "job_level"))
        for tier in range(1, count + 1):
            skill_id = f"{job_id}_{prefix}_{tier:03d}"
            unlock_level = _unlock_level_for_index(tier - 1, count, max_level=max_lv)
            power = _scaled_power(tier, unlock_level, scaling)
            mana = int(scaling.get("mana_base", 4) + tier * float(scaling.get("mana_per_tier", 0.2)))
            rng_tiles = int(scaling.get("range_tiles_base", 1)) + (tier - 1) // int(
                scaling.get("range_tiles_every_n_tiers", 25)
            )
            cd = max(
                0,
                int(scaling.get("cooldown_beats_base", 3))
                - (tier - 1) // int(scaling.get("cooldown_reduction_every_n_tiers", 15)),
            )
            reqs: dict[str, Any] = {axis: unlock_level}
            if cat_name == "attack" and preferred:
                gate_n = int(cat_cfg.get("weapon_mastery_gate_every_n", 40))
                if tier % gate_n == 0 or tier == count:
                    reqs["weapon_mastery_level"] = min(max_lv, unlock_level // 2)
                    reqs["weapon_class"] = preferred[0]
            if cat_name == "passive":
                reqs = {"character_level": unlock_level}

            entry = {
                "skill_id": skill_id,
                "label": f"{job_label} · {cat_cfg.get('label_ko', cat_name)} {tier}",
                "category": cat_name,
                "job_id": job_id,
                "tier": tier,
                "catalog_index": global_index,
                "type": cat_cfg.get("type", "active"),
                "power": 0 if cat_cfg.get("type") == "passive" else power,
                "power_scale_tier": tier,
                "mana_cost": 0 if cat_cfg.get("type") == "passive" else mana,
                "range_tiles": rng_tiles,
                "cooldown_beats": cd,
                "element": _ELEMENTS[tier % len(_ELEMENTS)],
                "tags": list(cat_cfg.get("default_tags", [])),
                "skill_kind": _job_skill_kind(job_id, cat_name, cat_cfg, unlocks),
                "unlock_axis": axis,
                "unlock_requirements": reqs,
                "combat_pipeline": "catalog",
            }
            from utils.skill_names import apply_name_overrides

            skills[skill_id] = apply_name_overrides(entry)
            global_index += 1

    return skills


def _build_weapon_class_skills(
    weapon_class: str, unlocks: dict[str, Any], mastery_cfg: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    wcat = unlocks["weapon_skill_catalog"]
    scaling = wcat["scaling"]
    max_lv = int(unlocks.get("max_level", 999))
    wlabel = mastery_cfg.get("classes", {}).get(weapon_class, {}).get("label", weapon_class)
    skills: dict[str, dict[str, Any]] = {}
    idx = 0
    for cat_name, cat_cfg in wcat["categories"].items():
        count = int(cat_cfg["count"])
        prefix = str(cat_cfg["prefix"])
        for tier in range(1, count + 1):
            skill_id = f"wpn_{weapon_class}_{prefix}_{tier:03d}"
            unlock_level = _unlock_level_for_index(tier - 1, count, max_level=max_lv)
            power = int(
                round(
                    float(scaling.get("base_power", 10))
                    + tier * float(scaling.get("power_per_tier", 0.42))
                    + unlock_level * float(scaling.get("power_per_mastery_level", 0.018))
                )
            )
            entry = {
                "skill_id": skill_id,
                "label": f"{wlabel} · {cat_name} {tier}",
                "category": cat_name,
                "weapon_class": weapon_class,
                "tier": tier,
                "type": cat_cfg.get("type", "active"),
                "power": 0 if cat_cfg.get("type") == "passive" else max(1, power),
                "mana_cost": 0 if cat_cfg.get("type") == "passive" else 5 + tier // 5,
                "range_tiles": 2 if cat_name == "move" else 1 + tier // 20,
                "cooldown_beats": max(0, 4 - tier // 20),
                "tags": list(cat_cfg.get("tags", [])),
                "skill_kind": "ranged_phys_single" if weapon_class == "bow" else "melee_phys_single",
                "unlock_axis": "weapon_mastery_level",
                "unlock_requirements": {"weapon_mastery_level": unlock_level, "weapon_class": weapon_class},
                "combat_pipeline": "catalog",
            }
            from utils.skill_names import apply_name_overrides

            skills[skill_id] = apply_name_overrides(entry)
            idx += 1
    return skills


@lru_cache(maxsize=8)
def _full_catalog(base_dir: str) -> dict[str, dict[str, Any]]:
    unlocks = load_progression_unlocks_config(base_dir)
    jobs_cfg = _read_json(base_dir, "config/job_stat_routes.json")
    mastery_cfg = _read_json(base_dir, "config/weapon_mastery.json")
    merged: dict[str, dict[str, Any]] = {}

    for job_id in unlocks.get("jobs", []):
        merged.update(_build_job_skills(job_id, unlocks, jobs_cfg))

    for wclass in mastery_cfg.get("classes", {}):
        merged.update(_build_weapon_class_skills(wclass, unlocks, mastery_cfg))

    return merged


def catalog_skill(skill_id: str, *, base_dir: str | Path) -> dict[str, Any] | None:
    return _full_catalog(str(Path(base_dir).resolve())).get(skill_id)


def catalog_skills_for_job(job_id: str, *, base_dir: str | Path) -> list[dict[str, Any]]:
    root = str(Path(base_dir).resolve())
    return [s for sid, s in _full_catalog(root).items() if sid.startswith(f"{job_id}_")]


def catalog_skill_count_for_job(job_id: str, *, base_dir: str | Path) -> int:
    return len(catalog_skills_for_job(job_id, base_dir=base_dir))


def catalog_skills_for_weapon_class(weapon_class: str, *, base_dir: str | Path) -> list[dict[str, Any]]:
    root = str(Path(base_dir).resolve())
    prefix = f"wpn_{weapon_class}_"
    return [s for sid, s in _full_catalog(root).items() if sid.startswith(prefix)]


def effective_skill_power(sdef: dict[str, Any], *, hero_levels: dict[str, Any]) -> float:
    """Scale catalog skill power by hero job/character levels at runtime."""
    if sdef.get("type") == "passive" or int(sdef.get("power", 0)) <= 0:
        return 0.0
    base = float(sdef.get("power", 8))
    tier = int(sdef.get("tier", 1))
    job_lv = int(hero_levels.get("job_level", 1))
    char_lv = int(hero_levels.get("character_level", 1))
    enhance = int(hero_levels.get("job_skill_enhance_tier", 1))
    mult = 1.0 + (job_lv / 999.0) * 0.5 + (char_lv / 999.0) * 0.2 + (enhance - 1) * 0.08
    return base * mult * (1.0 + (tier - 1) * 0.012)
