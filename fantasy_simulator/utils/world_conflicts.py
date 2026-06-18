"""World-map wars, invasions, apex threats — kingdoms fall, the world does not."""

from __future__ import annotations

import json
import random
import uuid
from pathlib import Path
from typing import Any

from utils.agent_competition import get_civilization_state, load_civ_config
from utils.civilization_coupling import _append_event, _civ_stage, _all_civ_defs
from utils.field_agents import ecology_enabled
from utils.settlement_build import get_player_settlement


def load_conflicts_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "world_conflicts.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _eco(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("flags", {}).setdefault("ecology", {})


def _wars(state: dict[str, Any]) -> dict[str, Any]:
    eco = _eco(state)
    return eco.setdefault(
        "world_wars",
        {"active": [], "history": [], "apex_cooldown": {}},
    )


def init_world_conflicts(state: dict[str, Any], *, base_dir: str | Path) -> None:
    w = _wars(state)
    cfg = load_conflicts_config(base_dir)
    w.setdefault("apex_status", {})
    for apex in cfg.get("apex_predators", []):
        w["apex_status"][apex["id"]] = {"dormant": True, "last_threat_turn": 0}


def _military_power(
    state: dict[str, Any],
    civ_id: str,
    cfg: dict[str, Any],
    civ_cfg: dict[str, Any],
    *,
    rng: random.Random,
    bonus: int = 0,
) -> int:
    cs = get_civilization_state(state, civ_id)
    prosperity = int(cs.get("prosperity", 0))
    stage_id = cs.get("stage_id") or _civ_stage(civ_cfg, civ_id, prosperity)
    stage_idx = 0
    defs = _all_civ_defs(civ_cfg).get(civ_id, {})
    for i, st in enumerate(defs.get("stages", [])):
        if st.get("id") == stage_id:
            stage_idx = i + 1
    return prosperity + stage_idx * 18 + bonus + rng.randint(0, 12)


def _player_alliance_bonus(
    state: dict[str, Any], conflicts_cfg: dict[str, Any], *, base_dir: str | Path
) -> int:
    profile = _eco(state).get("player_profile") or {}
    realm = profile.get("realm_id")
    if not realm:
        return 0
    bal = conflicts_cfg.get("balance", {})
    ps = get_player_settlement(state)
    return (
        int(ps.get("construction_level", 1))
        * int(bal.get("player_alliance_bonus_per_build_level", 4))
        + int(ps.get("hired_workers", 0))
        * int(bal.get("player_alliance_bonus_per_worker", 2))
    )


def _pick_war_goal(cfg: dict[str, Any], rng: random.Random) -> tuple[str, str]:
    goals = cfg.get("war_goals", {})
    ids = list(goals.keys())
    weights = [int(goals[g].get("weight", 10)) for g in ids]
    gid = rng.choices(ids, weights=weights, k=1)[0]
    return gid, str(goals[gid].get("label", gid))


def _alliance_power(
    state: dict[str, Any],
    realm_id: str,
    conflicts_cfg: dict[str, Any],
    civ_cfg: dict[str, Any],
    rng: random.Random,
    *,
    base_dir: str | Path,
) -> tuple[int, list[str]]:
    allies = list(conflicts_cfg.get("realm_alliances", {}).get(realm_id, []))
    coord = float(conflicts_cfg.get("balance", {}).get("alliance_coordination", 0.88))
    total = 0
    names: list[str] = []
    for cid in allies:
        if cid in _all_civ_defs(civ_cfg) or cid.startswith("player_"):
            p = _military_power(state, cid, civ_cfg, civ_cfg, rng=rng)
            total += p
            names.append(cid)
    total = int(total * coord) + _player_alliance_bonus(state, conflicts_cfg, base_dir=base_dir)
    return total, names


def _apply_loss(
    state: dict[str, Any],
    civ_id: str,
    loss: int,
    *,
    base_dir: str | Path,
    floor: int,
) -> None:
    cs = get_civilization_state(state, civ_id)
    cs["prosperity"] = max(floor, int(cs.get("prosperity", 0)) - loss)
    cfg = load_civ_config(base_dir)
    cs["stage_id"] = _civ_stage(cfg, civ_id, int(cs["prosperity"]))


def _enforce_world_floor(state: dict[str, Any], base_dir: str | Path) -> None:
    wcfg = load_conflicts_config(base_dir)
    floor = int(wcfg.get("balance", {}).get("world_prosperity_floor", 8))
    for cid in list(_eco(state).get("civilizations", {})):
        cs = get_civilization_state(state, cid)
        if int(cs.get("prosperity", 0)) < floor:
            cs["prosperity"] = floor


def _resolve_outcome(
    ratio: float,
    conflicts_cfg: dict[str, Any],
) -> str:
    bands = conflicts_cfg.get("outcome_bands", {})
    for name in ("repelled", "stalemate", "invasion_success", "kingdom_collapse", "apex_kingdom_fall"):
        if ratio <= float(bands.get(name, {}).get("max_ratio", 99)):
            return name
    return "stalemate"


