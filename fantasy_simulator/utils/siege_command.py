"""Siege command chain — up to 5 commanders per side, doctrine, chain collapse."""

from __future__ import annotations

import json
import random
import uuid
from pathlib import Path
from typing import Any

from utils.kingdom_system import get_kingdom_charter, load_kingdom_config


def load_command_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "siege_command.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _commander_block(war: dict[str, Any], side: str) -> dict[str, Any]:
    cmd = war.setdefault("command", {})
    return cmd.setdefault(
        side,
        {
            "doctrine": "coordinate_defense" if side == "defender" else "focus_barrier",
            "posture": "behind_wall" if side == "defender" else "forward_command",
            "commanders": [],
            "command_chain_intact": True,
            "autonomous": False,
        },
    )


def _alive_commanders(block: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in block.get("commanders", []) if c.get("alive", True)]


def command_chain_intact(block: dict[str, Any]) -> bool:
    alive = _alive_commanders(block)
    return bool(alive) and bool(block.get("command_chain_intact", True))


def _kingdom_support_mult(charter: dict[str, Any], ccfg: dict[str, Any]) -> float:
    base = float(ccfg.get("commander_base", {}).get("kingdom_support_mult", 1.35))
    interior = charter.get("interior", {})
    fort = charter.get("fortifications", {})
    bonus = 0.0
    bonus += int(interior.get("city_level", 0)) * 0.04
    bonus += int(fort.get("barrier_ritual_level", fort.get("ritual_level", 0))) * 0.06
    bonus += int(charter.get("military", {}).get("elite", 0)) * 0.01
    return base + bonus


def build_kingdom_commander(
    *,
    rank: int,
    title: str,
    charter: dict[str, Any],
    kcfg: dict[str, Any],
    ccfg: dict[str, Any],
) -> dict[str, Any]:
    """Single defender commander — highest HP/DEF, kingdom-boosted."""
    cbase = ccfg.get("commander_base", {})
    units = kcfg.get("military", {}).get("units", {})
    elite_def = int(units.get("elite", {}).get("defense", 28))
    guard_def = int(units.get("guard", {}).get("defense", 18))
    mil = charter.get("military", {})
    elites = int(mil.get("elite", 0))
    walls = int(charter.get("fortifications", {}).get("walls_level", 0))
    city = int(charter.get("interior", {}).get("city_level", 0))
    ritual = int(charter.get("fortifications", {}).get("barrier_ritual_level", 0))
    support = _kingdom_support_mult(charter, ccfg)

    hp = int(cbase.get("hp", 900))
    hp += elites * int(cbase.get("hp_per_elite_in_roster", 55))
    hp += city * int(cbase.get("hp_per_city_level", 80))
    hp += ritual * int(cbase.get("hp_per_barrier_ritual", 120))
    hp = int(hp * support * (1.0 + (5 - rank) * 0.08))

    defense = int(cbase.get("defense", 130))
    defense += max(elite_def, guard_def) + elites * 2
    defense += walls * int(cbase.get("defense_per_wall_level", 18))
    defense = int(defense * support)

    attack = int(cbase.get("attack", 42)) + rank * 3 + elites

    return {
        "id": f"def_cmd_{uuid.uuid4().hex[:6]}",
        "name": title,
        "rank": rank,
        "side": "defender",
        "hp": hp,
        "max_hp": hp,
        "defense": defense,
        "attack": attack,
        "alive": True,
        "protected_by_kingdom": rank <= 2,
        "posture_depth": 1,
    }


def ensure_kingdom_commander_roster(
    charter: dict[str, Any], *, base_dir: str | Path
) -> list[dict[str, Any]]:
    """Ensure charter has 5 commanders in roster (highest stat units)."""
    ccfg = load_command_config(base_dir)
    kcfg = load_kingdom_config(base_dir)
    roster = charter.setdefault("commanders", {}).setdefault("roster", [])
    titles = list(ccfg.get("commander_titles", []))
    size = int(ccfg.get("roster_size", 5))
    while len(roster) < size:
        rank = len(roster) + 1
        title = titles[len(roster)] if len(roster) < len(titles) else f"지휘관 {rank}"
        roster.append(
            build_kingdom_commander(
                rank=rank,
                title=title,
                charter=charter,
                kcfg=kcfg,
                ccfg=ccfg,
            )
        )
    return roster[:size]


