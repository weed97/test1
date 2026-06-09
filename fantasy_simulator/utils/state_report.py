"""Human-readable state summaries for CLI (presentation layer, no persistence)."""

from __future__ import annotations

from typing import Any

from utils.state_loader import StateLoader, event_entries
from utils.world_tension import format_tension_line


def format_summary(state: dict[str, Any]) -> str:
    """One-page status summary."""
    world = state.get("world", {})
    clock = ""
    if "minute_of_day" in world:
        from utils.world_clock import format_clock

        clock = f" · {format_clock(int(world['minute_of_day']))}"
    lines = [
        f"{world.get('name', 'Eldoria')} — Day {world.get('day', '?')} "
        f"({world.get('time_of_day', '?')}{clock})",
        f"Location: {world.get('location', '?')}",
        f"Weather: {world.get('weather', '?')} | {format_tension_line(state)}",
        f"Money: {state.get('inventory', {}).get('wallet', state.get('inventory', {}))}",
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
    base_dir: Any | None = None,
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
    faction_rep = state.get("flags", {}).get("faction_reputation")
    if faction_rep or rep:
        lines.extend(["", "평판:"])
        if faction_rep:
            from utils.faction_engine import FactionEngine

            root = base_dir or getattr(loader, "base_dir", None)
            if root:
                lines.extend(FactionEngine(root).format_summary(state))
        elif rep:
            for k, v in sorted(rep.items()):
                lines.append(f"  - {k}: {v}")
    main_story = state.get("flags", {}).get("main_story")
    if main_story and main_story.get("id"):
        from utils.main_story_engine import MainStoryEngine

        root = base_dir or getattr(loader, "base_dir", None)
        if root:
            engine = MainStoryEngine(root)
            lines.extend(["", f"장기 스토리: {engine.format_summary(state)}"])
            tracker = engine.ending_tracker_summary(state)
            if tracker:
                lines.extend(["  결말 추적 (내부):"] + tracker)
    if event_engine:
        lines.extend(["", f"퀘스트: {event_engine.show_quest_status(state)}"])
    recent = event_entries(state)
    if recent:
        lines.extend(["", "최근 이벤트:"])
        for ev in recent[-5:]:
            lines.append(f"  [{ev.get('type')}] {ev.get('summary')}")
    return "\n".join(lines)
