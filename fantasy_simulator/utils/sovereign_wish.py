"""Sovereign wish (4-year edict) — resolve world-scale effects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(base_dir: str | Path, rel: str) -> dict[str, Any]:
    with (Path(base_dir) / rel).open(encoding="utf-8") as f:
        return json.load(f)


def load_demigod_config(base_dir: str | Path) -> dict[str, Any]:
    return _read_json(base_dir, "config/demigod_sovereign.json")


def _sovereign_flags(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("flags", {}).setdefault("sovereign", {})


def world_day(state: dict[str, Any]) -> int:
    return int(state.get("world", {}).get("day", 1))


def wish_cooldown_days(cfg: dict[str, Any]) -> int:
    years = int(cfg.get("excalibur", {}).get("wish_interval_years", 4))
    days_per_year = int(cfg.get("days_per_year", 360))
    return years * days_per_year


def can_cast_sovereign_wish(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
) -> tuple[bool, str]:
    cfg = load_demigod_config(base_dir)
    sov = state.get("flags", {}).get("world_sovereign", {})
    holder = str(sov.get("holder_id", cfg.get("initial_holder", {}).get("id", "")))
    if not holder:
        return False, "주권 홀더 없음"
    last = int(_sovereign_flags(state).get("last_sovereign_wish_world_day", -10**9))
    gap = wish_cooldown_days(cfg)
    now = world_day(state)
    if now - last < gap:
        remain = gap - (now - last)
        return False, f"소원 재충전 중 ({remain}일 남음)"
    return True, ""


def wish_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    cfg = load_demigod_config(base_dir)
    gap = wish_cooldown_days(cfg)
    last = int(_sovereign_flags(state).get("last_sovereign_wish_world_day", -gap))
    now = world_day(state)
    ok, reason = can_cast_sovereign_wish(state, base_dir=base_dir)
    return {
        "can_cast": ok,
        "reason": reason,
        "last_sovereign_wish_world_day": last if last > -10**8 else None,
        "world_day": now,
        "cooldown_days": gap,
        "days_until_ready": 0 if ok else max(0, gap - (now - last)),
        "forbidden_edicts": list(cfg.get("forbidden_edicts", [])),
        "wish_edict_types": list(cfg.get("wish_edict_types", [])),
        "last_edict_type": _sovereign_flags(state).get("last_edict_type"),
    }


def _apply_edict(
    state: dict[str, Any],
    edict_type: str,
    payload: dict[str, Any],
    *,
    base_dir: str | Path,
    cfg: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    eco = state.setdefault("flags", {}).setdefault("ecology", {})

    if edict_type == "empower_self":
        boost = int(payload.get("power_bonus", 5))
        holder_id = str(
            state.get("flags", {}).get("world_sovereign", {}).get("holder_id", "npc_arthur_pendragon")
        )
        for a in eco.get("agents", []):
            if a.get("archetype_id") == holder_id or a.get("instance_id") == holder_id:
                pl = a.setdefault("plunder", {})
                pl["power_bonus"] = int(pl.get("power_bonus", 0)) + boost
                lines.append(f"[소원] {a.get('label', holder_id)} 힘이 강해진다. (+{boost})")
                break
        else:
            sov = state.setdefault("flags", {}).setdefault("world_sovereign", {})
            sov["wish_power_bonus"] = int(sov.get("wish_power_bonus", 0)) + boost
            lines.append(f"[소원] 주권자 힘이 강해진다. (+{boost})")

    elif edict_type == "empower_kingdom":
        from utils.agent_competition import get_civilization_state

        civ_id = str(payload.get("civilization_id", "ashpoint_commons"))
        gain = int(payload.get("prosperity_gain", 15))
        cs = get_civilization_state(state, civ_id)
        cs["prosperity"] = int(cs.get("prosperity", 0)) + gain
        lines.append(f"[소원] {civ_id} 번영 +{gain}")

    elif edict_type == "weaken_realm":
        from utils.agent_competition import get_civilization_state

        civ_id = str(payload.get("civilization_id", "goblin_tribe"))
        pen = min(
            int(cfg.get("capped_edicts", {}).get("weaken_realm", {}).get("max_tier_penalty", 2) * 8),
            int(payload.get("prosperity_penalty", 12)),
        )
        cs = get_civilization_state(state, civ_id)
        cs["prosperity"] = max(5, int(cs.get("prosperity", 0)) - pen)
        lines.append(f"[소원] {civ_id} 약화 (−번영 {pen})")

    elif edict_type == "empower_monsters":
        mult = float(payload.get("spawn_pressure", 1.15))
        wr = state.setdefault("flags", {}).setdefault("world_rules", {})
        wr["monster_spawn_pressure"] = float(wr.get("monster_spawn_pressure", 1.0)) * mult
        lines.append(f"[소원] 괴수 세력이 고조된다.")

    elif edict_type == "found_civilization":
        civ_id = str(payload.get("civilization_id", "wishborn_commons"))
        civs = eco.setdefault("civilizations", {})
        if civ_id not in civs:
            civs[civ_id] = {
                "prosperity": int(payload.get("prosperity", 20)),
                "wins": 0,
                "label": payload.get("label", civ_id),
            }
            lines.append(f"[소원] 새 문명 {civ_id} 성립")
        else:
            civs[civ_id]["prosperity"] = int(civs[civ_id].get("prosperity", 0)) + 10
            lines.append(f"[소원] {civ_id} 번영 확장")

    elif edict_type == "reshape_rule":
        key = str(payload.get("rule_key", "sovereign_edict"))
        value = payload.get("rule_value", True)
        expires = int(cfg.get("capped_edicts", {}).get("reshape_rule", {}).get("expires_after_years", 8))
        days_per_year = int(cfg.get("days_per_year", 360))
        wr = state.setdefault("flags", {}).setdefault("world_rules", {})
        wr[key] = value
        wr[f"{key}_expires_day"] = world_day(state) + expires * days_per_year
        lines.append(f"[소원] 세계 규칙 '{key}' 재형성")

    else:
        lines.append(f"[소원] 알 수 없는 칙령 유형: {edict_type}")

    return lines


def _apply_backlash(state: dict[str, Any], *, base_dir: str | Path) -> list[str]:
    lines: list[str] = []
    tension = state.setdefault("flags", {}).setdefault("world_tension", {})
    tension["value"] = min(100, int(tension.get("value", 0)) + 3)
    lines.append("[소원·반작용] 세계 긴장이 소폭 상승한다.")
    from utils.world_conflicts import init_world_conflicts

    init_world_conflicts(state, base_dir=base_dir)
    conflicts = state.get("flags", {}).get("ecology", {}).get("world_conflicts", {})
    if conflicts is not None:
        conflicts["wish_backlash"] = int(conflicts.get("wish_backlash", 0)) + 1
    return lines


def resolve_sovereign_wish(
    state: dict[str, Any],
    payload: dict[str, Any],
    *,
    base_dir: str | Path,
) -> dict[str, Any]:
    """Apply one sovereign edict if cooldown and forbidden checks pass."""
    cfg = load_demigod_config(base_dir)
    edict_type = str(payload.get("edict_type", "")).strip()
    if not edict_type:
        return {"ok": False, "error": "edict_type required"}

    forbidden = set(cfg.get("forbidden_edicts", []))
    if edict_type in forbidden:
        return {
            "ok": False,
            "error": "forbidden_edict",
            "message": "신의 봉인이 소원을 막았다.",
            "edict_type": edict_type,
        }

    allowed = set(cfg.get("wish_edict_types", []))
    if allowed and edict_type not in allowed:
        return {"ok": False, "error": "unknown_edict_type", "edict_type": edict_type}

    ok, reason = can_cast_sovereign_wish(state, base_dir=base_dir)
    if not ok:
        return {"ok": False, "error": "cooldown", "message": reason}

    lines = _apply_edict(state, edict_type, payload, base_dir=base_dir, cfg=cfg)
    lines.append("[소원] 하늘에 종이 울리고 세계가 소원을 받아들였다.")
    lines.extend(_apply_backlash(state, base_dir=base_dir))

    sf = _sovereign_flags(state)
    sf["last_sovereign_wish_world_day"] = world_day(state)
    sf["last_edict_type"] = edict_type
    history = sf.setdefault("wish_history", [])
    history.append({"day": world_day(state), "edict_type": edict_type, "payload": dict(payload)})
    if len(history) > 32:
        del history[:-32]

    return {
        "ok": True,
        "edict_type": edict_type,
        "world_day": world_day(state),
        "lines": lines,
    }
