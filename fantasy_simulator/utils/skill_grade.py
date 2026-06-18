"""Skill grade bands — character level gates for common → mythic catalog skills."""

from __future__ import annotations

from typing import Any

from utils.skill_catalog import load_progression_unlocks_config

GRADE_ORDER: tuple[str, ...] = ("common", "high", "rare", "hero", "legend", "mythic")

_DEFAULT_BANDS: list[dict[str, Any]] = [
    {"grade": "common", "min": 1, "max": 100, "label_ko": "일반"},
    {"grade": "high", "min": 101, "max": 200, "label_ko": "고급"},
    {"grade": "rare", "min": 201, "max": 400, "label_ko": "희귀"},
    {"grade": "hero", "min": 401, "max": 600, "label_ko": "영웅"},
    {"grade": "legend", "min": 601, "max": 800, "label_ko": "전설"},
    {"grade": "mythic", "min": 801, "max": 999, "label_ko": "신화"},
]


def skill_grade_bands(*, base_dir: str) -> list[dict[str, Any]]:
    cfg = load_progression_unlocks_config(base_dir)
    bands = cfg.get("skill_grade_bands", {}).get("bands")
    if isinstance(bands, list) and bands:
        return bands
    return list(_DEFAULT_BANDS)


def grade_for_unlock_level(level: int, *, base_dir: str) -> str:
    lv = max(1, min(999, int(level)))
    for band in skill_grade_bands(base_dir=base_dir):
        if int(band["min"]) <= lv <= int(band["max"]):
            return str(band["grade"])
    return "mythic"


def grade_label_ko(grade: str, *, base_dir: str) -> str:
    for band in skill_grade_bands(base_dir=base_dir):
        if str(band["grade"]) == grade:
            return str(band.get("label_ko", grade))
    labels = load_progression_unlocks_config(base_dir).get("skill_grade_bands", {}).get(
        "labels", {}
    )
    return str(labels.get(grade, grade))


def min_level_for_grade(grade: str, *, base_dir: str) -> int:
    for band in skill_grade_bands(base_dir=base_dir):
        if str(band["grade"]) == grade:
            return int(band["min"])
    return 1


def max_level_for_grade(grade: str, *, base_dir: str) -> int:
    for band in skill_grade_bands(base_dir=base_dir):
        if str(band["grade"]) == grade:
            return int(band["max"])
    return 999


def hero_can_learn_grade(character_level: int, grade: str, *, base_dir: str) -> bool:
    """True when character level has reached this skill grade's band."""
    return int(character_level) >= min_level_for_grade(grade, base_dir=base_dir)


def grade_cooldown_beats(grade: str, *, base_dir: str) -> int:
    cfg = load_progression_unlocks_config(base_dir)
    table = cfg.get("skill_grade_bands", {}).get("cooldown_beats", {})
    return int(table.get(grade, table.get("common", 0)))


def primary_unlock_level(sdef: dict[str, Any]) -> int:
    """Level on the skill's unlock axis used to assign catalog grade."""
    reqs = sdef.get("unlock_requirements", {})
    axis = str(sdef.get("unlock_axis", "job_level"))
    if axis == "character_level":
        return int(reqs.get("character_level", 1))
    if axis == "weapon_mastery_level":
        return int(reqs.get("weapon_mastery_level", 1))
    return int(reqs.get("job_level", reqs.get("character_level", 1)))


def enrich_skill_grade(sdef: dict[str, Any], *, base_dir: str) -> dict[str, Any]:
    """Attach skill_grade metadata to a catalog skill dict (mutates copy)."""
    out = dict(sdef)
    ulv = primary_unlock_level(out)
    grade = grade_for_unlock_level(ulv, base_dir=base_dir)
    out["skill_grade"] = grade
    out["grade_label_ko"] = grade_label_ko(grade, base_dir=base_dir)
    out["grade_unlock_level"] = ulv
    out["grade_min_character_level"] = min_level_for_grade(grade, base_dir=base_dir)
    min_cd = grade_cooldown_beats(grade, base_dir=base_dir)
    if grade in ("hero", "legend", "mythic"):
        out["cooldown_beats"] = max(int(out.get("cooldown_beats", 0)), min_cd)
    return out


def grade_bands_summary(*, base_dir: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for band in skill_grade_bands(base_dir=base_dir):
        g = str(band["grade"])
        out.append(
            {
                "grade": g,
                "label_ko": band.get("label_ko", grade_label_ko(g, base_dir=base_dir)),
                "min": int(band["min"]),
                "max": int(band["max"]),
                "cooldown_beats": grade_cooldown_beats(g, base_dir=base_dir),
            }
        )
    return out
