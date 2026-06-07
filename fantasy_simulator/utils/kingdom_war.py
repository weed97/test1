"""Kingdom siege wars — 공성/수성, class lanes (sword/bow/magic), monster legions."""

from __future__ import annotations

import json
import random
import uuid
from pathlib import Path
from typing import Any

from utils.agent_competition import get_civilization_state
from utils.field_agents import ecology_enabled
from utils.kingdom_system import (
    apply_siege_damage,
    compute_defense_rating,
    doctrine_effects,
    get_kingdom_charter,
    load_kingdom_config,
)


def load_war_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "kingdom_war.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _eco(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("flags", {}).setdefault("ecology", {})


def _war_bucket(state: dict[str, Any]) -> dict[str, Any]:
    return _eco(state).setdefault("kingdom_wars", {"active": [], "history": []})


def find_active_siege(state: dict[str, Any], war_id: str) -> dict[str, Any] | None:
    bucket = _war_bucket(state)
    return next(
        (w for w in bucket.get("active", []) if w.get("war_id") == war_id),
        None,
    )


def _class_cfg(wcfg: dict[str, Any], cls: str) -> dict[str, Any]:
    return wcfg.get("combat_classes", {}).get(cls, {})


def defender_forces_from_charter(
    charter: dict[str, Any], wcfg: dict[str, Any]
) -> dict[str, int]:
    """Map kingdom military + city mages to sword/bow/magic lanes."""
    mapping = wcfg.get("defender_mapping", {})
    mil = charter.get("military", {})
    forces: dict[str, int] = {"sword": 0, "bow": 0, "magic": 0, "beast": 0}
    for unit_key, cls in mapping.items():
        if unit_key == "mage_per_city_level":
            continue
        if unit_key in mil:
            target = str(cls)
            forces[target] = forces.get(target, 0) + int(mil.get(unit_key, 0))
    city = int(charter.get("interior", {}).get("city_level", 0))
    mages = city * int(mapping.get("mage_per_city_level", 3))
    forces["magic"] = forces.get("magic", 0) + mages
    return forces


def build_monster_legion(
    civ_id: str,
    wcfg: dict[str, Any],
    rng: random.Random,
) -> dict[str, Any]:
    legions = wcfg.get("monster_legions", {})
    ldef = legions.get(civ_id) or legions.get("default", {})
    size = int(ldef.get("size_base", 60)) + rng.randint(-12, 25)
    size = max(20, size)
    mix: dict[str, float] = ldef.get("mix", {})
    forces: dict[str, int] = {}
    for cls, ratio in mix.items():
        forces[cls] = max(0, int(size * float(ratio)))
    label = ldef.get("label", civ_id)
    return {
        "civ_id": civ_id,
        "label": label,
        "forces": forces,
        "total": sum(forces.values()),
        "morale": 75 + rng.randint(0, 20),
    }


def _lane_power(
    forces: dict[str, int],
    wcfg: dict[str, Any],
    *,
    phase: dict[str, Any],
    defending: bool,
    walls_level: int = 0,
    on_wall_bow_bonus: bool = False,
) -> tuple[int, dict[str, int]]:
    """Aggregate attack or defense power per class for current phase."""
    classes = wcfg.get("combat_classes", {})
    total = 0
    breakdown: dict[str, int] = {}
    for cls, count in forces.items():
        if count <= 0:
            continue
        cdef = classes.get(cls, {})
        atk = int(cdef.get("attack", 10))
        dfn = int(cdef.get("defense", 8))
        weight = 1.0
        if cls == "bow":
            weight = float(phase.get("bow_weight", 1.0))
            if defending and on_wall_bow_bonus:
                dfn = int(dfn * float(cdef.get("on_wall_def_mult", 1.5)))
        elif cls == "magic":
            weight = float(phase.get("magic_weight", 1.0))
        elif cls == "sword":
            weight = float(phase.get("sword_weight", 1.0))
            if defending and walls_level > 0:
                dfn = int(dfn * (1.0 + walls_level * 0.1))
        power = (dfn if defending else atk) * count
        power = int(power * weight)
        breakdown[cls] = power
        total += power
    return total, breakdown


