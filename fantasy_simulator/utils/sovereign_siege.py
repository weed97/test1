"""Arthur coalition siege — simple net DPS tick (config in arthur_coalition.json)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_arthur_coalition_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "arthur_coalition.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_arthur_siege_math_config(base_dir: str | Path) -> dict[str, Any]:
    """Backward compat — siege block lives in arthur_coalition."""
    return load_arthur_coalition_config(base_dir)


def _sovereign_state(state: dict[str, Any], *, siege: dict[str, Any]) -> dict[str, Any]:
    hp = int(siege.get("hp_milli", 1_000_000_000))
    return state.setdefault("flags", {}).setdefault(
        "world_sovereign",
        {
            "holder_id": "npc_arthur_pendragon",
            "hp_milli": hp,
            "tier": "demigod",
            "contested": False,
            "wound_stacks": 0,
            "sovereign_break_meter": 0,
        },
    )


def coalition_net_dps_milli(*, coalition_cfg: dict[str, Any]) -> int:
    s = coalition_cfg.get("siege", {})
    return int(s.get("net_dps_milli", 40_000))


def estimate_coalition_siege_seconds(*, coalition_cfg: dict[str, Any]) -> int:
    s = coalition_cfg.get("siege", {})
    if "seconds_to_kill" in s:
        return int(s["seconds_to_kill"])
    net = coalition_net_dps_milli(coalition_cfg=coalition_cfg)
    if net <= 0:
        return 0
    return int(s.get("hp_milli", 1_000_000_000)) // net


def tick_sovereign_coalition_siege(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
    beat_seconds: float = 1.0,
) -> list[str]:
    coalition = load_arthur_coalition_config(base_dir)
    siege = coalition.get("siege", {})
    sov = _sovereign_state(state, siege=siege)
    contested = bool(
        sov.get("contested") or coalition.get("sovereign_contested", {}).get("active", False)
    )

    eco = state.setdefault("flags", {}).setdefault("ecology", {})
    growth = eco.setdefault(
        "grand_coalition_siege",
        {"strikers": int(siege.get("anchor_strikers", 300_000)) // 2500},
    )
    strikers = int(growth.get("strikers", 120))
    growth["strikers"] = min(
        int(siege.get("anchor_strikers", 300_000)),
        max(strikers, strikers + strikers // 10),
    )

    anchor_n = max(1, int(siege.get("anchor_strikers", 300_000)))
    agg_dps = (growth["strikers"] * int(siege.get("aggregate_dps_milli", 200_000))) // anchor_n
    regen = int(siege.get("regen_per_sec_milli", 160_000))
    if contested:
        regen = regen // 5
    damage = int(agg_dps * beat_seconds)
    regen_apply = int(regen * beat_seconds)
    hp_before = int(sov.get("hp_milli", siege.get("hp_milli", 1_000_000_000)))
    hp_after = max(0, min(int(siege.get("hp_milli", hp_before)), hp_before - damage + regen_apply))
    net = hp_after - hp_before

    br_add = growth["strikers"] // 1000
    br_max = int(coalition.get("sovereign_contested", {}).get("sovereign_break_max", 100_000))
    sov["hp_milli"] = hp_after
    sov["contested"] = contested
    sov["sovereign_break_meter"] = min(br_max, int(sov.get("sovereign_break_meter", 0)) + br_add)

    eco["last_sovereign_siege"] = {
        "strikers": growth["strikers"],
        "damage_milli": damage,
        "regen_milli": regen_apply,
        "net_hp_milli": net,
        "hp_milli": hp_after,
    }

    lines: list[str] = []
    if hp_after <= 0:
        lines.append(f"[주권·공성] 연합 {growth['strikers']} — 아서 HP 붕괴.")
    elif net < 0:
        lines.append(
            f"[주권·공성] 연합 {growth['strikers']} — 순피해 {abs(net) // 1000} "
            f"(합산 {agg_dps // 1000}/s, 회복 {regen // 1000}/s)."
        )
    elif growth["strikers"] > 0:
        lines.append(f"[주권·공성] 연합 {growth['strikers']} — 아서 회복 우세.")
    return lines


def sovereign_siege_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    coalition = load_arthur_coalition_config(base_dir)
    siege = coalition.get("siege", {})
    sov = state.get("flags", {}).get("world_sovereign", {})
    return {
        "holder_id": sov.get("holder_id", "npc_arthur_pendragon"),
        "hp_milli": int(sov.get("hp_milli", siege.get("hp_milli", 1_000_000_000))),
        "contested": bool(sov.get("contested")),
        "sovereign_break_meter": int(sov.get("sovereign_break_meter", 0)),
        "coalition_net_dps_milli": coalition_net_dps_milli(coalition_cfg=coalition),
        "seconds_to_kill_at_anchor": estimate_coalition_siege_seconds(coalition_cfg=coalition),
        "siege": siege,
    }
