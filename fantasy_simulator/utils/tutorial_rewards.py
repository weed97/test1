"""Early-game copper stipends — no free gold; silver/gold come from danger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.currency import format_wallet, get_wallet, grant, wallet_summary
from utils.kingdom_system import get_kingdom_charter


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
    """Grant small copper on field actions until kingdom is founded."""
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

    copper = int(rdef.get("copper_each", 0))
    silver = int(rdef.get("silver_each", 0))
    if copper <= 0 and silver <= 0:
        return []

    counts[key] = used + 1
    grant(state, copper=copper, silver=silver, gold=0, base_dir=base_dir)
    label = str(rdef.get("label", key))
    wallet = get_wallet(state, base_dir=base_dir)
    parts = []
    if copper:
        parts.append(f"+{copper}쿠퍼")
    if silver:
        parts.append(f"+{silver}실버")
    return [
        f"[튜토리얼] {label} {' '.join(parts)} "
        f"({counts[key]}/{max_count}) · 보유 {format_wallet(wallet, base_dir=base_dir)}"
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
    money = wallet_summary(state, base_dir=base_dir)
    return {
        "active": True,
        "wallet": money["wallet"],
        "wallet_formatted": money["formatted"],
        "party_gold": money["party_gold"],
        "remaining_rewards": remaining,
        "progress_path": list(cfg.get("progress_path", [])),
    }