def _phase_for_round(round_num: int, wcfg: dict[str, Any]) -> dict[str, Any]:
    phases = wcfg.get("siege", {}).get("phases", [])
    if not phases:
        return {"id": "assault", "label": "공성"}
    return phases[round_num % len(phases)]


def start_siege_war(
    state: dict[str, Any],
    *,
    attacker_civ: str,
    goal_id: str,
    goal_label: str,
    base_dir: str | Path,
    rng: random.Random,
) -> dict[str, Any]:
    charter = get_kingdom_charter(state)
    if not charter:
        return {"ok": False, "error": "플레이어 왕국 없음 — 공성전 불가"}

    wcfg = load_war_config(base_dir)
    kcfg = load_kingdom_config(base_dir)
    bucket = _war_bucket(state)
    if len(bucket.get("active", [])) >= 2:
        return {"ok": False, "error": "동시 공성전 한도"}

    attacker = build_monster_legion(attacker_civ, wcfg, rng)
    defender_forces = defender_forces_from_charter(charter, wcfg)
    fort = charter.get("fortifications", {})
    war_id = f"siege_{uuid.uuid4().hex[:8]}"

    war = {
        "war_id": war_id,
        "type": "siege",
        "status": "active",
        "casus_belli": goal_id,
        "goal_label": goal_label,
        "round": 0,
        "max_rounds": int(wcfg.get("siege", {}).get("max_rounds", 15)),
        "attacker": attacker,
        "defender": {
            "kingdom_id": charter.get("kingdom_id"),
            "kingdom_name": charter.get("name"),
            "forces": defender_forces,
            "morale": min(100, int(charter.get("stability", 75)) + 10),
            "walls_level": int(fort.get("walls_level", 0)),
            "tower_count": int(fort.get("tower_count", 0)),
        },
        "barrier_hp_at_start": int(charter.get("barrier", {}).get("hp", 0)),
        "combat_log": [],
        "turn_started": int(state.get("turn", 0)),
    }
    bucket.setdefault("active", []).append(war)

    from utils.siege_command import init_war_command

    init_war_command(war, charter, base_dir=base_dir, rng=rng)

    line = (
        f"[공성전 개시] {attacker['label']}이(가) '{charter.get('name')}'을(를) 공격한다. "
        f"목적: {goal_label} · 검/활/마법/야수 군단 총 {attacker['total']}."
    )
    def_cmds = war.get("command", {}).get("defender", {}).get("commanders", [])
    if def_cmds:
        line += f" · 수성 지휘관 {len(def_cmds)}명 전장 배치"
    return {"ok": True, "war": war, "lines": [line]}


