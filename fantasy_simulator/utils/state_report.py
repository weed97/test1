"""Human-readable state summaries for CLI (presentation layer, no persistence)."""

from __future__ import annotations

from typing import Any

from utils.state_loader import StateLoader, event_entries


def format_summary(state: dict[str, Any]) -> str:
    """One-page status summary."""
    world = state.get("world", {})
    lines = [
        f"{world.get('name', 'Eldoria')} — Day {world.get('day', '?')} ({world.get('time_of_day', '?')})",
        f"Location: {world.get('location', '?')}",
        f"Weather: {world.get('weather', '?')} | Tension: {world.get('tension', 0)}",
        f"Gold: {state.get('inventory', {}).get('party_gold', 0)}",
    ]
    party = state.get("party", [])
    if party:
        lines.append("Party: " + ", ".join(party))
    recent = event_entries(state)
    if recent:
        lines.append("Recent: " + recent[-1].get("summary", ""))
    return "\n".join(lines)


def format_status_report(
    state: dict[str, Any],
    loader: StateLoader,
    *,
    event_engine: Any | None = None,
    mode: str = "rule",
) -> str:
    """Full status screen for CLI / interactive mode."""
    world = state.get("world", {})
    lines = [
        f"=== {world.get('name', 'Eldoria')} | Day {world.get('day', '?')} ({world.get('time_of_day', '?')}) ===",
        f"모드: {mode} | 저장: state/ (sharded)",
        format_summary(state),
        "",
        "파티:",
    ]
    for cid in state.get("party", []):
        c = loader.load_character(cid)
        if state.get("combat") and cid in state["combat"]["allies"]:
            stats = state["combat"]["allies"][cid]["stats"]
        else:
            stats = c["stats"]
        lines.append(
            f"  - {c['name']}: HP {stats['hp']}/{stats['max_hp']} "
            f"MP {stats['mana']}/{stats['max_mana']}"
        )
    if state.get("combat"):
        lines.append("(전투 진행 중)")
    rep = state.get("flags", {}).get("reputation", {})
    if rep:
        lines.extend(["", "평판:"])
        for k, v in sorted(rep.items()):
            lines.append(f"  - {k}: {v}")
    if event_engine:
        lines.extend(["", f"퀘스트: {event_engine.show_quest_status(state)}"])
    recent = event_entries(state)
    if recent:
        lines.extend(["", "최근 이벤트:"])
        for ev in recent[-5:]:
            lines.append(f"  [{ev.get('type')}] {ev.get('summary')}")
    return "\n".join(lines)