def build_attacker_commanders(
    attacker: dict[str, Any],
    *,
    ccfg: dict[str, Any],
    rng: random.Random,
) -> list[dict[str, Any]]:
    acfg = ccfg.get("attacker_commander", {})
    legion = int(attacker.get("total", 60))
    hp_base = int(acfg.get("hp_base", 650)) + legion * int(acfg.get("hp_per_legion_size", 4))
    labels = ["군단장", "무투장", "주술사장", "돌격대장", "야수왕"]
    out: list[dict[str, Any]] = []
    for i, title in enumerate(labels[: int(ccfg.get("max_fielded_per_side", 5))]):
        rank = i + 1
        hp = int(hp_base * (1.0 - i * 0.12) * rng.uniform(0.92, 1.08))
        defense = int(acfg.get("defense_base", 85) + rank * 8)
        out.append(
            {
                "id": f"atk_cmd_{uuid.uuid4().hex[:6]}",
                "name": f"{attacker.get('label', '군단')} {title}",
                "rank": rank,
                "side": "attacker",
                "hp": hp,
                "max_hp": hp,
                "defense": defense,
                "attack": 38 + rank * 5,
                "alive": True,
                "protected_by_kingdom": False,
                "posture_depth": 0,
            }
        )
    return out


def init_war_command(
    war: dict[str, Any],
    charter: dict[str, Any],
    *,
    base_dir: str | Path,
    rng: random.Random,
) -> None:
    ccfg = load_command_config(base_dir)
    roster = ensure_kingdom_commander_roster(charter, base_dir=base_dir)
    def_block = _commander_block(war, "defender")
    def_block["doctrine"] = "protect_commanders"
    def_block["posture"] = "behind_wall"
    def_block["commanders"] = [dict(c) for c in roster[: int(ccfg.get("max_fielded_per_side", 5))]]
    for c in def_block["commanders"]:
        c["side"] = "defender"
        c["alive"] = True

    atk_block = _commander_block(war, "attacker")
    goal = str(war.get("casus_belli", "plunder"))
    atk_block["doctrine"] = {
        "plunder": "focus_barrier",
        "decapitation": "focus_commander",
        "breach": "focus_gate",
    }.get(goal, "focus_barrier")
    atk_block["posture"] = "forward_command"
    atk_block["commanders"] = build_attacker_commanders(
        war.get("attacker", {}), ccfg=ccfg, rng=rng
    )
    atk_block["command_chain_intact"] = True
    atk_block["autonomous"] = False
    def_block["command_chain_intact"] = True
    def_block["autonomous"] = False


def _set_side_siege_command(
    war: dict[str, Any],
    *,
    side: str,
    doctrine: str,
    posture: str | None,
    base_dir: str | Path,
) -> dict[str, Any]:
    if war.get("status") != "active":
        return {"ok": False, "error": "공성전이 활성 상태가 아닙니다"}
    ccfg = load_command_config(base_dir)
    doctrines = ccfg.get("doctrines", {})
    if doctrine not in doctrines:
        return {"ok": False, "error": f"알 수 없는 교리: {doctrine}"}
    ddef = doctrines[doctrine]
    expected = "defender" if side == "defender" else "attacker"
    if ddef.get("side") != expected:
        return {"ok": False, "error": f"{expected} 교리만 설정할 수 있습니다"}
    block = _commander_block(war, side)
    if not command_chain_intact(block):
        return {"ok": False, "error": "지휘관 전멸 — 명령체계 붕괴, 단독 교전 중"}
    block["doctrine"] = doctrine
    if posture:
        if posture not in ccfg.get("postures", {}):
            return {"ok": False, "error": f"알 수 없는 지휘 위치: {posture}"}
        block["posture"] = posture
        depth = int(ccfg["postures"][posture].get("depth", 1))
        for c in block.get("commanders", []):
            if c.get("alive", True):
                c["posture_depth"] = depth
    return {
        "ok": True,
        "side": side,
        "doctrine": doctrine,
        "posture": block.get("posture"),
        "label": ddef.get("label", doctrine),
    }


def set_defender_siege_command(
    war: dict[str, Any],
    *,
    doctrine: str,
    posture: str | None = None,
    base_dir: str | Path,
) -> dict[str, Any]:
    return _set_side_siege_command(
        war, side="defender", doctrine=doctrine, posture=posture, base_dir=base_dir
    )