def _rounds_for_turn(
    sim_cfg: dict[str, Any],
    *,
    temporal_mode: str,
    minutes_advanced: int,
) -> int:
    if minutes_advanced > 0:
        mpr = max(1, int(sim_cfg.get("minutes_per_round", 20)))
        return max(1, min(6, minutes_advanced // mpr))
    key = f"rounds_per_turn_{temporal_mode}"
    return max(1, int(sim_cfg.get(key, sim_cfg.get("rounds_per_turn_classic", 1))))


def _micro_events(
    atk_br: dict[str, int],
    def_br: dict[str, int],
    phase: dict[str, Any],
    wcfg: dict[str, Any],
    *,
    t0_ms: int,
    stagger_ms: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    t = t0_ms
    templates = {
        "sword": ("돌격", "방어선"),
        "bow": ("일제 사격", "성벽 반격"),
        "magic": ("마법 포격", "결계 강화"),
        "beast": ("야수 돌진", "창쇠 방어"),
    }
    for cls, power in atk_br.items():
        if power <= 0:
            continue
        verb, _ = templates.get(cls, ("공격", ""))
        label = _class_cfg(wcfg, cls).get("label", cls)
        events.append(
            {
                "t_ms": t,
                "phase": phase.get("id"),
                "side": "attacker",
                "class": cls,
                "kind": "strike",
                "label": label,
                "power": power,
                "text": f"공격군 {label} {verb} (위력 {power})",
            }
        )
        t += stagger_ms + rng.randint(0, 30)
    for cls, power in def_br.items():
        if power <= 0:
            continue
        _, verb = templates.get(cls, ("", "방어"))
        label = _class_cfg(wcfg, cls).get("label", cls)
        events.append(
            {
                "t_ms": t,
                "phase": phase.get("id"),
                "side": "defender",
                "class": cls,
                "kind": "defend",
                "label": label,
                "power": power,
                "text": f"수성군 {label} {verb} (방어 {power})",
            }
        )
        t += stagger_ms + rng.randint(0, 30)
    return events


def resolve_siege_round(
    state: dict[str, Any],
    war: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random,
    sim_t0_ms: int = 0,
) -> dict[str, Any]:
    charter = get_kingdom_charter(state)
    if not charter:
        war["status"] = "aborted"
        return {
            "lines": ["[공성전] 왕국 소멸 — 전투 중단"],
            "events": [],
            "round": war.get("round", 0),
        }

    wcfg = load_war_config(base_dir)
    kcfg = load_kingdom_config(base_dir)
    fx = doctrine_effects(charter, kcfg)
    siege_cfg = wcfg.get("siege", {})
    war["round"] = int(war.get("round", 0)) + 1
    rnd = war["round"]
    phase = _phase_for_round(rnd - 1, wcfg)

    atk = war["attacker"]
    dfn = war["defender"]
    atk_forces: dict[str, int] = dict(atk.get("forces", {}))
    dfn_forces: dict[str, int] = dict(dfn.get("forces", {}))
    walls = int(dfn.get("walls_level", 0))
    towers = int(dfn.get("tower_count", 0))

    atk_power, atk_br = _lane_power(atk_forces, wcfg, phase=phase, defending=False)
    def_power, def_br = _lane_power(
        dfn_forces,
        wcfg,
        phase=phase,
        defending=True,
        walls_level=walls,
        on_wall_bow_bonus=True,
    )
    def_rating = compute_defense_rating(charter, kcfg)
    def_power += int(def_rating.get("tower_attack", 0)) + int(
        def_rating.get("wall_archer_volley", 0)
    ) // max(1, rnd)
    def_power += int(def_rating.get("garrison_power", 0)) // 2
    def_power = int(def_power * (1.0 + walls * float(siege_cfg.get("defender_wall_bonus_per_level", 0.12))))
    def_power = int(def_power * float(fx.get("garrison_defense_mult", 1.0)))

    from utils.siege_command import load_command_config, resolve_command_round

    cmd_cfg = load_command_config(base_dir)
    lost_cfg = cmd_cfg.get("command_lost", {})
    atk_coord = atk_power
    def_coord = def_power
    atk_cmd = war.get("command", {}).get("attacker", {})
    def_cmd = war.get("command", {}).get("defender", {})
    if atk_cmd.get("autonomous"):
        atk_coord = int(atk_power * rng.uniform(0.88, 1.12))
    if def_cmd.get("autonomous"):
        def_coord = int(
            def_power * (1.0 - float(lost_cfg.get("defense_coordination_penalty", 0.38)))
        )

    wcfg_full = wcfg
    sim_cfg = wcfg_full.get("simulation", {})
    stagger = int(sim_cfg.get("stagger_ms_per_event", 90))
    events: list[dict[str, Any]] = []
    if sim_cfg.get("micro_events_per_round", True):
        events = _micro_events(
            atk_br, def_br, phase, wcfg, t0_ms=sim_t0_ms, stagger_ms=stagger, rng=rng
        )

    lines: list[str] = []
    lines.append(f"[공성 {rnd}라운드·{phase.get('label', '?')}]")

    net = atk_coord - def_coord
    cmd_result = resolve_command_round(
        war,
        net=net,
        atk_power=atk_power,
        def_power=def_power,
        base_dir=base_dir,
        rng=rng,
        sim_t0_ms=sim_t0_ms,
        stagger_ms=stagger,
    )
    lines.extend(cmd_result.get("lines", []))
    events.extend(cmd_result.get("events", []))
    barrier_mult = float(cmd_result.get("barrier_damage_mult", 0.15))
    def_coord = int(def_coord * float(cmd_result.get("defense_coordination_mult", 1.0)))
    net = atk_coord - def_coord

    for ev in events:
        if ev.get("text"):
            lines.append(f"  {ev['text']}")

    if net > 0:
        barrier_dmg = int(
            net
            * float(siege_cfg.get("barrier_damage_from_magic_mult", 1.0))
            * barrier_mult
        )
        barrier_dmg += int(atk_br.get("magic", 0) * float(_class_cfg(wcfg, "magic").get("vs_barrier", 1.0)) * 0.08)
        barrier_dmg += int(atk_br.get("sword", 0) * 0.05)
        siege_result = apply_siege_damage(
            state, barrier_dmg, base_dir=base_dir, siege_type="magical"
        )
        lines.append(
            f"  결계 피해 {siege_result.get('damage_to_barrier', 0)} "
            f"(잔여 {siege_result.get('barrier_hp', '?')})"
        )
        dfn["morale"] = max(0, int(dfn.get("morale", 80)) - 5 - rng.randint(0, 4))
        atk["morale"] = min(100, int(atk.get("morale", 75)) + 2)
        if siege_result.get("barrier_broken"):
            lines.append("  ⚠ 왕국 결계 붕괴 — 물리적 함락 위험!")
            events.append(
                {
                    "t_ms": sim_t0_ms + stagger * (len(events) + 1),
                    "kind": "barrier_break",
                    "text": "왕국 결계가 산산조각났다!",
                }
            )
    else:
        repel = abs(net)
        lines.append(f"  수성 성공 — 공격군 퇴각 압박 ({repel})")
        atk["morale"] = max(0, int(atk.get("morale", 75)) - 6 - rng.randint(0, 5))
        dfn["morale"] = min(100, int(dfn.get("morale", 80)) + 3)

    # Casualties (abstract headcount)
    if net > 0:
        for cls in list(atk_forces.keys()):
            loss = max(0, int(atk_forces[cls] * rng.uniform(0.02, 0.08)))
            atk_forces[cls] = max(0, atk_forces[cls] - loss)
        for cls in list(dfn_forces.keys()):
            loss = max(0, int(dfn_forces[cls] * rng.uniform(0.03, 0.1)))
            dfn_forces[cls] = max(0, dfn_forces[cls] - loss)
    else:
        for cls in list(atk_forces.keys()):
            loss = max(0, int(atk_forces[cls] * rng.uniform(0.05, 0.12)))
            atk_forces[cls] = max(0, atk_forces[cls] - loss)

    atk["forces"] = atk_forces
    atk["total"] = sum(atk_forces.values())
    dfn["forces"] = dfn_forces
    war["combat_log"].append(
        {
            "round": rnd,
            "phase": phase.get("id"),
            "attack_power": atk_power,
            "defense_power": def_power,
            "net": net,
        }
    )

    morale_floor = int(siege_cfg.get("morale_break_threshold", 25))
    charter_barrier = int(charter.get("barrier", {}).get("hp", 0))

    if int(atk.get("morale", 0)) <= morale_floor or atk["total"] < 10:
        war["status"] = "ended"
        war["outcome"] = "siege_repelled"
        lines.append(f"[공성전 종료] {atk['label']} 군단 패주 — 왕국 방어 성공!")
        _finalize_siege(state, war, base_dir=base_dir)
    elif charter_barrier <= 0 and rnd >= 3:
        war["status"] = "ended"
        war["outcome"] = "barrier_broken"
        lines.append("[공성전 종료] 결계 붕괴 — 왕국이 물리적 함락 위기에 처했다.")
        charter["stability"] = max(0, int(charter.get("stability", 75)) - 15)
        _finalize_siege(state, war, base_dir=base_dir)
    elif rnd >= int(war.get("max_rounds", 15)):
        war["status"] = "ended"
        war["outcome"] = "kingdom_endured"
        lines.append("[공성전 종료] 장기 공성 끝에 왕국이 버텼다.")
        charter["stability"] = min(100, int(charter.get("stability", 75)) + 8)
        _finalize_siege(state, war, base_dir=base_dir)

    charter = get_kingdom_charter(state)
    barrier_hp = int(charter.get("barrier", {}).get("hp", 0)) if charter else 0
    return {
        "lines": lines,
        "events": events,
        "round": rnd,
        "phase": phase.get("id"),
        "attack_power": atk_power,
        "defense_power": def_power,
        "net": net,
        "attacker_morale": int(atk.get("morale", 0)),
        "defender_morale": int(dfn.get("morale", 0)),
        "barrier_hp": barrier_hp,
        "war_status": war.get("status"),
        "outcome": war.get("outcome"),
    }


def _finalize_siege(
    state: dict[str, Any],
    war: dict[str, Any],
    *,
    base_dir: str | Path,
) -> None:
    bucket = _war_bucket(state)
    active = bucket.get("active", [])
    if war in active:
        active.remove(war)
    hist = bucket.setdefault("history", [])
    war["turn_ended"] = int(state.get("turn", 0))
    hist.append(war)
    if len(hist) > 30:
        del hist[: len(hist) - 30]

    outcome = war.get("outcome", "")
    attacker_civ = war.get("attacker", {}).get("civ_id")
    if attacker_civ and outcome == "siege_repelled":
        cs = get_civilization_state(state, attacker_civ)
        cs["prosperity"] = max(5, int(cs.get("prosperity", 0)) - 12)
    elif attacker_civ and outcome == "barrier_broken":
        cs = get_civilization_state(state, attacker_civ)
        cs["prosperity"] = int(cs.get("prosperity", 0)) + 8


def tick_siege_for_sim_minutes(
    state: dict[str, Any],
    *,
    sim_minutes: float,
    base_dir: str | Path,
    rng: random.Random | None = None,
    sim_clock_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve siege rounds from accumulated simulation minutes (realtime clock)."""
    empty: dict[str, Any] = {"lines": [], "simulation": None, "new_events": []}
    if not ecology_enabled(state) or not get_kingdom_charter(state):
        return empty

    bucket = _war_bucket(state)
    active = [w for w in bucket.get("active", []) if w.get("status") == "active"]
    if not active:
        return empty

    wcfg = load_war_config(base_dir)
    sc = state.setdefault("meta", {}).setdefault("sim_clock", {})
    siege_cfg = (sim_clock_cfg or {}).get("siege", {})
    mpr = max(
        1.0,
        float(
            siege_cfg.get(
                "minutes_per_round",
                wcfg.get("simulation", {}).get("minutes_per_round", 20),
            )
        ),
    )
    sc["siege_accum"] = float(sc.get("siege_accum", 0.0)) + float(sim_minutes)
    stagger = int(
        siege_cfg.get(
            "stagger_ms_per_event",
            wcfg.get("simulation", {}).get("stagger_ms_per_event", 90),
        )
    )
    rng = rng or random.Random()
    t_cursor = int(sc.get("siege_t_cursor_ms", 0))

    all_lines: list[str] = []
    new_events: list[dict[str, Any]] = []
    war_sims: list[dict[str, Any]] = []
    rounds_done = 0

    while sc["siege_accum"] >= mpr:
        sc["siege_accum"] -= mpr
        rounds_done += 1
        for war in list(active):
            if war.get("status") != "active":
                continue
            result = resolve_siege_round(
                state,
                war,
                base_dir=base_dir,
                rng=rng,
                sim_t0_ms=t_cursor,
            )
            all_lines.extend(result.get("lines", []))
            evs = result.get("events", [])
            new_events.extend(evs)
            t_cursor += stagger * max(1, len(evs)) + 200
            war_sims.append(
                {
                    "war_id": war.get("war_id"),
                    "attacker_label": war.get("attacker", {}).get("label"),
                    "defender_name": war.get("defender", {}).get("kingdom_name"),
                    "status": war.get("status"),
                    "outcome": war.get("outcome"),
                    "round": result.get("round"),
                    "barrier_hp": result.get("barrier_hp"),
                    "events": evs,
                }
            )
        active = [w for w in bucket.get("active", []) if w.get("status") == "active"]
        if not active:
            break

    sc["siege_t_cursor_ms"] = t_cursor
    if rounds_done == 0:
        return empty

    charter = get_kingdom_charter(state)
    simulation = {
        "source": "sim_clock",
        "rounds_simulated": rounds_done,
        "sim_minutes": sim_minutes,
        "wars": war_sims,
        "barrier_hp": int(charter.get("barrier", {}).get("hp", 0)) if charter else 0,
    }
    bucket["last_simulation"] = simulation
    if new_events:
        state.setdefault("flags", {}).setdefault("ecology", {})["_last_siege_sim"] = simulation
    return {"lines": all_lines, "simulation": simulation, "new_events": new_events}


def simulate_kingdom_wars_for_turn(
    state: dict[str, Any],
    *,
    turn: int,
    temporal_mode: str = "classic",
    minutes_advanced: int = 0,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Auto-simulate active sieges for one player turn (no manual API step)."""
    empty: dict[str, Any] = {"lines": [], "simulation": None}
    if not ecology_enabled(state):
        return empty
    try:
        from utils.sim_clock import sim_clock_enabled

        if sim_clock_enabled(state, base_dir=base_dir):
            return empty
    except ImportError:
        pass
    if not get_kingdom_charter(state):
        return empty

    bucket = _war_bucket(state)
    active = [w for w in bucket.get("active", []) if w.get("status") == "active"]
    if not active:
        return empty

    wcfg = load_war_config(base_dir)
    sim_cfg = wcfg.get("simulation", {})
    if not sim_cfg.get("auto_on_every_turn", True):
        return empty

    rng = rng or random.Random()
    rounds = _rounds_for_turn(
        sim_cfg, temporal_mode=temporal_mode, minutes_advanced=minutes_advanced
    )
    stagger = int(sim_cfg.get("stagger_ms_per_event", 90))

    all_lines: list[str] = []
    war_sims: list[dict[str, Any]] = []
    t_cursor = 0

    for war in active:
        if war.get("status") != "active":
            continue
        war_events: list[dict[str, Any]] = []
        war_rounds: list[dict[str, Any]] = []
        for _ in range(rounds):
            if war.get("status") != "active":
                break
            result = resolve_siege_round(
                state,
                war,
                base_dir=base_dir,
                rng=rng,
                sim_t0_ms=t_cursor,
            )
            all_lines.extend(result.get("lines", []))
            war_events.extend(result.get("events", []))
            war_rounds.append(
                {
                    "round": result.get("round"),
                    "phase": result.get("phase"),
                    "attack_power": result.get("attack_power"),
                    "defense_power": result.get("defense_power"),
                    "net": result.get("net"),
                    "barrier_hp": result.get("barrier_hp"),
                }
            )
            t_cursor += stagger * max(1, len(result.get("events", []))) + 200

        charter = get_kingdom_charter(state)
        war_sims.append(
            {
                "war_id": war.get("war_id"),
                "attacker_label": war.get("attacker", {}).get("label"),
                "defender_name": war.get("defender", {}).get("kingdom_name"),
                "status": war.get("status"),
                "outcome": war.get("outcome"),
                "rounds_simulated": len(war_rounds),
                "rounds": war_rounds,
                "events": war_events,
                "barrier_hp": int(charter.get("barrier", {}).get("hp", 0)) if charter else 0,
            }
        )

    simulation = {
        "turn": turn,
        "temporal_mode": temporal_mode,
        "minutes_advanced": minutes_advanced,
        "rounds_per_war": rounds,
        "wars": war_sims,
    }
    bucket["last_simulation"] = simulation
    return {"lines": all_lines, "simulation": simulation}


def tick_kingdom_wars(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
    temporal_mode: str = "classic",
    minutes_advanced: int = 0,
) -> list[str]:
    """Backward-compatible wrapper — prefer simulate_kingdom_wars_for_turn."""
    result = simulate_kingdom_wars_for_turn(
        state,
        turn=int(state.get("turn", 0)),
        temporal_mode=temporal_mode,
        minutes_advanced=minutes_advanced,
        base_dir=base_dir,
        rng=rng,
    )
    return result.get("lines", [])


def siege_live_snapshot(
    state: dict[str, Any],
    war: dict[str, Any],
    *,
    base_dir: str | Path,
) -> dict[str, Any]:
    """Normalized live siege view for Godot 2D battlefield (not replay timeline)."""
    charter = get_kingdom_charter(state)
    wcfg = load_war_config(base_dir)
    phases = wcfg.get("siege", {}).get("phases", [])
    rnd = int(war.get("round", 0))
    if rnd > 0:
        phase = _phase_for_round(rnd - 1, wcfg)
    elif phases:
        phase = phases[0]
    else:
        phase = {"id": "assault", "label": "공성"}
    atk = war.get("attacker", {})
    dfn = war.get("defender", {})
    barrier_hp = int(charter.get("barrier", {}).get("hp", 0)) if charter else 0
    barrier_max = int(charter.get("barrier", {}).get("max_hp", 12000)) if charter else 12000
    last_log = war.get("combat_log", [])
    last_net = int(last_log[-1].get("net", 0)) if last_log else 0
    from utils.siege_command import command_live_view

    return {
        "war_id": war.get("war_id"),
        "status": war.get("status"),
        "outcome": war.get("outcome"),
        "round": rnd,
        "max_rounds": int(war.get("max_rounds", 15)),
        "phase": {"id": phase.get("id"), "label": phase.get("label")},
        "barrier_hp": barrier_hp,
        "barrier_max": barrier_max,
        "last_net": last_net,
        "command": command_live_view(war, base_dir=base_dir),
        "attacker": {
            "label": atk.get("label"),
            "morale": int(atk.get("morale", 0)),
            "forces": dict(atk.get("forces", {})),
            "total": int(atk.get("total", 0)),
        },
        "defender": {
            "kingdom_name": dfn.get("kingdom_name"),
            "morale": int(dfn.get("morale", 0)),
            "forces": dict(dfn.get("forces", {})),
            "walls_level": int(dfn.get("walls_level", 0)),
            "tower_count": int(dfn.get("tower_count", 0)),
        },
        "combat_classes": wcfg.get("combat_classes", {}),
    }


def active_siege_live(
    state: dict[str, Any], *, base_dir: str | Path
) -> dict[str, Any] | None:
    bucket = _war_bucket(state)
    active = [w for w in bucket.get("active", []) if w.get("status") == "active"]
    if not active:
        return None
    return siege_live_snapshot(state, active[0], base_dir=base_dir)


def kingdom_wars_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    wcfg = load_war_config(base_dir)
    bucket = _war_bucket(state)
    charter = get_kingdom_charter(state)
    live = active_siege_live(state, base_dir=base_dir)
    return {
        "has_kingdom": charter is not None,
        "active_sieges": bucket.get("active", []),
        "siege_live": live,
        "history": bucket.get("history", [])[-10:],
        "combat_classes": wcfg.get("combat_classes", {}),
        "monster_legions": list(wcfg.get("monster_legions", {}).keys()),
        "defender_forces": defender_forces_from_charter(charter, wcfg) if charter else None,
    }


def simulate_siege_round(
    state: dict[str, Any],
    war_id: str,
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    bucket = _war_bucket(state)
    war = next((w for w in bucket.get("active", []) if w.get("war_id") == war_id), None)
    if not war:
        return {"ok": False, "error": "active siege not found"}
    if war.get("status") != "active":
        return {"ok": False, "error": "siege already ended"}
    rng = rng or random.Random()
    result = resolve_siege_round(state, war, base_dir=base_dir, rng=rng)
    return {
        "ok": True,
        "war": war,
        "lines": result.get("lines", []),
        "events": result.get("events", []),
        "round_summary": result,
    }
