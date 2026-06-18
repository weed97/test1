"""Skill tree payload for API / Godot UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.level_unlocks import hero_level_snapshot, skills_available_for_hero, unlock_status_for_hero
from utils.skill_catalog import catalog_skills_for_job, catalog_skills_for_weapon_class
from utils.skill_grade import grade_bands_summary, hero_can_learn_grade
from utils.skill_names import SIGNATURE_SKILLS


def build_skill_tree(
    hero: dict[str, Any],
    *,
    base_dir: str | Path,
    character_id: str = "",
) -> dict[str, Any]:
    from utils.level_unlocks import normalize_hero_progress

    h = normalize_hero_progress(hero, base_dir=base_dir)
    snap = hero_level_snapshot(h, base_dir=base_dir)
    job_id = snap["job_id"]
    unlocked = set(h.get("unlocked_skills", []))
    eligible = set(skills_available_for_hero(h, base_dir=base_dir))

    categories: dict[str, list[dict[str, Any]]] = {}
    for sdef in catalog_skills_for_job(job_id, base_dir=base_dir):
        cat = str(sdef.get("category", "other"))
        sid = str(sdef["skill_id"])
        grade = str(sdef.get("skill_grade", "common"))
        categories.setdefault(cat, []).append(
            {
                "skill_id": sid,
                "label": sdef.get("label"),
                "tier": sdef.get("tier"),
                "skill_grade": grade,
                "grade_label_ko": sdef.get("grade_label_ko"),
                "type": sdef.get("type", "active"),
                "power": sdef.get("power"),
                "cooldown_beats": sdef.get("cooldown_beats"),
                "unlocked": sid in unlocked,
                "eligible": sid in eligible,
                "grade_learnable": hero_can_learn_grade(
                    int(snap["character_level"]), grade, base_dir=base_dir
                ),
                "unlock_requirements": sdef.get("unlock_requirements"),
                "signature": bool(sdef.get("signature")),
                "named_tier": bool(sdef.get("named_tier")),
            }
        )

    weapon_trees: dict[str, list[dict[str, Any]]] = {}
    for wclass, wlv in snap["weapon_masteries"].items():
        entries: list[dict[str, Any]] = []
        for sdef in catalog_skills_for_weapon_class(wclass, base_dir=base_dir):
            sid = str(sdef["skill_id"])
            req = int(sdef.get("unlock_requirements", {}).get("weapon_mastery_level", 999))
            grade = str(sdef.get("skill_grade", "common"))
            entries.append(
                {
                    "skill_id": sid,
                    "label": sdef.get("label"),
                    "tier": sdef.get("tier"),
                    "skill_grade": grade,
                    "grade_label_ko": sdef.get("grade_label_ko"),
                    "cooldown_beats": sdef.get("cooldown_beats"),
                    "unlocked": sid in unlocked,
                    "eligible": wlv >= req
                    and hero_can_learn_grade(
                        int(snap["character_level"]), grade, base_dir=base_dir
                    ),
                    "grade_learnable": hero_can_learn_grade(
                        int(snap["character_level"]), grade, base_dir=base_dir
                    ),
                    "unlock_requirements": sdef.get("unlock_requirements"),
                }
            )
        weapon_trees[wclass] = entries

    for cat in categories.values():
        cat.sort(key=lambda x: int(x.get("tier", 0)))

    status = unlock_status_for_hero(h, base_dir=base_dir)
    return {
        "character_id": character_id,
        "job_id": job_id,
        "levels": snap,
        "passive_slots": int(h.get("passive_slots", 1)),
        "job_skill_enhance_tier": int(h.get("job_skill_enhance_tier", 1)),
        "equip_unlocks": h.get("equip_unlocks", {}),
        "signatures": SIGNATURE_SKILLS.get(job_id, []),
        "categories": categories,
        "weapon_skills": weapon_trees,
        "next_unlocks": status["skills"].get("next_job_skills", []),
        "counts": {
            "job_unlocked": status["skills"]["job_unlocked_count"],
            "job_total": status["skills"]["job_total"],
        },
        "skill_grade_bands": grade_bands_summary(base_dir=base_dir),
    }