def _maybe_start_invasion(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random,
) -> dict[str, Any] | None:
    conflicts = load_conflicts_config(base_dir)
    civ_cfg = load_civ_config(base_dir)
    chance = float(conflicts.get("balance", {}).get("invasion_chance_per_beat", 0.2))
    if rng.random() > chance:
        return None

    candidates = []
    for pair in conflicts.get("invasion_pairs", []):
        aciv = pair["attacker_civ"]
        cs = get_civilization_state(state, aciv)
        if int(cs.get("prosperity", 0)) >= int(pair.get("min_attacker_prosperity", 30)):
            candidates.append(pair)
    if not candidates:
        return None

    pair = rng.choice(candidates)
    attacker = pair["attacker_civ"]
    realm = pair["defender_realm"]
    kingdom = pair["defender_kingdom"]
    goal_id, goal_label = _pick_war_goal(conflicts, rng)

    profile = _eco(state).get("player_profile") or {}
    if profile.get("realm_id") == realm:
        from utils.kingdom_system import get_kingdom_charter
        from utils.kingdom_war import start_siege_war

        if get_kingdom_charter(state):
            siege = start_siege_war(
                state,
                attacker_civ=attacker,
                goal_id=goal_id,
                goal_label=goal_label,
                base_dir=base_dir,
                rng=rng,
            )
            if siege.get("ok"):
                return siege

    atk_p = _military_power(state, attacker, civ_cfg, civ_cfg, rng=rng)
    def_p, allies = _alliance_power(
        state, realm, conflicts, civ_cfg, rng, base_dir=base_dir
    )

    if profile.get("realm_id") == realm:
        def_p += _player_alliance_bonus(state, conflicts, base_dir=base_dir)

    ratio = atk_p / max(1, def_p)
    outcome = _resolve_outcome(ratio, conflicts)
    band = conflicts.get("outcome_bands", {}).get(outcome, {})
    k_floor = int(conflicts.get("balance", {}).get("kingdom_collapse_floor", 5))

    attacker_label = _all_civ_defs(civ_cfg).get(attacker, {}).get("label", attacker)
    lines_narrative: list[str] = []

    if outcome == "repelled":
        _apply_loss(state, attacker, int(band.get("attacker_loss", 15)), base_dir=base_dir, floor=k_floor)
        lines_narrative.append(
            f"[전쟁] {attacker_label}의 {goal_label} 침입이 연합 방어에 막혔다. (공격 {atk_p} vs 방어 {def_p})"
        )
    elif outcome == "stalemate":
        _apply_loss(state, attacker, int(band.get("attacker_loss", 10)), base_dir=base_dir, floor=k_floor)
        for aid in allies[:2]:
            _apply_loss(state, aid, int(band.get("defender_loss", 10)), base_dir=base_dir, floor=k_floor)
        lines_narrative.append(
            f"[전쟁] {goal_label} 목적 전투가 교착 — 양측 피해. (공격 {atk_p} vs 연합 {def_p})"
        )
    elif outcome in ("invasion_success", "kingdom_collapse"):
        cs_atk = get_civilization_state(state, attacker)
        cs_atk["prosperity"] = int(cs_atk.get("prosperity", 0)) + int(band.get("attacker_gain", 8))
        primary_def = allies[0] if allies else f"player_{realm}"
        if primary_def:
            _apply_loss(
                state,
                primary_def,
                int(band.get("defender_loss", 28)),
                base_dir=base_dir,
                floor=k_floor,
            )
        if outcome == "kingdom_collapse":
            lines_narrative.append(
                f"[전쟁·멸망] {kingdom} 왕국이 거의 무너졌다 — 그러나 {realm} 영역 전체는 남아 있다. "
                f"({goal_label}, 공격 {atk_p} vs 연합 {def_p})"
            )
        else:
            lines_narrative.append(
                f"[전쟁] {goal_label} 침공 성공 — {kingdom} 왕국이 큰 피해. "
                f"(공격 {atk_p} vs 연합 {def_p})"
            )
    else:
        lines_narrative.append(f"[전쟁] {outcome}")

    war = {
        "war_id": f"war_{uuid.uuid4().hex[:8]}",
        "type": "invasion",
        "attacker_civ": attacker,
        "attacker_label": attacker_label,
        "defender_realm": realm,
        "defender_kingdom": kingdom,
        "casus_belli": goal_id,
        "goal_label": goal_label,
        "attacker_power": atk_p,
        "defender_power": def_p,
        "allies": allies,
        "power_ratio": round(ratio, 2),
        "outcome": outcome,
        "narrative": lines_narrative[0] if lines_narrative else "",
        "turn": int(state.get("turn", 0)),
    }
    return {"war": war, "lines": lines_narrative}


