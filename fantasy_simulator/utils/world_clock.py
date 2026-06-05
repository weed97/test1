"""In-world clock — minute_of_day sync with legacy time_of_day cycles."""

from __future__ import annotations

from typing import Any

MINUTES_PER_DAY = 1440

# Default clock anchors when migrating legacy saves (local solar time).
_DEFAULT_MINUTE_BY_PERIOD: dict[str, int] = {
    "morning": 8 * 60,
    "afternoon": 14 * 60,
    "evening": 18 * 60,
    "night": 22 * 60,
}


def ensure_world_clock(world: dict[str, Any]) -> None:
    """Ensure world has minute_of_day aligned with time_of_day."""
    if "minute_of_day" in world:
        world["minute_of_day"] = int(world["minute_of_day"]) % MINUTES_PER_DAY
        world["time_of_day"] = minute_to_time_of_day(world["minute_of_day"])
        return
    raw = world.get("time_of_day", "morning")
    world["minute_of_day"] = _DEFAULT_MINUTE_BY_PERIOD.get(raw, _DEFAULT_MINUTE_BY_PERIOD["afternoon"])


def minute_to_time_of_day(minute: int) -> str:
    """Map minute-of-day to legacy four-part cycle."""
    m = int(minute) % MINUTES_PER_DAY
    if 360 <= m < 720:
        return "morning"
    if 720 <= m < 1020:
        return "afternoon"
    if 1020 <= m < 1260:
        return "evening"
    return "night"


def format_clock(minute: int) -> str:
    """HH:MM in-world clock label."""
    m = int(minute) % MINUTES_PER_DAY
    return f"{m // 60:02d}:{m % 60:02d}"


def advance_world_minutes(world: dict[str, Any], minutes: int) -> str:
    """Advance in-world clock; return updated time_of_day label."""
    ensure_world_clock(world)
    delta = max(0, int(minutes))
    if delta == 0:
        return world.get("time_of_day", "afternoon")

    current = int(world["minute_of_day"])
    total = current + delta
    days_added = total // MINUTES_PER_DAY
    world["minute_of_day"] = total % MINUTES_PER_DAY
    if days_added:
        world["day"] = int(world.get("day", 1)) + days_added
    world["time_of_day"] = minute_to_time_of_day(world["minute_of_day"])
    return world["time_of_day"]


def advance_to_morning(world: dict[str, Any]) -> str:
    """Fast-forward rest/sleep until next morning (06:00)."""
    ensure_world_clock(world)
    target = _DEFAULT_MINUTE_BY_PERIOD["morning"]
    current = int(world["minute_of_day"])
    if current < target:
        delta = target - current
    else:
        delta = MINUTES_PER_DAY - current + target
    return advance_world_minutes(world, delta)
