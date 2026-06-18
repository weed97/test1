"""Zone-limited food and materials — depleted pools push players to dangerous regions."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from utils.settlement_build import get_player_settlement
from utils.spatial import resolve_zone_from_world


def load_regional_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "regional_resources.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _pools(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("flags", {}).setdefault("ecology", {}).setdefault(
        "regional_pools", {}
    )


def zone_id_from_state(state: dict[str, Any]) -> str:
    world = state.get("world", {})
    return resolve_zone_from_world(world)


def zone_profile(zone_id: str, *, base_dir: str | Path) -> dict[str, Any]:
    cfg = load_regional_config(base_dir)
    return dict(cfg.get("zones", {}).get(zone_id, {}))


def ensure_zone_pools(state: dict[str, Any], zone_id: str, *, base_dir: str | Path) -> dict[str, int]:
    pools = _pools(state)
    if zone_id in pools:
        return pools[zone_id]
    profile = zone_profile(zone_id, base_dir=base_dir)
    init: dict[str, int] = {}
    for res, rdef in profile.get("resources", {}).items():
        init[res] = int(rdef.get("max", 0))
    pools[zone_id] = init
    return init


def tick_regional_regen(state: dict[str, Any], *, base_dir: str | Path) -> list[str]:
    cfg = load_regional_config(base_dir)
    pools = _pools(state)
    lines: list[str] = []
    for zone_id, zdef in cfg.get("zones", {}).items():
        bucket = ensure_zone_pools(state, zone_id, base_dir=base_dir)
        for res, rdef in zdef.get("resources", {}).items():
            regen = int(rdef.get("regen_per_beat", 0))
            if regen <= 0:
                continue
            cap = int(rdef.get("max", 0))
            before = int(bucket.get(res, 0))
            after = min(cap, before + regen)
            if after > before:
                bucket[res] = after
    return lines


def regional_status(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    zone_id = zone_id_from_state(state)
    profile = zone_profile(zone_id, base_dir=base_dir)
    bucket = ensure_zone_pools(state, zone_id, base_dir=base_dir)
    caps = {
        res: int(rdef.get("max", 0))
        for res, rdef in profile.get("resources", {}).items()
    }
    return {
        "zone_id": zone_id,
        "danger_level": int(profile.get("danger_level", 1)),
        "danger_label": profile.get("danger_label", "?"),
        "remaining": dict(bucket),
        "max": caps,
    }


def _action_key(action: str) -> str | None:
    lower = action.lower().strip()
    if "explore" in lower or "탐험" in action:
        return "explore"
    if lower.startswith("investigate") or lower.startswith("inspect") or "조사" in action:
        return "investigate"
    if lower == "rest" or "휴식" in action:
        return "rest"
    return None


def try_regional_gather(
    state: dict[str, Any],
    action: str,
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
) -> list[str]:
    """Gather materials/food from the current zone pool into player stockpile."""
    key = _action_key(action)
    if not key:
        return []

    cfg = load_regional_config(base_dir)
    zone_id = zone_id_from_state(state)
    profile = zone_profile(zone_id, base_dir=base_dir)
    if not profile:
        return []

    bucket = ensure_zone_pools(state, zone_id, base_dir=base_dir)
    ps = get_player_settlement(state)
    stock = ps.setdefault("stockpile", {})
    lines: list[str] = []
    rng = rng or random.Random()

    for res, rdef in profile.get("resources", {}).items():
        gather = rdef.get("gather", {})
        amount = int(gather.get(key, 0))
        if amount <= 0:
            continue
        left = int(bucket.get(res, 0))
        if left <= 0:
            msg = cfg.get("depleted_message", "{resource} 고갈").format(resource=res)
            if f"[{zone_id}]" not in " ".join(lines):
                lines.append(f"[{profile.get('danger_label', zone_id)}] {msg}")
            continue
        take = min(amount, left)
        if key == "explore" and rng.random() < 0.25:
            take = max(0, take - 1)
        if take <= 0:
            continue
        bucket[res] = left - take
        stock[res] = int(stock.get(res, 0)) + take
        lines.append(
            f"[채집·{profile.get('danger_label', zone_id)}] {res} +{take} "
            f"(지역 잔여 {bucket[res]}/{rdef.get('max', '?')})"
        )

    return lines


def combat_loot_for_zone(
    zone_id: str,
    *,
    base_dir: str | Path,
    rng: random.Random | None = None,
    threat_level: int = 1,
) -> tuple[int, int]:
    """Return (copper, silver) loot for a victory in this zone."""
    cfg = load_regional_config(base_dir)
    profile = zone_profile(zone_id, base_dir=base_dir)
    loot_cfg = cfg.get("combat_loot", {})
    danger = int(profile.get("danger_level", 1))
    mult = float(profile.get("loot_copper_mult", 1.0))
    rng = rng or random.Random()
    base = int(loot_cfg.get("base_copper", 18))
    per = int(loot_cfg.get("copper_per_danger_level", 14))
    copper = int(
        (base + per * danger) * mult * max(1, threat_level) * rng.uniform(0.85, 1.15)
    )
    silver = 0
    chance = float(profile.get("loot_silver_chance", 0.0))
    every = int(loot_cfg.get("silver_every_danger", 3))
    if danger >= every and rng.random() < chance:
        silver = 1 + danger // every
    return max(1, copper), silver
