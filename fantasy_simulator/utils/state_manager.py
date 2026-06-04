"""World state load/save, LLM snapshot, and result application."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.state_loader import StateLoader, event_entries
from utils.state_store import StateStore


class StateManager:
    """Facade for sharded world_state + summaries for LLM prompts."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)
        self.store = StateStore.from_package_root(self.base_dir)
        self.loader = StateLoader.from_package_root(self.base_dir)

    def load(self) -> dict[str, Any]:
        return self.store.load()

    def save(self, state: dict[str, Any] | None = None, *, sync_hub: bool = True) -> None:
        """Persist sharded state/ and optionally mirror to world_state.json for Cursor."""
        self.store.save(state)
        if sync_hub:
            self.sync_hub()

    def sync_hub(self) -> None:
        """Write monolithic world_state.json — Cursor-facing SSOT mirror."""
        self.store.export_legacy()

    def snapshot(self, *, event_limit: int = 10) -> dict[str, Any]:
        """Compact state for LLM user messages."""
        return self.store.llm_context_snapshot(event_limit=event_limit)

    def summary(self, state: dict[str, Any] | None = None) -> str:
        """Human-readable one-page status summary."""
        state = state or self.load()
        world = state.get("world", {})
        lines = [
            f"{world.get('name', 'Eldoria')} — Day {world.get('day', '?')} ({world.get('time_of_day', '?')})",
            f"Location: {world.get('location', '?')}",
            f"Weather: {world.get('weather', '?')} | Tension: {world.get('tension', 0):.2f}",
            f"Gold: {state.get('inventory', {}).get('party_gold', 0)}",
        ]
        party = state.get("party", [])
        if party:
            lines.append("Party: " + ", ".join(party))
        recent = event_entries(state)
        if recent:
            lines.append("Recent: " + recent[-1].get("summary", ""))
        return "\n".join(lines)

    def append_event(self, entry: dict[str, Any], state: dict[str, Any]) -> None:
        self.store.append_event(entry)
        state["event_log"] = self.store.load()["event_log"]

    def apply_result(
        self,
        state: dict[str, Any],
        result: dict[str, Any],
        *,
        turn: int | None = None,
    ) -> dict[str, Any]:
        """Merge a single step result (rule or LLM) into world state."""
        role = result.get("role")
        parsed = result.get("parsed")
        mechanical = result.get("mechanical")

        if role == "rule_engine" and mechanical:
            for entry in mechanical.get("event_log_append", []):
                self.append_event(entry, state)
            if mechanical.get("character_updates"):
                self.loader.apply_character_updates(state, mechanical["character_updates"])
            return state

        if not parsed:
            return state

        if role == "mechanics":
            changes = parsed.get("state_changes") or {}
            if not changes.get("event_log_append") and parsed.get("description") and turn:
                changes = dict(changes)
                changes.setdefault(
                    "event_log_append",
                    [{"turn": turn, "type": parsed.get("result_type", "event"), "summary": parsed["description"]}],
                )
            self.store.apply_state_changes(changes, turn=turn)
            char_updates = changes.get("character_updates", {})
            if char_updates:
                self.loader.apply_character_updates(state, char_updates)
            state.update(self.load())

        elif role == "quick_event":
            flags = state.setdefault("flags", {})
            flags["last_quick_event"] = parsed
            changes = parsed.get("suggested_state_changes") or {}
            if changes:
                self.store.apply_state_changes(changes, turn=turn)
            self.save(state)

        elif role == "world_arbiter":
            flags = state.setdefault("flags", {})
            flags["last_consistency_check"] = parsed
            flags["consistency_score"] = parsed.get("consistency_score")
            self.save(state)

        return state

    def export_legacy(self) -> None:
        self.store.export_legacy()
