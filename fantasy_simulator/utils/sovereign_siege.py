"""Arthur / world-sovereign siege — parallel strike sum, regen, break meter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.combat_precision import apply_mitigation_milli, load_combat_precision_config


def load_arthur_siege_math_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "arthur_siege_math.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_arthur_coalition_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "arthur_coalition.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _sovereign_state(state: dict[str, Any]) -> dict[str, Any]:
    flags = state.setdefault("flags", {})
    return flags.setdefault(
        "world_sovereign",
        {
            "holder_id": "npc_arthur_pendragon",
            "hp_milli": 1000000000,
            "tier": "demigod",
            "contested": False,
            "wound_stacks": 0,
            "sovereign_break_meter": 0,
        },
    )


def arthur_defender_snapshot(
    *,
    siege_cfg: dict[str, Any],
    coalition_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ar = siege_cfg.get("arthur", {})
    ws = (coalition_cfg or {}).get("world_sovereign", {})
    return {
        "character_level": int(ws.get("character_level", 999)),
        "weapon_mastery_level": 999,
        "defense_milli": int(ar.get("defense_milli", 100_000_000)),
        "hp_milli": int(ar.get("hp_milli", 9_999_000)),
    }


def hp_damage_from_raw_milli(
    raw_attack_milli: int,
    *,
    combat_cfg: dict[str, Any],
    siege_cfg: dict[str, Any],
) -> int:
    """Final HP damage milli after Arthur-tier mitigation and per-hit cap."""
    defender = arthur_defender_snapshot(siege_cfg=siege_cfg)
    def_m = int(defender["defense_milli"])
    return apply_mitigation_milli(int(raw_attack_milli), def_m, cfg=combat_cfg)


def wounded_regen_per_sec_milli(
    *,
    siege_cfg: dict[str, Any],
    coalition_cfg: dict[str, Any],
    wound_stacks: int = 0,
    contested: bool = False,
) -> int:
    reg = siege_cfg.get("regeneration", {})
    cap = int(reg.get("combat_cap_per_sec_milli", 200_000))
    mult = 1000
    wounded_mult = int(reg.get("wounded_regen_mult_milli", 800))
    if wound_stacks > 0:
        mult = (mult * wounded_mult) // 1000
    sc = coalition_cfg.get("sovereign_contested", {})
    if contested:
        cm = int(reg.get("contested_regen_mult_milli", sc.get("regen_multiplier_milli", 50)))
        mult = (mult * cm) // 1000
    return (cap * mult) // 1000


def estimate_net_hp_per_sec_milli(
    aggregate_raw_dps_milli: int,
    *,
    siege_cfg: dict[str, Any],
    coalition_cfg: dict[str, Any],
    combat_cfg: dict[str, Any],
    wound_stacks: int = 1,
    contested: bool = True,
) -> int:
    """Net HP/s after one second of parallel raw input vs wounded regen."""
    per_sec_hits = hp_damage_from_raw_milli(
        aggregate_raw_dps_milli, combat_cfg=combat_cfg, siege_cfg=siege_cfg
    )
    regen = wounded_regen_per_sec_milli(
        siege_cfg=siege_cfg,
        coalition_cfg=coalition_cfg,
        wound_stacks=wound_stacks,
        contested=contested,
    )
    return per_sec_hits - regen


def resolve_parallel_strikes_milli(
    strikes: list[int],
    *,
    hp_milli_before: int,
    siege_cfg: dict[str, Any],
    coalition_cfg: dict[str, Any],
    wound_stacks: int = 0,
    contested: bool = False,
    beat_seconds: float = 1.0,
) -> dict[str, Any]:
    """
    Sum simultaneous HP damage (milli), then apply one regen tick.
    Each strike value is already post-mitigation HP damage milli.
    """
    total = sum(max(0, int(s)) for s in strikes)
    max_hp = int(siege_cfg.get("arthur", {}).get("hp_milli", 9_999_000))
    wounds = int(wound_stacks)
    if total > 0:
        wounds += int(siege_cfg.get("parallel_beat", {}).get("wound_stack_per_damaged_beat", 1))
        max_w = int(
            (coalition_cfg.get("sovereign_contested") or {}).get("wound_max_stacks", 10)
        )
        if max_w <= 0:
            max_w = 10
        wounds = min(max_w, wounds)

    instant_kill = total >= hp_milli_before
    hp_after_damage = max(0, hp_milli_before - total)

    regen_rate = wounded_regen_per_sec_milli(
        siege_cfg=siege_cfg,
        coalition_cfg=coalition_cfg,
        wound_stacks=wounds,
        contested=contested,
    )
    regen_applied = 0 if instant_kill else int(regen_rate * beat_seconds)
    hp_after = 0 if instant_kill else min(max_hp, hp_after_damage + regen_applied)

    pb = siege_cfg.get("parallel_beat", {})
    break_add = len(strikes) * int(pb.get("break_meter_per_striker_milli", 100)) // 1000
    break_add += (len(strikes) // 1000) * int(pb.get("break_meter_per_1000_attackers_milli", 50_000)) // 1000
    break_max = int(coalition_cfg.get("sovereign_contested", {}).get("sovereign_break_max", 100_000))

    return {
        "strike_count": len(strikes),
        "total_damage_milli": total,
        "hp_milli_before": hp_milli_before,
        "hp_milli_after_damage": hp_after_damage,
        "regen_applied_milli": regen_applied,
        "hp_milli_after": hp_after,
        "instant_kill": instant_kill,
        "wound_stacks": wounds,
        "regen_rate_per_sec_milli": regen_rate,
        "net_hp_delta_milli": hp_after - hp_milli_before,
        "break_meter_added": break_add,
        "break_meter_max": break_max,
    }


def coalition_aggregate_dps_milli(
    striker_count: int,
    *,
    siege_cfg: dict[str, Any],
) -> int:
    """Scale anchor aggregate DPS (200/s @ 300k) by army size."""
    anchor = siege_cfg.get("coalition_siege_anchor", {})
    base_n = max(1, int(anchor.get("strikers", 300_000)))
    base_dps = int(anchor.get("aggregate_dps_milli", 200_000))
    return (int(striker_count) * base_dps) // base_n


def coalition_net_dps_milli(*, siege_cfg: dict[str, Any]) -> int:
    anchor = siege_cfg.get("coalition_siege_anchor", {})
    agg = int(anchor.get("aggregate_dps_milli", 200_000))
    regen = int(anchor.get("wounded_regen_per_sec_milli", 160_000))
    return max(0, agg - regen)


def estimate_coalition_siege_seconds(*, siege_cfg: dict[str, Any]) -> int:
    anchor = siege_cfg.get("coalition_siege_anchor", {})
    if "seconds_to_kill" in anchor:
        return int(anchor["seconds_to_kill"])
    net = coalition_net_dps_milli(siege_cfg=siege_cfg)
    if net <= 0:
        return 0
    hp = int(anchor.get("hp_milli", 1_000_000_000))
    return hp // net


def coalition_strike_batch(
    *,
    striker_count: int,
    elite_count: int,
    siege_cfg: dict[str, Any],
    combat_cfg: dict[str, Any],
    beat_seconds: float = 1.0,
) -> list[int]:
    """Macro beat: aggregate coalition DPS for one second (probabilistic swarm EV)."""
    del elite_count, combat_cfg
    dmg = int(coalition_aggregate_dps_milli(striker_count, siege_cfg=siege_cfg) * beat_seconds)
    return [dmg] if dmg > 0 else []


def tick_sovereign_coalition_siege(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    beat_seconds: float = 1.0,
) -> list[str]:
    """Macro beat: grand coalition parallel strikers vs Arthur HP + break."""
    siege_cfg = load_arthur_siege_math_config(base_dir)
    coalition_cfg = load_arthur_coalition_config(base_dir)
    combat_cfg = load_combat_precision_config(base_dir)
    sov = _sovereign_state(state)
    contested = bool(
        sov.get("contested")
        or coalition_cfg.get("sovereign_contested", {}).get("active", False)
    )

    cp = siege_cfg.get("coalition_pressure", {})
    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    growth = eco.setdefault(
        "grand_coalition_siege",
        {"strikers": int(cp.get("base_strikers_per_beat", 120))},
    )
    strikers = int(growth.get("strikers", cp.get("base_strikers_per_beat", 120)))
    growth_mult = int(cp.get("growth_mult_per_ecology_beat_milli", 1020))
    growth["strikers"] = max(strikers, (strikers * growth_mult) // 1000)

    elite_frac = int(cp.get("elite_fraction_milli", 50))
    elites = (strikers * elite_frac) // 1000
    strikes = coalition_strike_batch(
        striker_count=strikers,
        elite_count=elites,
        siege_cfg=siege_cfg,
        combat_cfg=combat_cfg,
        beat_seconds=beat_seconds,
    )

    hp_before = int(sov.get("hp_milli", siege_cfg["arthur"]["hp_milli"]))
    result = resolve_parallel_strikes_milli(
        strikes,
        hp_milli_before=hp_before,
        siege_cfg=siege_cfg,
        coalition_cfg=coalition_cfg,
        wound_stacks=int(sov.get("wound_stacks", 0)),
        contested=contested,
        beat_seconds=beat_seconds,
    )

    sov["hp_milli"] = result["hp_milli_after"]
    sov["wound_stacks"] = result["wound_stacks"]
    sov["contested"] = contested
    br = int(sov.get("sovereign_break_meter", 0)) + result["break_meter_added"]
    br_max = int(coalition_cfg.get("sovereign_contested", {}).get("sovereign_break_max", 100_000))
    sov["sovereign_break_meter"] = min(br_max, br)

    eco["last_sovereign_siege"] = {
        "strikers": strikers,
        "elites": elites,
        **{k: v for k, v in result.items() if k != "break_meter_max"},
    }

    lines: list[str] = []
    if result["instant_kill"]:
        lines.append(
            f"[주권·공성] 연합 {result['strike_count']}동시 타격 — 아서 HP 붕괴 "
            f"({result['total_damage_milli'] // 1000} 피해)."
        )
    elif result["net_hp_delta_milli"] < 0:
        lines.append(
            f"[주권·공성] 연합 {result['strike_count']}명 — 순피해 "
            f"{abs(result['net_hp_delta_milli']) // 1000} (회복 {result['regen_applied_milli'] // 1000}/s)."
        )
    elif result["strike_count"] > 0:
        lines.append(
            f"[주권·공성] 연합 {result['strike_count']}명 — 아서 회복 우세 "
            f"(+{result['net_hp_delta_milli'] // 1000} HP)."
        )
    return lines


def estimate_mob_army_net_hp_per_sec_milli(
    *,
    siege_cfg: dict[str, Any],
    combat_cfg: dict[str, Any] | None = None,
) -> int:
    """Net HP/s at coalition siege anchor (200 aggregate − 160 regen = 40)."""
    del combat_cfg
    return coalition_net_dps_milli(siege_cfg=siege_cfg)


def sovereign_siege_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    siege_cfg = load_arthur_siege_math_config(base_dir)
    coalition_cfg = load_arthur_coalition_config(base_dir)
    sov = _sovereign_state(state)
    contested = bool(sov.get("contested"))
    wounds = int(sov.get("wound_stacks", 0))
    regen = wounded_regen_per_sec_milli(
        siege_cfg=siege_cfg,
        coalition_cfg=coalition_cfg,
        wound_stacks=wounds,
        contested=contested,
    )
    anchor = siege_cfg.get("mitigation_anchor", {})
    return {
        "holder_id": sov.get("holder_id"),
        "hp_milli": int(sov.get("hp_milli", siege_cfg["arthur"]["hp_milli"])),
        "contested": contested,
        "wound_stacks": wounds,
        "regen_per_sec_milli": regen,
        "sovereign_break_meter": int(sov.get("sovereign_break_meter", 0)),
        "hits_to_kill_at_min_damage": int(anchor.get("hits_to_kill_at_min_hp_damage", 1_000_000)),
        "coalition_net_dps_milli": coalition_net_dps_milli(siege_cfg=siege_cfg),
        "seconds_to_kill_at_anchor": estimate_coalition_siege_seconds(siege_cfg=siege_cfg),
        "world_apex_at_raw_cap": int(siege_cfg.get("world_apex_attackers", {}).get("count_at_raw_cap", 10)),
    }
