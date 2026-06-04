"""World tension tiers — global crisis level and event modifiers."""

from __future__ import annotations

from typing import Any

TIERS: list[dict[str, Any]] = [
    {"id": "calm", "min": 0, "max": 24, "label_ko": "평화", "event_weight": 0.8, "trade_bonus": 0.05},
    {"id": "uneasy", "min": 25, "max": 49, "label_ko": "불안", "event_weight": 1.0, "trade_bonus": 0.0},
    {"id": "tense", "min": 50, "max": 74, "label_ko": "긴장", "event_weight": 1.25, "trade_bonus": -0.1},
    {"id": "crisis", "min": 75, "max": 100, "label_ko": "위기", "event_weight": 1.5, "trade_bonus": -0.25},
]


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def get_tension(state: dict[str, Any]) -> int:
    return int(state.get("world", {}).get("tension", 42))


def set_tension(state: dict[str, Any], value: int) -> int:
    world = state.setdefault("world", {})
    v = _clamp(int(value))
    world["tension"] = v
    return v


def adjust_tension(state: dict[str, Any], delta: int) -> int:
    return set_tension(state, get_tension(state) + int(delta))


def tier_for_value(value: int) -> dict[str, Any]:
    v = _clamp(int(value))
    for tier in TIERS:
        if tier["min"] <= v <= tier["max"]:
            return tier
    return TIERS[1]


def get_tier(state: dict[str, Any]) -> dict[str, Any]:
    return tier_for_value(get_tension(state))


def event_weight_multiplier(state: dict[str, Any], seed: dict[str, Any] | None = None) -> float:
    """Scale random event weights by tension tier and optional seed tags."""
    mult = float(get_tier(state)["event_weight"])
    if not seed:
        return mult
    tags = set(seed.get("tension_tags") or [])
    tier_id = get_tier(state)["id"]
    if "peace" in tags and tier_id == "calm":
        mult *= 1.4
    if "crisis" in tags and tier_id in ("tense", "crisis"):
        mult *= 1.3
    if "horror" in tags and tier_id in ("tense", "crisis"):
        mult *= 1.2
    return mult


def passive_drift(state: dict[str, Any], *, rng: Any | None = None) -> tuple[int, str | None]:
    """Small per-turn tension drift from world state."""
    tension = get_tension(state)
    flags = state.get("flags", {})
    delta = 0
    note: str | None = None

    if flags.get("world_seal_broken"):
        delta += 2
        note = "봉인 파괴 여파로 긴장도 상승"
    elif flags.get("world_seal_reinforced"):
        delta -= 1

    quests = flags.get("quests", {})
    if quests.get("active") == "smoke_on_the_mountain" and int(quests.get("stage", 1)) >= 3:
        delta += 1

    faction_rep = flags.get("faction_reputation", {})
    if int(faction_rep.get("void_circle", 0)) >= 30:
        delta += 1
    if int(faction_rep.get("seal_wardens", 0)) >= 30:
        delta -= 1

    if rng is not None and delta == 0:
        roll = rng.randint(-1, 2)
        if roll > 0 and tension < 80:
            delta = roll
        elif roll < 0 and tension > 15:
            delta = roll

    if delta:
        new_val = adjust_tension(state, delta)
        if note is None and delta > 0:
            note = f"세계 긴장도 +{delta} ({tier_for_value(new_val)['label_ko']})"
        elif note is None and delta < 0:
            note = f"세계 긴장도 {delta} ({tier_for_value(new_val)['label_ko']})"
        return delta, note
    return 0, None


def format_tension_line(state: dict[str, Any]) -> str:
    t = get_tension(state)
    tier = tier_for_value(t)
    return f"Tension: {t}/100 ({tier['label_ko']})"
