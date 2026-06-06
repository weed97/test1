"""Unified item catalog — import, equipment templates, procedural expansion, API manifest."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_GRADE_ORDER = ("common", "high", "rare", "hero", "legend", "mythic", "demigod")
_GRADE_LABELS = {
    "common": "일반",
    "high": "고급",
    "rare": "희귀",
    "hero": "영웅",
    "legend": "전설",
    "mythic": "신화",
    "demigod": "준신",
}


def _read_json(base_dir: str | Path, rel: str) -> dict[str, Any]:
    with (Path(base_dir) / rel).open(encoding="utf-8") as f:
        return json.load(f)


def _grade_mult(meta: dict[str, Any], grade: str) -> float:
    return float(meta.get("grade_stat_multipliers", {}).get(grade, 1.0))


@lru_cache(maxsize=4)
def load_item_catalog_meta(base_dir: str) -> dict[str, Any]:
    return _read_json(base_dir, "config/item_catalog_meta.json")


@lru_cache(maxsize=4)
def _build_catalog(base_dir: str) -> dict[str, dict[str, Any]]:
    meta = load_item_catalog_meta(base_dir)
    items: dict[str, dict[str, Any]] = {}

    def put(entry: dict[str, Any]) -> None:
        iid = str(entry["item_id"])
        items[iid] = entry

    # Legacy progression.json items (keep ids stable for tests)
    prog = _read_json(base_dir, "config/progression.json")
    for iid, raw in prog.get("items", {}).items():
        put(
            {
                "item_id": iid,
                "label": raw.get("label", iid),
                "category": raw.get("category", _slot_category(raw.get("slot", "weapon"))),
                "grade": raw.get("grade", "common"),
                "slot": raw.get("slot"),
                "equippable": True,
                "attack": raw.get("attack"),
                "defense": raw.get("defense"),
                "agility": raw.get("agility"),
                "min_job_level": int(raw.get("min_job_level", 1)),
                "jobs": list(raw.get("jobs", [])) or None,
                "weapon_class": raw.get("weapon_class"),
                "source": "progression",
                "icon": raw.get("icon", "⚔️"),
                "value_gold": int(raw.get("value_gold", 20)),
            }
        )

    # Imported web catalog (24)
    imp_path = Path(base_dir) / "config/item_catalog_import.json"
    if imp_path.is_file():
        for raw in _read_json(base_dir, "config/item_catalog_import.json").get("items", []):
            put(dict(raw))

    # Equipment templates (combat-grade gear)
    eq = _read_json(base_dir, "config/equipment_templates.json")
    for iid, raw in eq.get("weapons", {}).items():
        put(
            {
                "item_id": iid,
                "label": raw.get("label", iid),
                "category": "weapon",
                "grade": raw.get("grade", "common"),
                "slot": "weapon",
                "equippable": True,
                "weapon_class": raw.get("weapon_class", "one_handed_sword"),
                "attack": int(raw.get("attack", raw.get("base_damage_max", 10))),
                "defense": 0,
                "skills": list(raw.get("skills", [])),
                "affixes": list(raw.get("affixes", [])),
                "pierce_fraction": raw.get("pierce_fraction"),
                "sovereign_power_id": raw.get("sovereign_power_id"),
                "min_job_level": _min_level_for_grade(str(raw.get("grade", "common"))),
                "source": "equipment_template",
                "icon": "⚔️",
                "value_gold": _gold_for_grade(str(raw.get("grade", "common"))),
                "description": raw.get("comment") or f"{raw.get('label', iid)} — 전투 템플릿",
            }
        )
    for iid, raw in eq.get("armor", {}).items():
        put(
            {
                "item_id": iid,
                "label": raw.get("label", iid),
                "category": "armor",
                "grade": raw.get("grade", "common"),
                "slot": "armor",
                "equippable": True,
                "defense": int(raw.get("defense", 5)),
                "resist_physical": raw.get("resist_physical"),
                "resist_element": raw.get("resist_element"),
                "skills": list(raw.get("skills", [])),
                "affixes": list(raw.get("affixes", [])),
                "min_job_level": _min_level_for_grade(str(raw.get("grade", "common"))),
                "source": "equipment_template",
                "icon": "🛡️",
                "value_gold": _gold_for_grade(str(raw.get("grade", "common"))),
            }
        )
    for iid, raw in eq.get("accessories", {}).items():
        put(
            {
                "item_id": iid,
                "label": raw.get("label", iid),
                "category": "accessory",
                "grade": raw.get("grade", "common"),
                "slot": raw.get("slot", "accessory"),
                "equippable": True,
                "bonus_str": raw.get("bonus_str"),
                "bonus_vit": raw.get("bonus_vit"),
                "bonus_agi": raw.get("bonus_agi"),
                "skills": list(raw.get("skills", [])),
                "affixes": list(raw.get("affixes", [])),
                "min_job_level": _min_level_for_grade(str(raw.get("grade", "common"))),
                "source": "equipment_template",
                "icon": "💍",
                "value_gold": _gold_for_grade(str(raw.get("grade", "common"))),
            }
        )

    _generate_bulk(items, meta, base_dir)
    return items


def _slot_category(slot: str) -> str:
    if slot == "weapon":
        return "weapon"
    if slot == "armor":
        return "armor"
    return "accessory"


def _min_level_for_grade(grade: str) -> int:
    return {
        "common": 1,
        "high": 10,
        "rare": 30,
        "hero": 80,
        "legend": 200,
        "mythic": 500,
        "demigod": 800,
    }.get(grade, 1)


def _gold_for_grade(grade: str) -> int:
    return {
        "common": 25,
        "high": 120,
        "rare": 450,
        "hero": 1800,
        "legend": 6000,
        "mythic": 20000,
        "demigod": 80000,
    }.get(grade, 50)


def _generate_bulk(
    items: dict[str, dict[str, Any]], meta: dict[str, Any], base_dir: str
) -> None:
    wm = _read_json(base_dir, "config/weapon_mastery.json")
    grade_mult = meta.get("grade_stat_multipliers", {})
    gen_grades = ("common", "high", "rare", "hero", "legend")

    for wclass, wmeta in wm.get("classes", {}).items():
        wlabel = str(wmeta.get("label", wclass))
        parts = meta.get("weapon_name_parts", {}).get(wclass, ["무기"])
        for gi, grade in enumerate(gen_grades):
            mult = float(grade_mult.get(grade, 1.0))
            for pi, part in enumerate(parts):
                iid = f"gen_{wclass}_{grade}_{pi}"
                if iid in items:
                    continue
                base_atk = int(8 * mult + gi * 3 + pi)
                items[iid] = {
                    "item_id": iid,
                    "label": f"{_GRADE_LABELS[grade]} {wlabel}·{part}",
                    "category": "weapon",
                    "grade": grade,
                    "slot": "weapon",
                    "equippable": True,
                    "weapon_class": wclass,
                    "attack": base_atk,
                    "min_job_level": _min_level_for_grade(grade),
                    "source": "generated",
                    "icon": "⚔️",
                    "value_gold": _gold_for_grade(grade) + pi * 15,
                    "description": f"{wlabel} 숙련자용 {_GRADE_LABELS[grade]} 등급 무기.",
                }

    armor_parts = meta.get("armor_name_parts", ["갑옷"])
    for gi, grade in enumerate(gen_grades):
        mult = float(grade_mult.get(grade, 1.0))
        for pi, part in enumerate(armor_parts):
            iid = f"gen_armor_{grade}_{pi}"
            if iid not in items:
                items[iid] = {
                    "item_id": iid,
                    "label": f"{_GRADE_LABELS[grade]} {part}",
                    "category": "armor",
                    "grade": grade,
                    "slot": "armor",
                    "equippable": True,
                    "defense": int(5 * mult + gi * 2),
                    "min_job_level": _min_level_for_grade(grade),
                    "source": "generated",
                    "icon": "🛡️",
                    "value_gold": _gold_for_grade(grade),
                }

    acc_parts = meta.get("accessory_name_parts", ["반지"])
    for gi, grade in enumerate(gen_grades):
        for pi, part in enumerate(acc_parts):
            iid = f"gen_accessory_{grade}_{pi}"
            if iid not in items:
                items[iid] = {
                    "item_id": iid,
                    "label": f"{_GRADE_LABELS[grade]} {part}",
                    "category": "accessory",
                    "grade": grade,
                    "slot": "accessory",
                    "equippable": True,
                    "bonus_agi": max(1, gi + pi),
                    "min_job_level": _min_level_for_grade(grade),
                    "source": "generated",
                    "icon": "💍",
                    "value_gold": _gold_for_grade(grade) // 2,
                }

    for idx, base in enumerate(meta.get("material_bases", [])):
        tier = (idx % 5) + 1
        grade = gen_grades[min(idx // 4, len(gen_grades) - 1)]
        iid = f"mat_{idx:02d}_{re.sub(r'[^a-z0-9_]+', '_', base)[:20]}"
        if iid not in items:
            items[iid] = {
                "item_id": iid,
                "label": base,
                "category": "material",
                "grade": grade,
                "stackable": True,
                "craft_tier": tier,
                "source": "generated",
                "icon": "🪨",
                "value_gold": 5 + idx * 12,
                "description": f"제작·강화 재료 (티어 {tier}).",
            }

    prefixes = ("하급", "중급", "상급", "정예", "왕실")
    for idx, pot in enumerate(meta.get("potion_bases", [])):
        grade = str(pot.get("grade", "common"))
        iid = f"pot_{idx:02d}"
        if iid not in items:
            pref = prefixes[min(idx, len(prefixes) - 1)]
            items[iid] = {
                "item_id": iid,
                "label": f"{pref} {pot['suffix']}",
                "category": "potion",
                "grade": grade,
                "consumable": True,
                "stackable": True,
                "hp_restore": pot.get("hp_restore"),
                "mp_restore": pot.get("mp_restore"),
                "cure_poison": pot.get("cure_poison"),
                "buff_str": pot.get("buff_str"),
                "buff_agi": pot.get("buff_agi"),
                "buff_vit": pot.get("buff_vit"),
                "source": "generated",
                "icon": "🧪",
                "value_gold": _gold_for_grade(grade) // 3,
            }

    scroll_grades = ("common", "high", "rare", "hero", "legend")
    elements = ("화염", "냉기", "번개", "신성", "그림자")
    for ei, elem in enumerate(elements):
        for gi, grade in enumerate(scroll_grades):
            iid = f"scroll_{elem}_{grade}"
            if iid not in items:
                mult = float(grade_mult.get(grade, 1.0))
                items[iid] = {
                    "item_id": iid,
                    "label": f"{_GRADE_LABELS[grade]} {elem} 두루마리",
                    "category": "magic",
                    "grade": grade,
                    "consumable": True,
                    "stackable": True,
                    "scroll_damage": int(15 * mult + ei * 5),
                    "scroll_element": elem,
                    "source": "generated",
                    "icon": "📜",
                    "value_gold": _gold_for_grade(grade) // 2,
                    "description": f"일회용 {elem} 마법 — 전투 중 사용.",
                }


def get_item_def(item_id: str, *, base_dir: str | Path) -> dict[str, Any] | None:
    return _build_catalog(str(base_dir)).get(item_id)


def all_items(*, base_dir: str | Path) -> list[dict[str, Any]]:
    return list(_build_catalog(str(base_dir)).values())


def catalog_counts(*, base_dir: str | Path) -> dict[str, int]:
    items = all_items(base_dir=base_dir)
    by_cat: dict[str, int] = {}
    for it in items:
        cat = str(it.get("category", "misc"))
        by_cat[cat] = by_cat.get(cat, 0) + 1
    return {"total": len(items), "by_category": by_cat}


def build_catalog_manifest(
    *,
    base_dir: str | Path,
    category: str | None = None,
    grade: str | None = None,
    search: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> dict[str, Any]:
    meta = load_item_catalog_meta(str(base_dir))
    items = all_items(base_dir=base_dir)
    q = (search or "").strip().lower()

    def match(it: dict[str, Any]) -> bool:
        if category and it.get("category") != category:
            return False
        if grade and it.get("grade") != grade:
            return False
        if q:
            blob = f"{it.get('item_id')} {it.get('label')} {it.get('description', '')}".lower()
            if q not in blob:
                return False
        return True

    filtered = [it for it in items if match(it)]
    filtered.sort(key=lambda x: (_GRADE_ORDER.index(x.get("grade", "common")), str(x.get("label", ""))))
    page = filtered[offset : offset + limit]
    colors = meta.get("grade_colors", {})
    entries = []
    for it in page:
        g = str(it.get("grade", "common"))
        entries.append(
            {
                **it,
                "grade_label": _GRADE_LABELS.get(g, g),
                "rarity_color": colors.get(g, "#9aa0a6"),
            }
        )
    return {
        "meta": {
            "title": meta.get("title"),
            "version": meta.get("version", 1),
            "categories": meta.get("categories", []),
            "grade_colors": colors,
        },
        "counts": catalog_counts(base_dir=base_dir),
        "filtered_count": len(filtered),
        "offset": offset,
        "limit": limit,
        "items": entries,
    }


def clear_catalog_cache() -> None:
    _build_catalog.cache_clear()
    load_item_catalog_meta.cache_clear()
