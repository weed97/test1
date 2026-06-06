"""Level-axis unlocks — skills, equip gates, milestones up to Lv999."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.skill_catalog import (
    catalog_skills_for_job,
    catalog_skills_for_weapon_class,
    load_progression_unlocks_config,
)


def _read_json(base_dir: str | Path, rel: str) -> dict[str, Any]:
    with (Path(base_dir) / rel).open(encoding="utf-8") as f:
        return json.load(f)


def xp_threshold_for_level(level: int, formula: dict[str, Any]) -> int:
    if level <= 1:
        return 0
    base = float(formula.get("base", 80))
    exp = float(formula.get("exponent", 1.82))
    return int(base * ((level - 1) ** exp))


def level_from_xp(xp: int, formula: dict[str, Any], *, max_level: int = 999) -> int:
    lv = 1
    while lv < max_level and xp >= xp_threshold_for_level(lv + 1, formula):
        lv += 1
    return lv


def mastery_rank_for_level(level: int, *, base_dir: str | Path) -> str:
    cfg = _read_json(base_dir, "config/weapon_mastery.json")
    thresholds = cfg.get("rank_thresholds", {})
    rank = "novice"
    for name, need in sorted(thresholds.items(), key=lambda x: int(x[1])):
        if level >= int(need):
            rank = name
    return rank


def _normalize_job_block(block: Any, *, fallback_level: int = 1, fallback_xp: int = 0) -> dict[str, Any]:
    if isinstance(block, int):
        return {"level": block, "xp": 0}
    if not isinstance(block, dict):
        return {"level": fallback_level, "xp": fallback_xp}
    level = int(block.get("level", block.get("job_level", fallback_level)))
    return {"level": level, "xp": int(block.get("xp", fallback_xp))}


def _normalize_weapon_mastery_block(
    block: Any,
    *,
    base_dir: str | Path,
    fallback_level: int = 1,
) -> dict[str, Any]:
    if isinstance(block, int):
        level = min(int(block), 999)
        return {
            "level": level,
            "xp": 0,
            "rank": mastery_rank_for_level(level, base_dir=base_dir),
        }
    if not isinstance(block, dict):
        level = fallback_level
        return {
            "level": level,
            "xp": 0,
            "rank": mastery_rank_for_level(level, base_dir=base_dir),
        }
    level = min(999, int(block.get("level", block.get("weapon_mastery_level", fallback_level))))
    return {
        "level": level,
        "xp": int(block.get("xp", 0)),
        "rank": mastery_rank_for_level(level, base_dir=base_dir),
    }


def _rank_index(rank_order: list[str], rank: str) -> int:
    try:
        return rank_order.index(rank)
    except ValueError:
        return -1


def normalize_hero_progress(hero: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    """Migrate legacy hero dict to multi-axis Lv999 schema."""
    prog = load_progression_config(base_dir)
    max_lv = int(prog.get("character", {}).get("max_level", 999))
    job_id = str(hero.get("active_job_id") or hero.get("job_id", "wanderer"))
    hero["active_job_id"] = job_id
    hero["job_id"] = job_id  # legacy compat

    if "jobs" not in hero:
        jl = int(hero.get("job_level", 1))
        hero["jobs"] = {job_id: {"level": jl, "xp": int(hero.get("xp", 0))}}
    hero["jobs"] = {
        jid: _normalize_job_block(
            block,
            fallback_level=int(hero.get("job_level", 1)),
            fallback_xp=int(hero.get("xp", 0)),
        )
        for jid, block in hero["jobs"].items()
    }
    if job_id not in hero["jobs"]:
        hero["jobs"][job_id] = {
            "level": int(hero.get("job_level", 1)),
            "xp": int(hero.get("xp", 0)),
        }
    jl = int(hero["jobs"][job_id].get("level", hero.get("job_level", 1)))
    if int(hero.get("job_level", 1)) > jl:
        jl = int(hero["job_level"])
        hero["jobs"][job_id]["level"] = jl
    hero["job_level"] = jl
    hero.setdefault("character_level", int(hero.get("character_level", max(1, jl))))
    hero.setdefault("character_xp", int(hero.get("character_xp", 0)))

    hero.setdefault("weapon_masteries", {})
    if not hero["weapon_masteries"]:
        wlv = int(hero.get("weapon_mastery_level", 1))
        wclass = str(hero.get("weapon_class", "one_handed_sword"))
        hero["weapon_masteries"][wclass] = {
            "level": wlv,
            "xp": 0,
            "rank": mastery_rank_for_level(wlv, base_dir=base_dir),
        }

    hero["weapon_masteries"] = {
        wclass: _normalize_weapon_mastery_block(
            block,
            base_dir=base_dir,
            fallback_level=int(hero.get("weapon_mastery_level", 1)),
        )
        for wclass, block in hero["weapon_masteries"].items()
    }
    for block in hero["weapon_masteries"].values():
        block["level"] = min(max_lv, int(block["level"]))
        block["rank"] = mastery_rank_for_level(block["level"], base_dir=base_dir)

    hero.setdefault("unlocked_skills", [])
    hero.setdefault("equip_unlocks", {"milestones": [], "grades": ["common"]})
    hero.setdefault("passive_slots", 1)
    hero.setdefault("job_skill_enhance_tier", 1)
    return hero


def load_progression_config(base_dir: str | Path) -> dict[str, Any]:
    return _read_json(base_dir, "config/progression.json")


def hero_level_snapshot(hero: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    if hero.get("jobs") or hero.get("weapon_masteries"):
        h = normalize_hero_progress(hero, base_dir=base_dir)
        job_id = str(h.get("active_job_id", "wanderer"))
        job_lv = int(h["jobs"].get(job_id, {}).get("level", 1))
        char_lv = int(h.get("character_level", 1))
        masteries = {
            wc: int(b.get("level", 1)) for wc, b in h.get("weapon_masteries", {}).items()
        }
        return {
            "character_level": char_lv,
            "job_id": job_id,
            "job_level": job_lv,
            "weapon_masteries": masteries,
            "job_skill_enhance_tier": int(h.get("job_skill_enhance_tier", 1)),
        }
    stats = hero.get("stats") or {}
    job_id = str(hero.get("job_id", "wanderer"))
    char_lv = int(hero.get("character_level", stats.get("level", 1)))
    job_lv = int(hero.get("job_level", char_lv))
    wlv = int(hero.get("weapon_mastery_level", 1))
    wclass = str(hero.get("weapon_class", "one_handed_sword"))
    return {
        "character_level": char_lv,
        "job_id": job_id,
        "job_level": job_lv,
        "weapon_masteries": {wclass: wlv},
        "job_skill_enhance_tier": 1,
    }


def _requirements_met(reqs: dict[str, Any], snap: dict[str, Any], *, job_id: str) -> bool:
    if "character_level" in reqs and snap["character_level"] < int(reqs["character_level"]):
        return False
    if "job_level" in reqs and snap["job_level"] < int(reqs["job_level"]):
        return False
    wml = reqs.get("weapon_mastery_level")
    wclass = reqs.get("weapon_class")
    if wml is not None:
        wc = str(wclass) if wclass else next(iter(snap["weapon_masteries"]), "")
        if snap["weapon_masteries"].get(wc, 0) < int(wml):
            return False
    if wclass and snap["weapon_masteries"].get(str(wclass), 0) < 1:
        return False
    return True


def skills_available_for_hero(hero: dict[str, Any], *, base_dir: str | Path) -> list[str]:
    snap = hero_level_snapshot(hero, base_dir=base_dir)
    job_id = snap["job_id"]
    available: list[str] = []
    for sdef in catalog_skills_for_job(job_id, base_dir=base_dir):
        if _requirements_met(sdef.get("unlock_requirements", {}), snap, job_id=job_id):
            available.append(str(sdef["skill_id"]))
    for wclass, wlv in snap["weapon_masteries"].items():
        for sdef in catalog_skills_for_weapon_class(wclass, base_dir=base_dir):
            reqs = dict(sdef.get("unlock_requirements", {}))
            reqs.setdefault("weapon_mastery_level", 1)
            reqs.setdefault("weapon_class", wclass)
            snap_weapon = dict(snap)
            snap_weapon["weapon_masteries"] = {wclass: wlv}
            if _requirements_met(reqs, snap_weapon, job_id=job_id):
                available.append(str(sdef["skill_id"]))
    return available


def sync_unlocked_skills(hero: dict[str, Any], *, base_dir: str | Path) -> list[str]:
    """Add newly eligible catalog skills to hero.unlocked_skills; return new IDs."""
    h = normalize_hero_progress(hero, base_dir=base_dir)
    eligible = set(skills_available_for_hero(h, base_dir=base_dir))
    had = set(h.get("unlocked_skills", []))
    new_ids = sorted(eligible - had)
    if new_ids:
        h.setdefault("unlocked_skills", []).extend(new_ids)
    return new_ids


def apply_milestone_unlocks(hero: dict[str, Any], *, base_dir: str | Path) -> list[str]:
    """Character/job/weapon milestones → equip_unlocks, passive slots, enhance tier."""
    unlocks = load_progression_unlocks_config(base_dir)
    h = normalize_hero_progress(hero, base_dir=base_dir)
    snap = hero_level_snapshot(h, base_dir=base_dir)
    lines: list[str] = []
    eq = h.setdefault("equip_unlocks", {"milestones": [], "grades": ["common"]})
    seen = set(eq.get("milestones", []))

    curve = unlocks.get("equip_unlock_curve", {})
    for m in curve.get("weapon_mastery_milestones", []):
        for wlv in snap["weapon_masteries"].values():
            if wlv >= int(m["level"]) and m["unlock"] not in seen:
                seen.add(m["unlock"])
                eq.setdefault("milestones", []).append(m["unlock"])
                lines.append(f"[해금] 장비·기능: {m['unlock']}")
    for m in curve.get("character_level_milestones", []):
        if snap["character_level"] >= int(m["level"]) and m["unlock"] not in seen:
            seen.add(m["unlock"])
            eq.setdefault("milestones", []).append(m["unlock"])
            lines.append(f"[해금] {m['unlock']}")
    for m in curve.get("job_level_milestones", []):
        if snap["job_level"] >= int(m["level"]) and m["unlock"] not in seen:
            seen.add(m["unlock"])
            eq.setdefault("milestones", []).append(m["unlock"])
            lines.append(f"[해금] {m['unlock']}")

    ms = unlocks.get("milestone_unlocks", {}).get("character_level", {})
    slot_every = int(ms.get("passive_slot_every", 50))
    max_slots = int(ms.get("max_passive_slots", 20))
    new_slots = 1 + snap["character_level"] // slot_every
    h["passive_slots"] = min(max_slots, new_slots)

    for m in unlocks.get("equip_unlock_curve", {}).get("job_level_milestones", []):
        if snap["job_level"] >= int(m["level"]) and "enhance" in m["unlock"]:
            tier = int(str(m["unlock"]).split("_tier_")[-1]) if "_tier_" in m["unlock"] else 1
            h["job_skill_enhance_tier"] = max(int(h.get("job_skill_enhance_tier", 1)), tier)

    return lines


def can_wield_grade(
    hero: dict[str, Any],
    grade: str,
    *,
    weapon_class: str,
    base_dir: str | Path,
) -> tuple[bool, str]:
    """Check item_grades wield_gates + hero levels."""
    grades = _read_json(base_dir, "config/item_grades.json")
    gate = grades.get("wield_gates", {}).get(grade.lower())
    if not gate:
        return True, ""
    h = normalize_hero_progress(hero, base_dir=base_dir)
    snap = hero_level_snapshot(h, base_dir=base_dir)
    if snap["character_level"] < int(gate.get("min_character_level", 1)):
        return False, f"캐릭터 Lv{gate['min_character_level']} 필요"
    wlv = snap["weapon_masteries"].get(weapon_class, 0)
    if wlv < int(gate.get("min_weapon_class_level", 1)):
        return False, f"{weapon_class} 숙련 Lv{gate['min_weapon_class_level']} 필요"
    need_rank = gate.get("min_mastery_rank")
    if need_rank:
        thresholds = _read_json(base_dir, "config/weapon_mastery.json").get("rank_thresholds", {})
        rank_order = sorted(thresholds.keys(), key=lambda k: int(thresholds[k]))
        have = mastery_rank_for_level(wlv, base_dir=base_dir)
        if _rank_index(rank_order, have) < _rank_index(rank_order, str(need_rank)):
            return False, f"숙련 경지 {need_rank} 필요"
    return True, ""


def can_equip_template(
    hero: dict[str, Any],
    template: dict[str, Any],
    *,
    weapon_class: str,
    base_dir: str | Path,
) -> tuple[bool, str]:
    grade = str(template.get("grade", "common"))
    ok, reason = can_wield_grade(hero, grade, weapon_class=weapon_class, base_dir=base_dir)
    if not ok:
        return False, reason
    return True, ""


def unlock_status_for_hero(hero: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    h = normalize_hero_progress(hero, base_dir=base_dir)
    snap = hero_level_snapshot(h, base_dir=base_dir)
    job_id = snap["job_id"]
    unlocks = load_progression_unlocks_config(base_dir)
    job_total = int(unlocks["skill_catalog"]["skills_per_job"])
    unlocked = list(h.get("unlocked_skills", []))
    job_unlocked = [s for s in unlocked if s.startswith(f"{job_id}_")]
    wpn_unlocked = [s for s in unlocked if s.startswith("wpn_")]
    return {
        "levels": snap,
        "passive_slots": int(h.get("passive_slots", 1)),
        "job_skill_enhance_tier": int(h.get("job_skill_enhance_tier", 1)),
        "equip_unlocks": h.get("equip_unlocks", {}),
        "skills": {
            "job_unlocked_count": len(job_unlocked),
            "job_total": job_total,
            "weapon_unlocked_count": len(wpn_unlocked),
            "weapon_total_per_class": int(unlocks["weapon_skill_catalog"]["skills_per_class"]),
            "unlocked_sample": unlocked[:12],
            "next_job_skills": _next_locked_skills(h, job_id, base_dir=base_dir, limit=5),
        },
    }


def _next_locked_skills(
    hero: dict[str, Any], job_id: str, *, base_dir: str | Path, limit: int = 5
) -> list[dict[str, Any]]:
    snap = hero_level_snapshot(hero, base_dir=base_dir)
    had = set(hero.get("unlocked_skills", []))
    nxt: list[dict[str, Any]] = []
    for sdef in catalog_skills_for_job(job_id, base_dir=base_dir):
        sid = str(sdef["skill_id"])
        if sid in had:
            continue
        if not _requirements_met(sdef.get("unlock_requirements", {}), snap, job_id=job_id):
            nxt.append(
                {
                    "skill_id": sid,
                    "label": sdef.get("label"),
                    "unlock_requirements": sdef.get("unlock_requirements"),
                }
            )
        if len(nxt) >= limit:
            break
    return nxt


def grant_axis_xp(
    hero: dict[str, Any],
    *,
    character_xp: int = 0,
    job_xp: int = 0,
    weapon_xp: int = 0,
    weapon_class: str | None = None,
    base_dir: str | Path,
) -> list[str]:
    """Grant XP on all axes, sync levels, unlock skills + milestones."""
    prog = load_progression_config(base_dir)
    unlocks = load_progression_unlocks_config(base_dir)
    max_lv = int(unlocks.get("max_level", 999))
    h = normalize_hero_progress(hero, base_dir=base_dir)
    lines: list[str] = []
    job_id = str(h.get("active_job_id", "wanderer"))

    if character_xp:
        h["character_xp"] = int(h.get("character_xp", 0)) + character_xp
        old = int(h.get("character_level", 1))
        h["character_level"] = level_from_xp(
            int(h["character_xp"]),
            prog.get("character", {}).get("xp_formula", {}),
            max_level=max_lv,
        )
        if h["character_level"] > old:
            lines.append(f"[성장] 캐릭터 Lv{h['character_level']}")

    if job_xp:
        jb = h["jobs"].setdefault(job_id, {"level": 1, "xp": 0})
        jb["xp"] = int(jb.get("xp", 0)) + job_xp
        old = int(jb.get("level", 1))
        jb["level"] = level_from_xp(
            int(jb["xp"]),
            prog.get("job_progression", {}).get("xp_formula", {}),
            max_level=max_lv,
        )
        h["job_level"] = jb["level"]
        if jb["level"] > old:
            lines.append(f"[성장] 직업 Lv{jb['level']} ({job_id})")

    if weapon_xp and weapon_class:
        wm = h["weapon_masteries"].setdefault(
            weapon_class, {"level": 1, "xp": 0, "rank": "novice"}
        )
        wm["xp"] = int(wm.get("xp", 0)) + weapon_xp
        old = int(wm.get("level", 1))
        wm["level"] = level_from_xp(
            int(wm["xp"]),
            _read_json(base_dir, "config/weapon_mastery.json").get("xp_formula", {}),
            max_level=max_lv,
        )
        wm["rank"] = mastery_rank_for_level(wm["level"], base_dir=base_dir)
        if wm["level"] > old:
            lines.append(f"[성장] {weapon_class} 숙련 Lv{wm['level']} ({wm['rank']})")

    new_skills = sync_unlocked_skills(h, base_dir=base_dir)
    for sk in new_skills[:8]:
        lines.append(f"[스킬 해금] {sk}")
    if len(new_skills) > 8:
        lines.append(f"[스킬 해금] …외 {len(new_skills) - 8}개")

    lines.extend(apply_milestone_unlocks(h, base_dir=base_dir))
    return lines