def _maybe_apex_threat(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random,
) -> dict[str, Any] | None:
    conflicts = load_conflicts_config(base_dir)
    civ_cfg = load_civ_config(base_dir)
    w = _wars(state)
    turn = int(state.get("turn", 0))

    for apex in conflicts.get("apex_predators", []):
        aid = apex["id"]
        cooldown = w.get("apex_cooldown", {}).get(aid, 0)
        if turn - int(cooldown) < 8:
            continue

        bound = apex.get("bound_civ")
        cs = get_civilization_state(state, bound)
        if int(cs.get("prosperity", 0)) < int(apex.get("min_civ_prosperity", 80)):
            continue
        stage = cs.get("stage_id") or ""
        if stage != apex.get("min_civ_stage") and int(cs.get("prosperity", 0)) < int(
            apex.get("min_civ_prosperity", 80)
        ) + 10:
            continue
        if rng.random() > 0.18:
            continue

        realm = apex["realm"]
        kingdom = apex["threat_kingdom"]
        apex_power = int(apex.get("base_power", 130)) + rng.randint(0, 25)
        def_p, allies = _alliance_power(
            state, realm, conflicts, civ_cfg, rng, base_dir=base_dir
        )
        ratio = apex_power / max(1, def_p)

        k_floor = int(conflicts.get("balance", {}).get("kingdom_collapse_floor", 5))
        lines: list[str] = []
        apex_label = apex.get("label", aid)

        if ratio > 1.6:
            outcome = "apex_kingdom_fall"
            primary = allies[0] if allies else bound
            if primary:
                _apply_loss(state, primary, 70, base_dir=base_dir, floor=k_floor)
            lines.append(
                f"[재앙] {apex_label} — 연합이 막지 못해 {kingdom} 왕국이 함락 직전. "
                f"세계 전체는 아직 붕괴하지 않았다. (위협 {apex_power} vs 연합 {def_p})"
            )
        elif ratio > 1.05:
            outcome = "narrow_defeat"
            for aid in allies[:3]:
                _apply_loss(state, aid, 35, base_dir=base_dir, floor=k_floor)
            lines.append(
                f"[재앙] {apex_label} — 연합 대규모 전투에서 패배했으나 {realm} 영역은 유지. "
                f"({apex_power} vs {def_p})"
            )
        else:
            outcome = "apex_repelled"
            cs_bound = get_civilization_state(state, bound)
            cs_bound["prosperity"] = max(k_floor, int(cs_bound.get("prosperity", 0)) - 20)
            lines.append(
                f"[재앙] {apex_label} — 왕국 연합이 간신히 저지했다. ({apex_power} vs {def_p})"
            )

        w["apex_cooldown"][aid] = turn
        war = {
            "war_id": f"apex_{uuid.uuid4().hex[:8]}",
            "type": "apex_threat",
            "apex_id": aid,
            "apex_label": apex_label,
            "bound_civ": bound,
            "defender_realm": realm,
            "defender_kingdom": kingdom,
            "attacker_power": apex_power,
            "defender_power": def_p,
            "allies": allies,
            "power_ratio": round(ratio, 2),
            "outcome": outcome,
            "narrative": lines[0],
            "turn": turn,
        }
        return {"war": war, "lines": lines}

    return None


def tick_world_conflicts(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> list[str]:
    if not ecology_enabled(state):
        return []

    init_world_conflicts(state, base_dir=base_dir)
    conflicts = load_conflicts_config(base_dir)
    w = _wars(state)
    r = rng or random.Random()
    lines: list[str] = []
    max_wars = int(conflicts.get("balance", {}).get("max_wars_per_tick", 1))

    for _ in range(max_wars):
        result = _maybe_apex_threat(state, base_dir=base_dir, rng=r)
        if result is None:
            result = _maybe_start_invasion(state, base_dir=base_dir, rng=r)
        if result is None:
            break
        war = result["war"]
        lines.extend(result.get("lines", []))
        w["history"].append(war)
        if len(w["history"]) > 40:
            w["history"] = w["history"][-40:]
        w["active"] = [war]
        _append_event(
            state,
            {
                "type": "war",
                "war_id": war["war_id"],
                "outcome": war.get("outcome"),
                "narrative": war.get("narrative"),
            },
            base_dir=base_dir,
        )

    from utils.sovereign_siege import tick_sovereign_coalition_siege

    lines.extend(tick_sovereign_coalition_siege(state, base_dir=base_dir))

    _enforce_world_floor(state, base_dir)
    return lines


def conflicts_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    w = _wars(state)
    cfg = load_conflicts_config(base_dir)
    return {
        "active_war": (w.get("active") or [None])[-1] if w.get("active") else None,
        "history": w.get("history", [])[-10:],
        "apex_status": w.get("apex_status", {}),
        "war_goals": cfg.get("war_goals", {}),
        "apex_predators": [
            {"id": a["id"], "label": a["label"], "realm": a["realm"]}
            for a in cfg.get("apex_predators", [])
        ],
    }