def set_attacker_siege_command(
    war: dict[str, Any],
    *,
    doctrine: str,
    posture: str | None = None,
    base_dir: str | Path,
) -> dict[str, Any]:
    return _set_side_siege_command(
        war, side="attacker", doctrine=doctrine, posture=posture, base_dir=base_dir
    )


def _doctrine_weights(
    block: dict[str, Any],
    ccfg: dict[str, Any],
    *,
    rng: random.Random,
) -> dict[str, float]:
    lost = ccfg.get("command_lost", {})
    if block.get("autonomous") or not command_chain_intact(block):
        base = rng.uniform(0.6, 1.4)
        return {
            "barrier_weight": base * rng.uniform(0.7, 1.3),
            "gate_weight": rng.uniform(0.5, 1.5),
            "commander_snipe_weight": rng.uniform(0.4, 1.6) * float(lost.get("autonomous_aggression", 1.15)),
            "coordination": 1.0 - float(lost.get("attack_coordination_penalty", 0.35)),
        }
    doctrine_id = str(block.get("doctrine", "focus_barrier"))
    ddef = ccfg.get("doctrines", {}).get(doctrine_id, {})
    posture_id = str(block.get("posture", "forward_command"))
    posture = ccfg.get("postures", {}).get(posture_id, {})
    coord = float(ddef.get("coordination", 1.0)) * (1.0 + float(posture.get("command_effectiveness", 0)))
    return {
        "barrier_weight": float(ddef.get("barrier_weight", 1.0)),
        "gate_weight": float(ddef.get("gate_weight", 1.0)),
        "commander_snipe_weight": float(ddef.get("commander_snipe_weight", 0.5)),
        "bodyguard_mult": float(ddef.get("bodyguard_mult", 1.0)),
        "coordination": max(0.35, coord),
    }


