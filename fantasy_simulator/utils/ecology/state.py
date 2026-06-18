"""Ecology flag bucket — shared state namespace without field_agents import cycles."""

from __future__ import annotations

from typing import Any


def ecology_flags(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("flags", {}).setdefault("ecology", {})
