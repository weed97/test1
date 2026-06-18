"""Normalize player action strings for gather / tutorial reward lookups."""

from __future__ import annotations


def action_key(action: str) -> str | None:
    lower = action.lower().strip()
    if "explore" in lower or "탐험" in action:
        return "explore"
    if lower.startswith("investigate") or lower.startswith("inspect") or "조사" in action:
        return "investigate"
    if lower == "rest" or "휴식" in action:
        return "rest"
    return None
