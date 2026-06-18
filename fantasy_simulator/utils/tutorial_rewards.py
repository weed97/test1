"""Early-game gold path before kingdom founding — explore/investigate/rest stipends."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.kingdom_system import get_kingdom_charter
from utils.settlement_build import _party_gold, _set_party_gold


def load_tutorial_config(base_dir: str | Path) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "tutorial.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _tutorial_bucket(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("flags", {}).setdefault("tutorial", {"counts": {}})


def _action_key(action: str) -> str | None:
    lower = action.lower().strip()
    if "explore" in lower or "탐험" in action:
        return "explore"
    if lower.startswith("investigate") or lower.startswith("inspect") or "조사" in action:
        return "investigate"
    if lower == "rest" or "휴식" in action:
        return "rest"
    return None


def apply_tutorial_reward(
    state: dict[str, Any],
    action: str,
    *,
    base_dir: str | Path,
) -> list[str]:
    """Grant modest gold on field actions until kingdom is founded."""
    if get_kingdom_charter(state):
        return []
    key = _action_key(action)
    if not key:
        return []

    cfg = load_tutorial_config(base_dir)
    rdef = cfg.get("rewards", {}).get(key)
    if not rdef:
        return []

    bucket = _tutorial_bucket(state)
    counts: dict[str, int] = bucket.setdefault("counts", {})
    used = int(counts.get(key, 0))
    max_count = int(rdef.get("max_count", 0))
    if used >= max_count:
        return []

    gold_each = int(rdef.get("gold_each", 0))
    if gold_each <= 0:
        return []

    counts[key] = used + 1
    before = _party_gold(state)
    _set_party_gold(state, before + gold_each)
    label = str(rdef.get("label", key))
    return [
        f"[튜토리얼] {label} +{gold_each}G "
        f"({counts[key]}/{max_count}) · 보유 {before + gold_each}G"
    ]


def tutorial_progress_summary(
    state: dict[str, Any],
    *,
    base_dir: str | Path,
) -> dict[str, Any]:
    if get_kingdom_charter(state):
        return {"active": False}
    cfg = load_tutorial_config(base_dir)
    counts = _tutorial_bucket(state).get("counts", {})
    rewards = cfg.get("rewards", {})
    remaining: dict[str, int] = {}
    for key, rdef in rewards.items():
        max_count = int(rdef.get("max_count", 0))
        remaining[key] = max(0, max_count - int(counts.get(key, 0)))
    return {
        "active": True,
        "party_gold": _party_gold(state),
        "remaining_rewards": remaining,
        "progress_path": list(cfg.get("progress_path", [])),
    }
