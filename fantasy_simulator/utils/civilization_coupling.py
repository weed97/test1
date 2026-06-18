"""Player-race civilizations coupled to world — ripple when player kingdom grows."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from utils.agent_competition import get_civilization_state, load_civ_config
from utils.ecology_state import ecology_flags
from utils.field_agents import ecology_enabled
from utils.settlement_build import get_player_settlement


def _all_civ_defs(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key in ("civilizations", "npc_societies", "player_civilizations", "off_map_civilizations"):
        out.update(cfg.get(key, {}))
    return out


def _civ_stage(cfg: dict[str, Any], civ_id: str, prosperity: int) -> str:
    defs = _all_civ_defs(cfg).get(civ_id, {})
    stage_id = defs.get("stages", [{}])[0].get("id", "unknown")
    for st in defs.get("stages", []):
        if prosperity >= int(st.get("prosperity", 0)):
            stage_id = st["id"]
    return stage_id


def _stage_label(cfg: dict[str, Any], civ_id: str, stage_id: str) -> str:
    for st in _all_civ_defs(cfg).get(civ_id, {}).get("stages", []):
        if st.get("id") == stage_id:
            return str(st.get("label", stage_id))
    return stage_id


def _append_event(state: dict[str, Any], event: dict[str, Any], *, base_dir: str | Path) -> None:
    cfg = load_civ_config(base_dir)
    cap = int(cfg.get("coupling", {}).get("max_recent_events", 24))
    events = ecology_flags(state).setdefault("civilization_events", [])
    events.append(event)
    if len(events) > cap:
        del events[: len(events) - cap]


def init_player_civilization(
    state: dict[str, Any],
    *,
    player_race: str = "human",
    base_dir: str | Path,
) -> dict[str, Any]:
    """Bind session to race realm + player civ; seed off-map civilizations."""
    cfg = load_civ_config(base_dir)
    race_def = cfg.get("player_races", {}).get(player_race)
    if not race_def:
        player_race = "human"
        race_def = cfg["player_races"]["human"]

    player_civ_id = str(race_def["player_civilization_id"])
    eco = ecology_flags(state)
    eco["player_profile"] = {
        "race": player_race,
        "race_label": race_def.get("label", player_race),
        "realm_id": race_def.get("realm_id"),
        "kingdom_id": race_def.get("kingdom_id"),
        "player_civilization_id": player_civ_id,
        "citizen_stage": "adventurer",
        "citizen_stage_label": "모험가",
    }

    world = state.setdefault("world", {})
    if race_def.get("default_map_id"):
        world["map_id"] = race_def["default_map_id"]
    if race_def.get("world_x") is not None:
        world["world_x"] = int(race_def["world_x"])
        world["world_y"] = int(race_def["world_y"])
    world["realm_id"] = race_def.get("realm_id")
    world["kingdom_id"] = race_def.get("kingdom_id")

    get_civilization_state(state, player_civ_id)
    for civ_id in race_def.get("linked_civs", []):
        get_civilization_state(state, civ_id)

    for civ_id in cfg.get("off_map_civilizations", {}):
        cs = get_civilization_state(state, civ_id)
        if cs.get("stage_id") is None:
            cs["prosperity"] = int(cs.get("prosperity", 0)) + random.randint(3, 12)
            cs["stage_id"] = _civ_stage(cfg, civ_id, int(cs["prosperity"]))

    eco["dev_snapshot"] = _development_snapshot(state)
    return dict(eco["player_profile"])


def _development_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    ps = get_player_settlement(state)
    return {
        "construction_level": int(ps.get("construction_level", 1)),
        "construction_xp": int(ps.get("construction_xp", 0)),
        "completed_count": len(ps.get("completed_buildings", [])),
        "sites_count": len(ps.get("sites", [])),
        "is_kingdom": bool(ps.get("is_kingdom")),
        "hired_workers": int(ps.get("hired_workers", 0)),
    }


def _citizen_stage_from_state(state: dict[str, Any]) -> tuple[str, str]:
    ps = get_player_settlement(state)
    if ps.get("is_kingdom"):
        return "kingdom", "왕국"
    lvl = int(ps.get("construction_level", 1))
    completed = len(ps.get("completed_buildings", []))
    if lvl >= 2 or completed >= 1:
        return "citizen", "왕국 시민"
    if ps.get("sites") or lvl > 1:
        return "settler", "개척자"
    return "adventurer", "모험가"


def _pulse_from_snapshot_delta(
    old: dict[str, Any], new: dict[str, Any], cfg: dict[str, Any]
) -> tuple[int, str]:
    coupling = cfg.get("coupling", {})
    pulse = 0
    reasons: list[str] = []

    if new["construction_level"] > old["construction_level"]:
        d = new["construction_level"] - old["construction_level"]
        gain = d * int(coupling.get("pulse_per_construction_level", 6))
        pulse += gain
        reasons.append(f"건축 Lv{new['construction_level']}")

    if new["completed_count"] > old["completed_count"]:
        pulse += int(coupling.get("pulse_building_complete", 18))
        reasons.append("건물 완공")

    if new["is_kingdom"] and not old["is_kingdom"]:
        pulse += int(coupling.get("pulse_kingdom_founded", 70))
        reasons.append("왕국 선포")

    reason = ", ".join(reasons) if reasons else "탐험·시간 경과"
    return pulse, reason


def _apply_prosperity(
    state: dict[str, Any],
    civ_id: str,
    amount: int,
    *,
    base_dir: str | Path,
    source: str,
) -> str | None:
    if amount <= 0:
        return None
    cfg = load_civ_config(base_dir)
    cs = get_civilization_state(state, civ_id)
    old_stage = cs.get("stage_id")
    cs["prosperity"] = int(cs.get("prosperity", 0)) + amount
    cs["stage_id"] = _civ_stage(cfg, civ_id, int(cs["prosperity"]))
    if cs["stage_id"] != old_stage and old_stage is not None:
        label = _all_civ_defs(cfg).get(civ_id, {}).get("label", civ_id)
        st_lab = _stage_label(cfg, civ_id, cs["stage_id"])
        _append_event(
            state,
            {
                "type": "stage_up",
                "civilization_id": civ_id,
                "label": label,
                "stage_id": cs["stage_id"],
                "stage_label": st_lab,
                "source": source,
            },
            base_dir=base_dir,
        )
        return f"[세계] {label} — 「{st_lab}」 ({source})"
    return None


def tick_civilization_coupling(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> list[str]:
    """Pulse player civ from development; ripple linked + off-map civilizations."""
    if not ecology_enabled(state):
        return []

    eco = ecology_flags(state)
    profile = eco.get("player_profile")
    if not profile:
        return []

    cfg = load_civ_config(base_dir)
    coupling = cfg.get("coupling", {})
    r = rng or random.Random()
    lines: list[str] = []

    old_snap = eco.get("dev_snapshot") or _development_snapshot(state)
    new_snap = _development_snapshot(state)
    pulse, reason = _pulse_from_snapshot_delta(old_snap, new_snap, cfg)
    pulse += int(coupling.get("base_pulse_per_beat", 2))
    eco["dev_snapshot"] = new_snap

    stage_id, stage_label = _citizen_stage_from_state(state)
    if profile.get("citizen_stage") != stage_id:
        profile["citizen_stage"] = stage_id
        profile["citizen_stage_label"] = stage_label
        lines.append(f"[여정] {profile['race_label']} — {stage_label} 단계에 도달했다.")
        _append_event(
            state,
            {
                "type": "player_stage",
                "stage_id": stage_id,
                "stage_label": stage_label,
                "source": reason,
            },
            base_dir=base_dir,
        )

    player_civ = str(profile["player_civilization_id"])
    line = _apply_prosperity(state, player_civ, pulse, base_dir=base_dir, source=reason)
    if line:
        lines.append(line)

    ripple = max(1, int(pulse * float(coupling.get("ripple_ratio", 0.35))))
    race_def = cfg.get("player_races", {}).get(profile["race"], {})
    linked = list(race_def.get("linked_civs", []))

    for civ_id in linked:
        amt = max(1, int(ripple * r.uniform(0.7, 1.1)))
        rl = _apply_prosperity(
            state, civ_id, amt, base_dir=base_dir, source=f"연동({reason})"
        )
        if rl:
            lines.append(rl)
        else:
            _append_event(
                state,
                {
                    "type": "ripple",
                    "civilization_id": civ_id,
                    "prosperity_delta": amt,
                    "source": reason,
                },
                base_dir=base_dir,
            )

    off_min = int(coupling.get("off_map_tick_min", 1))
    off_max = int(coupling.get("off_map_tick_max", 4))
    off_ripple = float(coupling.get("off_map_ripple_ratio", 0.22))
    player_realm = profile.get("realm_id")

    for civ_id, cdef in cfg.get("off_map_civilizations", {}).items():
        if civ_id in linked:
            continue
        amt = r.randint(off_min, off_max) + max(0, int(pulse * off_ripple))
        if cdef.get("realm_id") == player_realm:
            amt = max(amt, ripple // 2)
        rl = _apply_prosperity(
            state,
            civ_id,
            amt,
            base_dir=base_dir,
            source="세계의 숨결",
        )
        if rl:
            lines.append(rl)

    eco["world_pulse"] = {
        "last_pulse": pulse,
        "last_reason": reason,
        "tick": int(state.get("turn", 0)),
    }
    return lines


def civilization_world_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    cfg = load_civ_config(base_dir)
    eco = ecology_flags(state)
    civs = eco.get("civilizations", {})
    enriched: dict[str, Any] = {}
    for cid, cs in civs.items():
        defs = _all_civ_defs(cfg).get(cid, {})
        stage_id = cs.get("stage_id") or _civ_stage(cfg, cid, int(cs.get("prosperity", 0)))
        enriched[cid] = {
            **cs,
            "label": defs.get("label", cid),
            "kind": defs.get("kind", "unknown"),
            "realm_id": defs.get("realm_id"),
            "stage_label": _stage_label(cfg, cid, stage_id),
        }
    return {
        "player_profile": eco.get("player_profile"),
        "civilizations": enriched,
        "recent_events": list(eco.get("civilization_events", [])),
        "world_pulse": eco.get("world_pulse"),
    }