def _apply_commander_damage(
    commanders: list[dict[str, Any]],
    raw_damage: int,
    *,
    snipe_resistance: float,
    bodyguard_mult: float,
    rng: random.Random,
    ccfg: dict[str, Any] | None = None,
) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (damage_dealt, killed_commanders, events)."""
    alive = [c for c in commanders if c.get("alive", True)]
    if not alive or raw_damage <= 0:
        return 0, [], []
    target = min(alive, key=lambda c: int(c.get("rank", 99)))
    if not target.get("protected_by_kingdom"):
        target = rng.choice(alive)
    combat_cfg = (ccfg or {}).get("combat", {})
    def_div = float(combat_cfg.get("defense_divisor", 88))
    min_hit = int(combat_cfg.get("min_snipe_damage", 28))
    resist = max(0.1, 1.0 - snipe_resistance)
    guard = bodyguard_mult if target.get("protected_by_kingdom") else 1.0
    scaled = raw_damage * resist / max(1.0, int(target.get("defense", 1)) / def_div) / guard
    mitigated = max(min_hit, int(scaled))
    target["hp"] = int(target.get("hp", 0)) - mitigated
    events: list[dict[str, Any]] = [
        {
            "kind": "commander_hit",
            "side": target.get("side"),
            "commander_id": target.get("id"),
            "commander_name": target.get("name"),
            "damage": mitigated,
            "hp_remaining": max(0, int(target.get("hp", 0))),
            "text": f"지휘관 {target.get('name')} 피격 (-{mitigated})",
        }
    ]
    killed: list[dict[str, Any]] = []
    if int(target.get("hp", 0)) <= 0:
        target["alive"] = False
        target["hp"] = 0
        killed.append(target)
        events.append(
            {
                "kind": "commander_fall",
                "side": target.get("side"),
                "commander_id": target.get("id"),
                "commander_name": target.get("name"),
                "text": f"☠ 지휘관 {target.get('name')} 전사 — 명령 전달 두절 위험",
            }
        )
    return mitigated, killed, events


def _check_chain_collapse(
    block: dict[str, Any],
    ccfg: dict[str, Any],
    side_label: str,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    alive = _alive_commanders(block)
    if not alive and not block.get("autonomous"):
        block["command_chain_intact"] = False
        block["autonomous"] = True
        loss = int(ccfg.get("command_lost", {}).get("morale_loss", 20))
        events.append(
            {
                "kind": "command_chain_lost",
                "side": block.get("commanders", [{}])[0].get("side", "attacker"),
                "text": f"[{side_label}] 지휘관 전멸 — 명령체계 붕괴, 부대가 단독 판단으로 교전",
                "morale_loss": loss,
            }
        )
    elif alive and not block.get("command_chain_intact"):
        supreme = min(alive, key=lambda c: int(c.get("rank", 99)))
        if int(supreme.get("rank", 99)) > 1:
            block["command_chain_intact"] = True
            events.append(
                {
                    "kind": "command_chain_restored",
                    "side": supreme.get("side"),
                    "text": f"부관 {supreme.get('name')}이(가) 잔여 지휘권을 승계",
                }
            )
    return events


def resolve_command_round(
    war: dict[str, Any],
    *,
    net: int,
    atk_power: int,
    def_power: int,
    base_dir: str | Path,
    rng: random.Random,
    sim_t0_ms: int = 0,
    stagger_ms: int = 90,
) -> dict[str, Any]:
    """Apply doctrine targeting, commander damage, chain collapse for one round."""
    ccfg = load_command_config(base_dir)
    cmd = war.setdefault("command", {})
    atk_block = cmd.get("attacker", {})
    def_block = cmd.get("defender", {})
    events: list[dict[str, Any]] = []
    lines: list[str] = []
    barrier_mult = 1.0
    gate_stress = 0
    coordination_def_mult = 1.0

    atk_w = _doctrine_weights(atk_block, ccfg, rng=rng)
    def_w = _doctrine_weights(def_block, ccfg, rng=rng)

    if atk_block.get("autonomous"):
        lines.append("  공격군: 명령체계 없음 — 각 부대 단독 판단")
    else:
        lines.append(
            f"  공격 지휘: {ccfg.get('doctrines', {}).get(atk_block.get('doctrine'), {}).get('label', '?')}"
        )
    if def_block.get("autonomous"):
        lines.append("  수성군: 명령체계 붕괴 — 성벽별 자율 방어")
        coordination_def_mult -= float(ccfg.get("command_lost", {}).get("defense_coordination_penalty", 0.38))
    else:
        lines.append(
            f"  수성 지휘: {ccfg.get('doctrines', {}).get(def_block.get('doctrine'), {}).get('label', '?')} "
            f"({ccfg.get('postures', {}).get(def_block.get('posture'), {}).get('label', '')})"
        )

    if net > 0:
        total_w = max(
            0.1,
            atk_w["barrier_weight"] + atk_w["gate_weight"] + atk_w["commander_snipe_weight"],
        )
        barrier_mult = 0.15 * (atk_w["barrier_weight"] / total_w) * float(atk_w["coordination"])
        barrier_mult = max(0.05, barrier_mult * (1.0 + net / max(1, atk_power) * 0.1))

        snipe_net = float(ccfg.get("combat", {}).get("snipe_net_factor", 0.58))
        snipe_pool = int(net * atk_w["commander_snipe_weight"] / total_w * snipe_net)
        if snipe_pool > 0 and def_block.get("commanders"):
            posture = ccfg.get("postures", {}).get(str(def_block.get("posture", "behind_wall")), {})
            snipe_res = float(posture.get("snipe_resistance", 0.5))
            if snipe_res > 0.55:
                lines.append("  적 지휘관이 성벽 깊숙이 숨어 암살 전략 효율 저하")
                snipe_pool = int(snipe_pool * (1.0 - snipe_res * 0.65))
            bodyguard = float(def_w.get("bodyguard_mult", 1.0))
            _, killed, evs = _apply_commander_damage(
                def_block.get("commanders", []),
                snipe_pool,
                snipe_resistance=snipe_res,
                bodyguard_mult=bodyguard,
                rng=rng,
                ccfg=ccfg,
            )
            for i, ev in enumerate(evs):
                ev["t_ms"] = sim_t0_ms + stagger_ms * (i + 1)
            events.extend(evs)
            if killed:
                war["defender"]["morale"] = max(
                    0, int(war["defender"].get("morale", 80)) - 8 * len(killed)
                )

        gate_stress = int(net * atk_w["gate_weight"] / total_w * 0.12)
        if gate_stress > 0:
            lines.append(f"  성문 압박 +{gate_stress}")
    else:
        repel = abs(net)
        counter_snipe = int(repel * def_w.get("commander_snipe_weight", 0.3) * 0.15)
        if counter_snipe > 0 and def_block.get("autonomous"):
            counter_snipe = int(counter_snipe * 0.5)
        if counter_snipe > 0 and atk_block.get("commanders"):
            posture = ccfg.get("postures", {}).get(str(atk_block.get("posture", "forward_command")), {})
            _, killed, evs = _apply_commander_damage(
                atk_block.get("commanders", []),
                counter_snipe,
                snipe_resistance=float(posture.get("snipe_resistance", 0)),
                bodyguard_mult=1.0,
                rng=rng,
                ccfg=ccfg,
            )
            for i, ev in enumerate(evs):
                ev["t_ms"] = sim_t0_ms + stagger_ms * (i + 3)
            events.extend(evs)
            if killed:
                war["attacker"]["morale"] = max(
                    0, int(war["attacker"].get("morale", 75)) - 10 * len(killed)
                )

    events.extend(_check_chain_collapse(atk_block, ccfg, "공격군"))
    events.extend(_check_chain_collapse(def_block, ccfg, "수성군"))

    for ev in events:
        if ev.get("kind") == "command_chain_lost":
            side = ev.get("side")
            bucket = atk_block if side == "attacker" else def_block
            loss = int(ev.get("morale_loss", 20))
            if side == "attacker":
                war["attacker"]["morale"] = max(0, int(war["attacker"].get("morale", 0)) - loss)
            else:
                war["defender"]["morale"] = max(0, int(war["defender"].get("morale", 0)) - loss)
                coordination_def_mult -= 0.15

    return {
        "barrier_damage_mult": barrier_mult,
        "gate_stress": gate_stress,
        "defense_coordination_mult": max(0.4, coordination_def_mult),
        "events": events,
        "lines": lines,
    }


def command_live_view(war: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    ccfg = load_command_config(base_dir)
    cmd = war.get("command", {})

    def _side_view(side: str) -> dict[str, Any]:
        block = cmd.get(side, {})
        alive = _alive_commanders(block)
        supreme = min(alive, key=lambda c: int(c.get("rank", 99))) if alive else None
        return {
            "doctrine": block.get("doctrine"),
            "doctrine_label": ccfg.get("doctrines", {})
            .get(str(block.get("doctrine")), {})
            .get("label"),
            "posture": block.get("posture"),
            "posture_label": ccfg.get("postures", {})
            .get(str(block.get("posture")), {})
            .get("label"),
            "command_chain_intact": command_chain_intact(block),
            "autonomous": bool(block.get("autonomous")),
            "commanders": [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "rank": c.get("rank"),
                    "hp": c.get("hp"),
                    "max_hp": c.get("max_hp"),
                    "alive": c.get("alive", True),
                    "protected_by_kingdom": c.get("protected_by_kingdom", False),
                    "posture_depth": c.get("posture_depth", 1),
                }
                for c in block.get("commanders", [])
            ],
            "supreme_commander": supreme.get("name") if supreme else None,
            "alive_count": len(alive),
        }

    return {
        "attacker": _side_view("attacker"),
        "defender": _side_view("defender"),
        "doctrines_available": {
            k: v.get("label")
            for k, v in ccfg.get("doctrines", {}).items()
            if v.get("side") == "defender"
        },
        "postures_available": {
            k: v.get("label") for k, v in ccfg.get("postures", {}).items()
        },
    }


def kingdom_commander_roster_status(
    state: dict[str, Any], *, base_dir: str | Path
) -> dict[str, Any]:
    charter = get_kingdom_charter(state)
    if not charter:
        return {"has_roster": False, "roster": []}
    ccfg = load_command_config(base_dir)
    roster = ensure_kingdom_commander_roster(charter, base_dir=base_dir)
    return {
        "has_roster": True,
        "roster_size": int(ccfg.get("roster_size", 5)),
        "roster": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "rank": c.get("rank"),
                "hp": c.get("max_hp"),
                "defense": c.get("defense"),
                "attack": c.get("attack"),
                "protected_by_kingdom": c.get("protected_by_kingdom"),
            }
            for c in roster
        ],
    }
