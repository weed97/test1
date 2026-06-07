"""Kingdom charter — barrier (결계), fortress, military, interior, laws, upkeep."""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path
from typing import Any

from utils.settlement_build import (
    _deduct_materials,
    _materials_available,
    _party_gold,
    _set_party_gold,
    get_player_settlement,
)


def load_kingdom_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "kingdom_system.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _eco(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("flags", {}).setdefault("ecology", {})


def get_kingdom_charter(state: dict[str, Any]) -> dict[str, Any] | None:
    charter = _eco(state).get("kingdom_charter")
    return charter if isinstance(charter, dict) else None


def _default_charter(
    *,
    kingdom_id: str,
    name: str,
    map_id: str,
    x: int,
    y: int,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    barrier_cfg = cfg.get("barrier", {})
    base_hp = int(barrier_cfg.get("base_max_hp", 12000))
    laws = dict(cfg.get("default_laws", {}))
    return {
        "kingdom_id": kingdom_id,
        "name": name,
        "map_id": map_id,
        "x": int(x),
        "y": int(y),
        "laws": laws,
        "barrier": {
            "level": 1,
            "hp": base_hp,
            "max_hp": base_hp,
            "regen_per_beat": int(barrier_cfg.get("regen_per_beat", 80)),
            "physical_destroy_blocked": bool(
                barrier_cfg.get("physical_destroy_blocked", True)
            ),
            "ritual_level": 0,
        },
        "fortifications": {
            "walls_level": 0,
            "tower_count": 0,
            "wall_defense": 0,
            "tower_attack": 0,
        },
        "military": {
            "scout": 0,
            "guard": 0,
            "wall_archer": 0,
            "elite": 0,
            "in_training": [],
        },
        "interior": {
            "farmland_plots": 0,
            "food_store": 120,
            "city_level": 0,
            "population_cap": 0,
            "training_ground_level": 0,
        },
        "stability": 75,
        "prosperity": 95,
        "unpaid_beats": 0,
        "physically_destroyed": False,
    }


def _founding_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("founding", {})


def founding_cost_preview(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    """What it costs / whether player can start kingdom founding."""
    kcfg = load_kingdom_config(base_dir)
    fdef = _founding_cfg(kcfg)
    ps = get_player_settlement(state)
    gold = _party_gold(state)
    direct = int(fdef.get("gold_cost", 0))
    ancillary = int(fdef.get("ancillary_gold", 0))
    total_gold = direct + ancillary
    materials = dict(fdef.get("materials", {}))
    required = set(fdef.get("requires_buildings", []))
    done = {b.get("building_id") for b in ps.get("completed_buildings", [])}
    missing_buildings = sorted(required - done)
    checks: list[dict[str, Any]] = []
    lvl = int(ps.get("construction_level", 1))
    checks.append(
        {
            "id": "construction_level",
            "ok": lvl >= int(fdef.get("min_construction_level", 5)),
            "need": fdef.get("min_construction_level"),
            "have": lvl,
        }
    )
    checks.append(
        {
            "id": "buildings",
            "ok": not missing_buildings,
            "need": sorted(required),
            "missing": missing_buildings,
        }
    )
    workers = int(ps.get("hired_workers", 0))
    min_w = int(fdef.get("min_hired_workers", 8))
    checks.append({"id": "workers", "ok": workers >= min_w, "need": min_w, "have": workers})
    checks.append(
        {
            "id": "gold",
            "ok": gold >= total_gold,
            "need": total_gold,
            "direct": direct,
            "ancillary": ancillary,
            "have": gold,
        }
    )
    mats_ok = _materials_available(ps, materials)
    checks.append({"id": "materials", "ok": mats_ok, "need": materials, "have": dict(ps.get("stockpile", {}))})
    checks.append({"id": "not_kingdom", "ok": not ps.get("is_kingdom"), "error": "이미 왕국"})
    can = all(c["ok"] for c in checks)
    return {
        "can_found": can,
        "checks": checks,
        "gold_cost_direct": direct,
        "gold_cost_ancillary": ancillary,
        "gold_cost_total": total_gold,
        "ancillary_note": fdef.get("ancillary_note", ""),
        "materials": materials,
        "build_points": int(fdef.get("build_points", 2500)),
        "barrier_preview": kcfg.get("barrier", {}),
        "default_laws": kcfg.get("default_laws", {}),
    }


def can_found_kingdom(state: dict[str, Any], *, base_dir: str | Path) -> tuple[bool, str]:
    preview = founding_cost_preview(state, base_dir=base_dir)
    if preview["can_found"]:
        return True, ""
    for c in preview["checks"]:
        if not c["ok"]:
            if c["id"] == "gold":
                return False, f"골드 부족 (필요 {c['need']}, 보유 {c['have']})"
            if c["id"] == "materials":
                return False, "자재 부족"
            if c["id"] == "buildings":
                return False, f"필수 건물 미완공: {', '.join(c['missing'])}"
            if c["id"] == "workers":
                return False, f"고용 인력 {c['need']}명 이상 필요 (현재 {c['have']})"
            if c["id"] == "construction_level":
                return False, f"건축 레벨 {c['need']} 필요 (현재 {c['have']})"
            if c["id"] == "not_kingdom":
                return False, "이미 왕국 승격됨"
    return False, "왕국 선포 조건 미충족"


def deduct_founding_costs(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    kcfg = load_kingdom_config(base_dir)
    fdef = _founding_cfg(kcfg)
    ps = get_player_settlement(state)
    direct = int(fdef.get("gold_cost", 0))
    ancillary = int(fdef.get("ancillary_gold", 0))
    total = direct + ancillary
    gold = _party_gold(state)
    if gold < total:
        return {"ok": False, "error": f"골드 부족 (필요 {total}, 보유 {gold})"}
    if not _materials_available(ps, fdef.get("materials", {})):
        return {"ok": False, "error": "자재 부족"}
    _set_party_gold(state, gold - total)
    _deduct_materials(ps, fdef.get("materials", {}))
    return {
        "ok": True,
        "gold_spent_direct": direct,
        "gold_spent_ancillary": ancillary,
        "gold_spent_total": total,
        "materials_spent": fdef.get("materials"),
    }


def complete_kingdom_founding(
    state: dict[str, Any],
    *,
    map_id: str,
    x: int,
    y: int,
    name: str = "플레이어 왕국",
    base_dir: str | Path,
) -> dict[str, Any]:
    """Create charter after kingdom construction project completes."""
    kcfg = load_kingdom_config(base_dir)
    ps = get_player_settlement(state)
    eco = _eco(state)
    kingdom_id = f"kr_{uuid.uuid4().hex[:10]}"
    charter = _default_charter(
        kingdom_id=kingdom_id,
        name=name,
        map_id=map_id,
        x=x,
        y=y,
        cfg=kcfg,
    )
    eco["kingdom_charter"] = charter
    ps["is_kingdom"] = True
    ps["kingdom_id"] = kingdom_id

    profile = eco.get("player_profile") or {}
    civ_id = profile.get("player_civilization_id")
    if civ_id:
        from utils.agent_competition import get_civilization_state

        cs = get_civilization_state(state, str(civ_id))
        cs["prosperity"] = max(int(cs.get("prosperity", 0)), 95)
        cs["stage_id"] = "kingdom"

    return {
        "ok": True,
        "kingdom_id": kingdom_id,
        "charter": charter,
        "message": (
            f"[왕국] '{name}' 결계가 전개되었다. 물리적 멸망은 결계 붕괴 전까지 불가. "
            f"({map_id} {x},{y})"
        ),
    }


def _recalc_barrier_max(charter: dict[str, Any], cfg: dict[str, Any]) -> None:
    barrier_cfg = cfg.get("barrier", {})
    base = int(barrier_cfg.get("base_max_hp", 12000))
    ritual_lvl = int(charter.get("barrier", {}).get("ritual_level", 0))
    ritual_mult = 1.0
    for row in cfg.get("fortifications", {}).get("barrier_ritual", {}).get("levels", []):
        if int(row.get("level", 0)) <= ritual_lvl:
            ritual_mult = float(row.get("hp_mult", ritual_mult))
    walls = int(charter.get("fortifications", {}).get("walls_level", 0))
    wall_bonus = 0
    for row in cfg.get("fortifications", {}).get("walls", {}).get("levels", []):
        if int(row.get("level", 0)) <= walls:
            wall_bonus = int(row.get("hp_bonus", wall_bonus))
    max_hp = int((base + wall_bonus) * ritual_mult)
    b = charter.setdefault("barrier", {})
    b["max_hp"] = max_hp
    b["hp"] = min(int(b.get("hp", max_hp)), max_hp)


def _military_total(charter: dict[str, Any]) -> int:
    m = charter.get("military", {})
    return sum(int(m.get(k, 0)) for k in ("scout", "guard", "wall_archer", "elite"))


def _military_cap(charter: dict[str, Any], cfg: dict[str, Any]) -> int:
    mil = cfg.get("military", {})
    tg = int(charter.get("interior", {}).get("training_ground_level", 0))
    return int(mil.get("unit_caps_base", 20)) + tg * int(
        mil.get("unit_caps_per_training_level", 15)
    )


def compute_upkeep(charter: dict[str, Any], cfg: dict[str, Any]) -> dict[str, int]:
    up = cfg.get("upkeep", {})
    m = charter.get("military", {})
    mil_count = _military_total(charter) + len(m.get("in_training", []))
    towers = int(charter.get("fortifications", {}).get("tower_count", 0))
    city = int(charter.get("interior", {}).get("city_level", 0))
    gold = (
        int(up.get("base_gold_per_beat", 35))
        + mil_count * int(up.get("gold_per_military", 3))
        + towers * int(up.get("gold_per_tower", 12))
        + city * int(up.get("gold_per_city_level", 20))
    )
    food = mil_count * int(up.get("food_per_military", 1))
    return {"gold": gold, "food": food}


def kingdom_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    charter = get_kingdom_charter(state)
    kcfg = load_kingdom_config(base_dir)
    ps = get_player_settlement(state)
    preview = founding_cost_preview(state, base_dir=base_dir)
    payload: dict[str, Any] = {
        "is_kingdom": bool(ps.get("is_kingdom")),
        "founding_preview": preview,
        "party_gold": _party_gold(state),
        "stockpile": dict(ps.get("stockpile", {})),
    }
    if charter is None:
        payload["charter"] = None
        payload["defense_summary"] = None
        payload["upkeep"] = None
        return payload

    _recalc_barrier_max(charter, kcfg)
    upkeep = compute_upkeep(charter, kcfg)
    fort = charter.get("fortifications", {})
    mil = charter.get("military", {})
    interior = charter.get("interior", {})
    defense = compute_defense_rating(charter, kcfg)
    payload.update(
        {
            "charter": charter,
            "upkeep": upkeep,
            "defense_summary": defense,
            "military_cap": _military_cap(charter, kcfg),
            "military_total": _military_total(charter),
            "fortifications": fort,
            "interior": interior,
            "laws": charter.get("laws", {}),
            "barrier_pct": int(
                100 * int(charter["barrier"]["hp"]) / max(1, int(charter["barrier"]["max_hp"]))
            ),
            "physically_destroyable": not bool(
                kcfg.get("siege", {}).get("barrier_must_break_before_physical_destroy", True)
            )
            or int(charter["barrier"]["hp"]) <= 0,
        }
    )
    return payload


def compute_defense_rating(charter: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    fort = charter.get("fortifications", {})
    mil = charter.get("military", {})
    barrier = charter.get("barrier", {})
    walls_lvl = int(fort.get("walls_level", 0))
    wall_def = int(fort.get("wall_defense", 0))
    tower_atk = int(fort.get("tower_attack", 0))
    tower_count = int(fort.get("tower_count", 0))
    scouts = int(mil.get("scout", 0))
    guards = int(mil.get("guard", 0))
    archers = int(mil.get("wall_archer", 0))
    elites = int(mil.get("elite", 0))
    siege = cfg.get("siege", {})
    arch_mult = float(siege.get("wall_archer_damage_mult_on_walls", 1.8))
    wall_attack = int(archers * 22 * arch_mult) if walls_lvl > 0 else 0
    garrison = guards * 18 + elites * 28
    return {
        "barrier_hp": int(barrier.get("hp", 0)),
        "barrier_max_hp": int(barrier.get("max_hp", 0)),
        "wall_defense": wall_def,
        "tower_attack": tower_atk,
        "tower_count": tower_count,
        "wall_archer_volley": wall_attack,
        "garrison_power": garrison,
        "scout_coverage": scouts * 8,
        "total_rating": wall_def + tower_atk + garrison + wall_attack + scouts * 5,
        "physical_destroy_blocked": bool(barrier.get("physical_destroy_blocked", True))
        and int(barrier.get("hp", 0)) > 0,
    }


def set_kingdom_laws(
    state: dict[str, Any],
    laws: dict[str, Any],
    *,
    base_dir: str | Path,
) -> dict[str, Any]:
    charter = get_kingdom_charter(state)
    if not charter:
        return {"ok": False, "error": "왕국이 없습니다"}
    allowed = set(load_kingdom_config(base_dir).get("default_laws", {}).keys())
    current = charter.setdefault("laws", {})
    for key, val in laws.items():
        if key in allowed:
            current[key] = val
    charter["stability"] = min(100, int(charter.get("stability", 75)) + 2)
    return {"ok": True, "laws": current}


def upgrade_fortification(
    state: dict[str, Any],
    upgrade_type: str,
    *,
    base_dir: str | Path,
) -> dict[str, Any]:
    """upgrade_type: walls | tower | barrier_ritual"""
    charter = get_kingdom_charter(state)
    if not charter:
        return {"ok": False, "error": "왕국이 없습니다"}
    kcfg = load_kingdom_config(base_dir)
    ps = get_player_settlement(state)
    fort_cfg = kcfg.get("fortifications", {})
    fort = charter.setdefault("fortifications", {})

    if upgrade_type == "walls":
        wcfg = fort_cfg.get("walls", {})
        cur = int(fort.get("walls_level", 0))
        nxt = cur + 1
        if nxt > int(wcfg.get("max_level", 5)):
            return {"ok": False, "error": "성벽 최대 레벨"}
        row = next((r for r in wcfg.get("levels", []) if int(r["level"]) == nxt), None)
        if not row:
            return {"ok": False, "error": "성벽 레벨 정의 없음"}
        cost = int(row.get("gold", 0))
        mats = dict(row.get("materials", {}))
        if _party_gold(state) < cost:
            return {"ok": False, "error": "골드 부족"}
        if not _materials_available(ps, mats):
            return {"ok": False, "error": "자재 부족"}
        _set_party_gold(state, _party_gold(state) - cost)
        _deduct_materials(ps, mats)
        fort["walls_level"] = nxt
        fort["wall_defense"] = int(row.get("wall_defense", 0))
        _recalc_barrier_max(charter, kcfg)
        return {"ok": True, "walls_level": nxt, "gold_spent": cost}

    if upgrade_type == "tower":
        tcfg = fort_cfg.get("tower", {})
        cur = int(fort.get("tower_count", 0))
        if cur >= int(tcfg.get("max_count", 8)):
            return {"ok": False, "error": "포탑 최대 수량"}
        cost = int(tcfg.get("gold_each", 0))
        mats = dict(tcfg.get("materials_each", {}))
        if _party_gold(state) < cost:
            return {"ok": False, "error": "골드 부족"}
        if not _materials_available(ps, mats):
            return {"ok": False, "error": "자재 부족"}
        _set_party_gold(state, _party_gold(state) - cost)
        _deduct_materials(ps, mats)
        fort["tower_count"] = cur + 1
        fort["tower_attack"] = fort["tower_count"] * int(tcfg.get("attack_per_tower", 25))
        return {"ok": True, "tower_count": fort["tower_count"], "gold_spent": cost}

    if upgrade_type == "barrier_ritual":
        bcfg = fort_cfg.get("barrier_ritual", {})
        cur = int(charter.get("barrier", {}).get("ritual_level", 0))
        nxt = cur + 1
        if nxt > int(bcfg.get("max_level", 5)):
            return {"ok": False, "error": "결계 의식 최대 레벨"}
        row = next((r for r in bcfg.get("levels", []) if int(r["level"]) == nxt), None)
        if not row:
            return {"ok": False, "error": "결계 레벨 정의 없음"}
        cost = int(row.get("gold", 0))
        mats = dict(row.get("materials", {}))
        if _party_gold(state) < cost:
            return {"ok": False, "error": "골드 부족"}
        if not _materials_available(ps, mats):
            return {"ok": False, "error": "자재 부족"}
        _set_party_gold(state, _party_gold(state) - cost)
        _deduct_materials(ps, mats)
        charter["barrier"]["ritual_level"] = nxt
        _recalc_barrier_max(charter, kcfg)
        charter["barrier"]["hp"] = charter["barrier"]["max_hp"]
        return {"ok": True, "ritual_level": nxt, "gold_spent": cost}

    return {"ok": False, "error": f"unknown upgrade: {upgrade_type}"}


def build_interior(
    state: dict[str, Any],
    build_type: str,
    *,
    base_dir: str | Path,
) -> dict[str, Any]:
    """build_type: farmland | city_district | training_ground"""
    charter = get_kingdom_charter(state)
    if not charter:
        return {"ok": False, "error": "왕국이 없습니다"}
    kcfg = load_kingdom_config(base_dir)
    ps = get_player_settlement(state)
    interior = charter.setdefault("interior", {})
    icfg = kcfg.get("interior", {})

    if build_type == "farmland":
        fcfg = icfg.get("farmland", {})
        cur = int(interior.get("farmland_plots", 0))
        if cur >= int(fcfg.get("max_plots", 12)):
            return {"ok": False, "error": "농경지 최대"}
        cost = int(fcfg.get("gold_each", 0))
        mats = dict(fcfg.get("materials_each", {}))
        if _party_gold(state) < cost:
            return {"ok": False, "error": "골드 부족"}
        if not _materials_available(ps, mats):
            return {"ok": False, "error": "자재 부족"}
        _set_party_gold(state, _party_gold(state) - cost)
        _deduct_materials(ps, mats)
        interior["farmland_plots"] = cur + 1
        return {"ok": True, "farmland_plots": interior["farmland_plots"], "gold_spent": cost}

    if build_type == "city_district":
        ccfg = icfg.get("city_district", {})
        cur = int(interior.get("city_level", 0))
        nxt = cur + 1
        row = next((r for r in ccfg.get("levels", []) if int(r["level"]) == nxt), None)
        if not row:
            return {"ok": False, "error": "도시 최대 레벨"}
        cost = int(row.get("gold", 0))
        mats = dict(row.get("materials", {}))
        if _party_gold(state) < cost:
            return {"ok": False, "error": "골드 부족"}
        if not _materials_available(ps, mats):
            return {"ok": False, "error": "자재 부족"}
        _set_party_gold(state, _party_gold(state) - cost)
        _deduct_materials(ps, mats)
        interior["city_level"] = nxt
        interior["population_cap"] = int(row.get("population_cap", 0))
        tax = float(row.get("tax_bonus", 0))
        laws = charter.setdefault("laws", {})
        laws["tax_rate"] = min(0.25, float(laws.get("tax_rate", 0.08)) + tax)
        return {"ok": True, "city_level": nxt, "gold_spent": cost}

    if build_type == "training_ground":
        tcfg = icfg.get("training_ground", {})
        cur = int(interior.get("training_ground_level", 0))
        nxt = cur + 1
        row = next((r for r in tcfg.get("levels", []) if int(r["level"]) == nxt), None)
        if not row:
            return {"ok": False, "error": "훈련소 최대 레벨"}
        cost = int(row.get("gold", 0))
        mats = dict(row.get("materials", {}))
        if _party_gold(state) < cost:
            return {"ok": False, "error": "골드 부족"}
        if not _materials_available(ps, mats):
            return {"ok": False, "error": "자재 부족"}
        _set_party_gold(state, _party_gold(state) - cost)
        _deduct_materials(ps, mats)
        interior["training_ground_level"] = nxt
        return {"ok": True, "training_ground_level": nxt, "gold_spent": cost}

    return {"ok": False, "error": f"unknown interior: {build_type}"}


def recruit_military(
    state: dict[str, Any],
    unit_type: str,
    count: int = 1,
    *,
    base_dir: str | Path,
) -> dict[str, Any]:
    charter = get_kingdom_charter(state)
    if not charter:
        return {"ok": False, "error": "왕국이 없습니다"}
    kcfg = load_kingdom_config(base_dir)
    units = kcfg.get("military", {}).get("units", {})
    udef = units.get(unit_type)
    if not udef:
        return {"ok": False, "error": f"unknown unit: {unit_type}"}
    count = max(1, int(count))
    interior = charter.get("interior", {})
    fort = charter.get("fortifications", {})
    if unit_type == "wall_archer" and int(fort.get("walls_level", 0)) < int(
        udef.get("requires_walls_level", 1)
    ):
        return {"ok": False, "error": "성벽 Lv1 이상 필요 (성벽 궁수)"}
    if unit_type == "elite" and int(interior.get("training_ground_level", 0)) < int(
        udef.get("requires_training_ground", 2)
    ):
        return {"ok": False, "error": "훈련소 Lv2 이상 필요 (정예)"}
    cap = _military_cap(charter, kcfg)
    total = _military_total(charter) + len(charter.get("military", {}).get("in_training", []))
    if total + count > cap:
        return {"ok": False, "error": f"병력 상한 {cap}명"}
    gold_each = int(udef.get("gold", 0))
    food_each = int(udef.get("food", 0))
    cost = gold_each * count
    food_need = food_each * count
    if _party_gold(state) < cost:
        return {"ok": False, "error": "골드 부족"}
    interior_store = charter.setdefault("interior", {})
    if int(interior_store.get("food_store", 0)) < food_need:
        return {"ok": False, "error": "군량 부족"}
    _set_party_gold(state, _party_gold(state) - cost)
    interior_store["food_store"] = int(interior_store.get("food_store", 0)) - food_need
    mil = charter.setdefault("military", {})
    queue = mil.setdefault("in_training", [])
    beats = int(udef.get("train_beats", 5))
    for _ in range(count):
        queue.append({"unit": unit_type, "beats_left": beats})
    return {
        "ok": True,
        "queued": count,
        "unit": unit_type,
        "train_beats": beats,
        "gold_spent": cost,
    }


def apply_siege_damage(
    state: dict[str, Any],
    damage: int,
    *,
    base_dir: str | Path,
    siege_type: str = "magical",
) -> dict[str, Any]:
    """External siege — barrier absorbs first; physical destroy blocked until hp=0."""
    charter = get_kingdom_charter(state)
    if not charter:
        return {"ok": False, "error": "왕국 없음"}
    kcfg = load_kingdom_config(base_dir)
    barrier = charter.setdefault("barrier", {})
    reduction = float(kcfg.get("barrier", {}).get("siege_damage_reduction", 0.65))
    effective = int(math.ceil(damage * (1.0 - reduction)))
    hp = int(barrier.get("hp", 0))
    hp = max(0, hp - effective)
    barrier["hp"] = hp
    result: dict[str, Any] = {
        "ok": True,
        "damage_in": damage,
        "damage_to_barrier": effective,
        "barrier_hp": hp,
        "barrier_broken": hp <= 0,
    }
    siege_cfg = kcfg.get("siege", {})
    if hp <= 0 and siege_type == "physical" and siege_cfg.get(
        "barrier_must_break_before_physical_destroy", True
    ):
        charter["physically_destroyed"] = True
        result["physically_destroyed"] = True
        result["message"] = "결계 붕괴 — 왕국 영토가 물리적으로 위협받는다"
    elif hp > 0:
        result["physical_destroy_blocked"] = True
        result["message"] = "결계가 공격을 막았다 — 물리적 멸망 불가"
    return result


def tick_kingdom(state: dict[str, Any], *, base_dir: str | Path) -> list[str]:
    """Upkeep, food production, training queue, barrier regen."""
    from utils.field_agents import ecology_enabled

    if not ecology_enabled(state):
        return []

    charter = get_kingdom_charter(state)
    if not charter or charter.get("physically_destroyed"):
        return []

    kcfg = load_kingdom_config(base_dir)
    lines: list[str] = []
    upkeep = compute_upkeep(charter, kcfg)
    gold = _party_gold(state)
    interior = charter.setdefault("interior", {})
    food_store = int(interior.get("food_store", 0))

    # Farmland production
    plots = int(interior.get("farmland_plots", 0))
    fpb = int(kcfg.get("interior", {}).get("farmland", {}).get("food_per_beat_each", 6))
    if plots > 0:
        produced = plots * fpb
        interior["food_store"] = food_store + produced
        food_store = interior["food_store"]
        lines.append(f"[왕국·농경] 식량 +{produced} (보유 {food_store})")

    food_need = upkeep["food"]
    gold_need = upkeep["gold"]
    unpaid = int(charter.get("unpaid_beats", 0))

    if gold >= gold_need and food_store >= food_need:
        _set_party_gold(state, gold - gold_need)
        interior["food_store"] = food_store - food_need
        charter["unpaid_beats"] = 0
        if gold_need > 0 or food_need > 0:
            lines.append(f"[왕국·유지] -{gold_need}G, -{food_need} 식량")
    else:
        charter["unpaid_beats"] = unpaid + 1
        penalty = int(kcfg.get("upkeep", {}).get("stability_penalty_if_unpaid", 8))
        charter["stability"] = max(0, int(charter.get("stability", 75)) - penalty)
        lines.append(f"[왕국·유지] 자원 부족 — 안정도 -{penalty}")

    # Training queue
    mil = charter.setdefault("military", {})
    queue: list[dict[str, Any]] = mil.get("in_training", [])
    done_units: list[str] = []
    new_queue: list[dict[str, Any]] = []
    for entry in queue:
        entry["beats_left"] = int(entry.get("beats_left", 1)) - 1
        if entry["beats_left"] <= 0:
            ut = str(entry.get("unit", "guard"))
            mil[ut] = int(mil.get(ut, 0)) + 1
            done_units.append(ut)
        else:
            new_queue.append(entry)
    mil["in_training"] = new_queue
    if done_units:
        labels = kcfg.get("military", {}).get("units", {})
        names = [labels.get(u, {}).get("label", u) for u in done_units]
        lines.append(f"[왕국·훈련] 병력 편성: {', '.join(names)}")

    # Barrier regen
    barrier = charter.setdefault("barrier", {})
    if int(charter.get("unpaid_beats", 0)) < int(
        kcfg.get("upkeep", {}).get("barrier_offline_if_unpaid_beats", 3)
    ):
        regen = int(barrier.get("regen_per_beat", 80))
        max_hp = int(barrier.get("max_hp", regen))
        barrier["hp"] = min(max_hp, int(barrier.get("hp", 0)) + regen)

    return lines
