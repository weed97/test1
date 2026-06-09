"""Player settlement — construction level, buildings, hire labor, kingdom."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Literal

from utils.config_loader import load_config
from utils.ecology_state import ecology_flags

BuildMode = Literal["self", "hire"]


def load_buildings_config(base_dir: str | Path) -> dict[str, Any]:
    return load_config(base_dir, "settlement_buildings.json")


def get_player_settlement(state: dict[str, Any]) -> dict[str, Any]:
    eco = ecology_flags(state)
    ps = eco.setdefault(
        "player_settlement",
        {
            "construction_level": 1,
            "construction_xp": 0,
            "self_labor": 2,
            "hired_workers": 0,
            "stockpile": {"wood": 20, "stone": 10, "iron": 5},
            "sites": [],
            "completed_buildings": [],
            "is_kingdom": False,
        },
    )
    return ps


def _party_gold(state: dict[str, Any], *, base_dir: str | Path) -> int:
    from utils.currency import party_gold

    return party_gold(state, base_dir=base_dir)


def _set_party_gold(state: dict[str, Any], amount: int, *, base_dir: str | Path) -> None:
    from utils.currency import set_party_gold

    set_party_gold(state, amount, base_dir=base_dir)


def _spend_build_cost(
    state: dict[str, Any], cost_spec: int | dict[str, Any], *, base_dir: str | Path
) -> bool:
    from utils.currency import normalize_cost, spend

    return spend(state, normalize_cost(cost_spec, base_dir=base_dir), base_dir=base_dir)


def _can_afford_build_cost(
    state: dict[str, Any], cost_spec: int | dict[str, Any], *, base_dir: str | Path
) -> bool:
    from utils.currency import can_afford, normalize_cost

    return can_afford(state, normalize_cost(cost_spec, base_dir=base_dir), base_dir=base_dir)


def construction_level_info(cfg: dict[str, Any], level: int) -> dict[str, Any]:
    for row in cfg.get("construction_levels", []):
        if int(row["level"]) == level:
            return row
    return cfg.get("construction_levels", [{}])[0]


def unlocked_building_ids(state: dict[str, Any], base_dir: str | Path) -> list[str]:
    cfg = load_buildings_config(base_dir)
    ps = get_player_settlement(state)
    lvl = int(ps.get("construction_level", 1))
    out: list[str] = []
    for bid, bdef in cfg.get("buildings", {}).items():
        if int(bdef.get("min_construction_level", 99)) <= lvl:
            out.append(bid)
    return sorted(out)


def list_buildable(
    state: dict[str, Any], *, base_dir: str | Path
) -> list[dict[str, Any]]:
    """Buildings player can start now (level + not kingdom-locked)."""
    cfg = load_buildings_config(base_dir)
    ps = get_player_settlement(state)
    lvl = int(ps.get("construction_level", 1))
    result: list[dict[str, Any]] = []
    for bid in unlocked_building_ids(state, base_dir):
        bdef = cfg["buildings"][bid]
        afford_gold = _can_afford_build_cost(
            state, int(bdef.get("gold_cost", 0)), base_dir=base_dir
        )
        mats_ok = _materials_available(ps, bdef.get("materials", {}))
        result.append(
            {
                "id": bid,
                "label": bdef.get("label", bid),
                "min_construction_level": bdef.get("min_construction_level"),
                "gold_cost": bdef.get("gold_cost"),
                "labor_cost": bdef.get("labor_cost"),
                "materials": bdef.get("materials"),
                "roles": bdef.get("roles", []),
                "can_afford_gold": afford_gold,
                "can_afford_materials": mats_ok,
                "build_points": bdef.get("build_points"),
            }
        )
    return result


def _materials_available(ps: dict[str, Any], need: dict[str, Any]) -> bool:
    stock = ps.get("stockpile", {})
    for k, v in need.items():
        if int(stock.get(k, 0)) < int(v):
            return False
    return True


def _deduct_materials(ps: dict[str, Any], need: dict[str, Any]) -> None:
    stock = ps.setdefault("stockpile", {})
    for k, v in need.items():
        stock[k] = int(stock.get(k, 0)) - int(v)


def _find_site(ps: dict[str, Any], map_id: str, x: int, y: int) -> dict[str, Any] | None:
    for site in ps.get("sites", []):
        if site.get("map_id") == map_id and int(site.get("x")) == x and int(site.get("y")) == y:
            return site
    return None


def _get_or_create_site(
    state: dict[str, Any], *, map_id: str, x: int, y: int
) -> dict[str, Any]:
    ps = get_player_settlement(state)
    site = _find_site(ps, map_id, x, y)
    if site:
        return site
    site = {
        "site_id": f"site_{uuid.uuid4().hex[:8]}",
        "map_id": map_id,
        "x": int(x),
        "y": int(y),
        "name": "플레이어 거점",
        "buildings": [],
        "active_project": None,
    }
    ps.setdefault("sites", []).append(site)
    return site


def hire_workers(
    state: dict[str, Any], count: int, *, base_dir: str | Path
) -> dict[str, Any]:
    cfg = load_buildings_config(base_dir)
    hire = cfg.get("hire", {})
    ps = get_player_settlement(state)
    lvl = int(ps.get("construction_level", 1))
    if lvl < int(hire.get("unlock_construction_level", 2)):
        return {"ok": False, "error": "건축 레벨 2 이상 필요 (NPC 고용)"}
    count = max(1, int(count))
    max_h = int(hire.get("max_hired", 12))
    current = int(ps.get("hired_workers", 0))
    if current + count > max_h:
        return {"ok": False, "error": f"고용 한도 {max_h}명"}
    cost = int(hire.get("gold_per_worker", 120)) * count
    if not _can_afford_build_cost(state, cost, base_dir=base_dir):
        from utils.currency import format_wallet, get_wallet

        return {
            "ok": False,
            "error": f"화폐 부족 (필요 {cost}쿠퍼 상당, 보유 {format_wallet(get_wallet(state, base_dir=base_dir), base_dir=base_dir)})",
        }
    _spend_build_cost(state, cost, base_dir=base_dir)
    ps["hired_workers"] = current + count
    return {
        "ok": True,
        "hired_workers": ps["hired_workers"],
        "gold_spent": cost,
        "wage_per_beat": hire.get("wage_gold_per_beat"),
        "labor_per_worker": hire.get("labor_per_worker_per_beat"),
    }


def start_build(
    state: dict[str, Any],
    building_id: str,
    *,
    map_id: str,
    x: int,
    y: int,
    mode: BuildMode = "self",
    base_dir: str | Path,
) -> dict[str, Any]:
    cfg = load_buildings_config(base_dir)
    bdef = cfg.get("buildings", {}).get(building_id)
    if not bdef:
        return {"ok": False, "error": f"unknown building: {building_id}"}

    ps = get_player_settlement(state)
    lvl = int(ps.get("construction_level", 1))
    if int(bdef.get("min_construction_level", 1)) > lvl:
        return {
            "ok": False,
            "error": f"건축 레벨 {bdef['min_construction_level']} 필요 (현재 {lvl})",
        }

    level_info = construction_level_info(cfg, lvl)
    active_count = sum(1 for s in ps.get("sites", []) if s.get("active_project"))
    if active_count >= int(level_info.get("max_active_projects", 1)):
        return {"ok": False, "error": "동시 건설 한도 초과"}

    if mode == "hire":
        hire_cfg = cfg.get("hire", {})
        if lvl < int(hire_cfg.get("unlock_construction_level", 2)):
            return {"ok": False, "error": "고용 건설은 건축 레벨 2+"}
        if int(ps.get("hired_workers", 0)) < 1:
            return {"ok": False, "error": "고용 인력 없음 — hire_workers 먼저"}

    gold_cost = int(bdef.get("gold_cost", 0))
    if not _can_afford_build_cost(state, gold_cost, base_dir=base_dir):
        return {"ok": False, "error": "화폐 부족 (쿠퍼/실버)"}
    if not _materials_available(ps, bdef.get("materials", {})):
        return {"ok": False, "error": "자재 부족", "need": bdef.get("materials")}

    site = _get_or_create_site(state, map_id=map_id, x=x, y=y)
    if site.get("active_project"):
        return {"ok": False, "error": "이 타일에 이미 건설 중"}

    _spend_build_cost(state, gold_cost, base_dir=base_dir)
    _deduct_materials(ps, bdef.get("materials", {}))

    site["active_project"] = {
        "building_id": building_id,
        "label": bdef.get("label", building_id),
        "progress": 0,
        "required": int(bdef.get("build_points", 50)),
        "mode": mode,
        "labor_cost_total": int(bdef.get("labor_cost", 0)),
        "labor_applied": 0,
    }
    return {
        "ok": True,
        "site_id": site["site_id"],
        "project": site["active_project"],
        "gold_spent": gold_cost,
        "materials_spent": bdef.get("materials"),
    }


def _add_construction_xp(state: dict[str, Any], xp: int, base_dir: str | Path) -> None:
    cfg = load_buildings_config(base_dir)
    ps = get_player_settlement(state)
    ps["construction_xp"] = int(ps.get("construction_xp", 0)) + xp
    lvl = int(ps.get("construction_level", 1))
    for row in sorted(cfg.get("construction_levels", []), key=lambda r: -int(r["level"])):
        if ps["construction_xp"] >= int(row.get("xp_required", 0)):
            new_lvl = int(row["level"])
            if new_lvl > lvl:
                ps["construction_level"] = new_lvl
                level_info = construction_level_info(cfg, new_lvl)
                ps["self_labor"] = int(level_info.get("self_labor_per_beat", ps.get("self_labor", 2)))
            break


def tick_player_build_projects(
    state: dict[str, Any], *, base_dir: str | Path
) -> list[str]:
    """Apply labor each ecology beat; pay wages; complete buildings."""
    from utils.field_agents import ecology_enabled

    if not ecology_enabled(state):
        return []

    cfg = load_buildings_config(base_dir)
    ps = get_player_settlement(state)
    lvl = int(ps.get("construction_level", 1))
    level_info = construction_level_info(cfg, lvl)
    lines: list[str] = []

    hire_cfg = cfg.get("hire", {})
    wages = int(ps.get("hired_workers", 0)) * int(hire_cfg.get("wage_gold_per_beat", 8))
    if wages > 0:
        if not _can_afford_build_cost(state, wages, base_dir=base_dir):
            lines.append("[건설] 임금 지불 실패 — 일꾼들이 작업을 멈췄다.")
        else:
            _spend_build_cost(state, wages, base_dir=base_dir)
            lines.append(f"[건설] 임금 -{wages}쿠퍼 ({ps['hired_workers']}명)")

    labor_self = int(level_info.get("self_labor_per_beat", 2))
    labor_hire = int(ps.get("hired_workers", 0)) * int(
        hire_cfg.get("labor_per_worker_per_beat", 4)
    )

    for site in ps.get("sites", []):
        proj = site.get("active_project")
        if not proj:
            continue
        mode = proj.get("mode", "self")
        labor = labor_hire if mode == "hire" else labor_self
        if mode == "hire" and int(ps.get("hired_workers", 0)) < 1:
            labor = 0
        proj["progress"] = int(proj.get("progress", 0)) + labor
        proj["labor_applied"] = int(proj.get("labor_applied", 0)) + labor
        bid = proj.get("building_id")
        bdef = cfg.get("buildings", {}).get(bid, {})
        if int(proj["progress"]) >= int(proj.get("required", 1)):
            if proj.get("is_kingdom_project"):
                from utils.kingdom_system import complete_kingdom_founding

                site["name"] = str(proj.get("kingdom_name", "플레이어 왕국"))
                site["active_project"] = None
                founded = complete_kingdom_founding(
                    state,
                    map_id=str(site.get("map_id", "")),
                    x=int(site.get("x", 0)),
                    y=int(site.get("y", 0)),
                    name=site["name"],
                    doctrine_id=str(proj.get("doctrine_id", "")),
                    custom_decree=str(proj.get("custom_decree", "")),
                    base_dir=base_dir,
                )
                lines.append(founded.get("message", "[왕국] 선포 완료"))
                continue
            completed = {
                "building_id": bid,
                "label": proj.get("label", bid),
                "map_id": site.get("map_id"),
                "x": site.get("x"),
                "y": site.get("y"),
                "roles": bdef.get("roles", []),
                "effects": bdef.get("effects", {}),
            }
            site.setdefault("buildings", []).append(completed)
            ps.setdefault("completed_buildings", []).append(completed)
            site["active_project"] = None
            xp = max(10, int(bdef.get("build_points", 20)) // 2)
            _add_construction_xp(state, xp, base_dir)
            lines.append(
                f"[건설 완료] {completed['label']} @ {site.get('name')} "
                f"({site['map_id']} {site['x']},{site['y']}) — 건축 XP +{xp}"
            )
        else:
            pct = int(100 * proj["progress"] / max(1, int(proj["required"])))
            lines.append(
                f"[건설] {proj.get('label')} {pct}% (+{labor} 노동, {mode})"
            )
    return lines


def settlement_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    from utils.currency import wallet_summary
    from utils.regional_resources import regional_status

    ps = get_player_settlement(state)
    cfg = load_buildings_config(base_dir)
    lvl = int(ps.get("construction_level", 1))
    next_lvl = construction_level_info(cfg, min(lvl + 1, 5))
    money = wallet_summary(state, base_dir=base_dir)
    return {
        "construction_level": lvl,
        "construction_title": construction_level_info(cfg, lvl).get("title"),
        "construction_xp": int(ps.get("construction_xp", 0)),
        "next_level_xp": int(next_lvl.get("xp_required", 0)) if lvl < 5 else None,
        "wallet": money["wallet"],
        "wallet_formatted": money["formatted"],
        "party_gold": money["party_gold"],
        "regional_resources": regional_status(state, base_dir=base_dir),
        "hired_workers": int(ps.get("hired_workers", 0)),
        "self_labor_per_beat": construction_level_info(cfg, lvl).get("self_labor_per_beat"),
        "stockpile": dict(ps.get("stockpile", {})),
        "sites": ps.get("sites", []),
        "completed_buildings": ps.get("completed_buildings", []),
        "buildable": list_buildable(state, base_dir=base_dir),
        "is_kingdom": bool(ps.get("is_kingdom")),
    }


def try_start_kingdom(
    state: dict[str, Any],
    *,
    map_id: str,
    x: int,
    y: int,
    base_dir: str | Path,
    kingdom_name: str = "플레이어 왕국",
    doctrine_id: str = "",
    custom_decree: str = "",
) -> dict[str, Any]:
    from utils.kingdom_system import (
        can_found_kingdom,
        deduct_founding_costs,
        founding_cost_preview,
        load_kingdom_config,
    )

    ok, err = can_found_kingdom(state, base_dir=base_dir)
    if not ok:
        return {"ok": False, "error": err, "preview": founding_cost_preview(state, base_dir=base_dir)}
    ps = get_player_settlement(state)
    site = _get_or_create_site(state, map_id=map_id, x=x, y=y)
    if site.get("active_project"):
        return {"ok": False, "error": "이 타일에 이미 건설 중"}
    paid = deduct_founding_costs(state, base_dir=base_dir)
    if not paid.get("ok"):
        return paid
    fdef = load_kingdom_config(base_dir).get("founding", {})
    site["active_project"] = {
        "building_id": "kingdom",
        "label": fdef.get("label", "왕국 선포 의식"),
        "progress": 0,
        "required": int(fdef.get("build_points", 2500)),
        "mode": str(fdef.get("mode", "hire")),
        "is_kingdom_project": True,
        "kingdom_name": kingdom_name,
        "doctrine_id": doctrine_id,
        "custom_decree": custom_decree,
    }
    return {
        "ok": True,
        "site_id": site["site_id"],
        "project": site["active_project"],
        "costs": paid,
        "preview": founding_cost_preview(state, base_dir=base_dir),
    }
