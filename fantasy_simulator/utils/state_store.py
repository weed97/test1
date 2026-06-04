"""Sharded world state load/save with legacy world_state.json migration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.io_helpers import load_json, save_json

SHARD_FILES = {
    "meta": "meta.json",
    "world": "world.json",
    "factions": "factions.json",
    "party": "party.json",
    "inventory": "inventory.json",
    "flags": "flags.json",
    "combat": "combat.json",
    "event_log": "event_log.json",
}


@dataclass
class StateStore:
    """Manages sharded state under `state/` with optional legacy monolith import."""

    base_dir: Path
    _cache: dict[str, Any] = field(default_factory=dict, init=False)

    @classmethod
    def from_package_root(cls, root: Path | str) -> StateStore:
        return cls(base_dir=Path(root))

    @property
    def state_dir(self) -> Path:
        return self.base_dir / "state"

    @property
    def legacy_path(self) -> Path:
        return self.base_dir / "world_state.json"

    def load(self, *, force: bool = False) -> dict[str, Any]:
        if force:
            self._cache.clear()

        if self._cache:
            return self._cache

        if self._shards_exist():
            self._cache = self._load_shards()
        elif self.legacy_path.exists():
            self._cache = load_json(self.legacy_path)
            self._migrate_to_shards(self._cache)
        else:
            raise FileNotFoundError(
                f"No state found: expected {self.state_dir}/ or {self.legacy_path}"
            )
        return self._cache

    def reload(self) -> dict[str, Any]:
        """Discard in-memory cache and reload from disk."""
        return self.load(force=True)

    def save(self, state: dict[str, Any] | None = None) -> None:
        state = state if state is not None else self._cache
        if not state:
            raise ValueError("No state to save")

        state.setdefault("meta", {})
        state["meta"]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        state["meta"]["storage"] = "sharded"
        self._cache = state
        self._save_shards(state)

    def export_legacy(self, path: Path | None = None) -> None:
        """Write monolithic world_state.json hub mirror from canonical state/."""
        target = path or self.legacy_path
        state = self.load()
        save_json(target, state)

    def get_recent_events(self, limit: int = 10) -> list[dict[str, Any]]:
        log = self.load().get("event_log", [])
        if isinstance(log, dict):
            entries = log.get("entries", [])
        else:
            entries = log
        return entries[-limit:]

    def append_event(self, entry: dict[str, Any]) -> None:
        state = self.load()
        log = state.setdefault("event_log", {"next_turn": 1, "entries": []})
        if isinstance(log, list):
            log = {"next_turn": len(log) + 1, "entries": log}
            state["event_log"] = log
        log["entries"].append(entry)
        self.save(state)

    def llm_context_snapshot(self, *, event_limit: int = 10) -> dict[str, Any]:
        """Compact state for LLM prompts — omits full event history."""
        state = self.load()
        log = state.get("event_log", [])
        if isinstance(log, dict):
            recent = log.get("entries", [])[-event_limit:]
            next_turn = log.get("next_turn", len(recent) + 1)
        else:
            recent = log[-event_limit:]
            next_turn = len(log) + 1

        return {
            "meta": state.get("meta", {}),
            "world": state.get("world", {}),
            "factions": state.get("factions", {}),
            "party": state.get("party", []),
            "active_characters": state.get("active_characters", []),
            "npc_locations": state.get("npc_locations", {}),
            "inventory": state.get("inventory", {}),
            "flags": state.get("flags", {}),
            "combat": state.get("combat"),
            "recent_events": recent,
            "next_turn": next_turn,
        }

    def apply_patches(self, patches: dict[str, Any]) -> None:
        state = self.load()
        for key, value in patches.items():
            if key == "event_log_append":
                for entry in value:
                    self.append_event(entry)
            elif key in ("world", "factions", "flags", "inventory", "combat"):
                if value is None and key == "combat":
                    state[key] = None
                elif isinstance(value, dict) and isinstance(state.get(key), dict):
                    _deep_merge(state[key], value)
                else:
                    state[key] = value
            else:
                state[key] = value
        self.save(state)

    def apply_state_changes(self, changes: dict[str, Any], *, turn: int | None = None) -> None:
        """Apply mechanics_codex state_changes blob to sharded state."""
        if not changes:
            return
        patches: dict[str, Any] = {}
        for key in ("world", "factions", "flags", "inventory", "combat"):
            if key in changes:
                patches[key] = changes[key]
        if changes.get("event_log_append"):
            patches["event_log_append"] = changes["event_log_append"]
        elif turn is not None and changes.get("description"):
            patches["event_log_append"] = [
                {
                    "turn": turn,
                    "type": changes.get("result_type", "event"),
                    "summary": changes["description"],
                }
            ]
        self.apply_patches(patches)

    def _shards_exist(self) -> bool:
        return (self.state_dir / "meta.json").exists()

    def _load_shards(self) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for key, filename in SHARD_FILES.items():
            path = self.state_dir / filename
            state[key if key != "event_log" else "event_log"] = load_json(path)

        party_shard = state.pop("party")
        state["active_characters"] = party_shard.get("active_characters", [])
        state["party"] = party_shard.get("party", [])
        state["npc_locations"] = party_shard.get("npc_locations", {})

        log = state["event_log"]
        if isinstance(log, dict):
            state["_event_next_turn"] = log.get("next_turn", 1)
            state["event_log"] = log
        return state

    def _save_shards(self, state: dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)

        save_json(self.state_dir / SHARD_FILES["meta"], state.get("meta", {}))
        save_json(self.state_dir / SHARD_FILES["world"], state.get("world", {}))
        save_json(self.state_dir / SHARD_FILES["factions"], state.get("factions", {}))
        save_json(
            self.state_dir / SHARD_FILES["party"],
            {
                "active_characters": state.get("active_characters", []),
                "party": state.get("party", []),
                "npc_locations": state.get("npc_locations", {}),
            },
        )
        save_json(self.state_dir / SHARD_FILES["inventory"], state.get("inventory", {}))
        save_json(self.state_dir / SHARD_FILES["flags"], state.get("flags", {}))
        save_json(self.state_dir / SHARD_FILES["combat"], state.get("combat"))

        log = state.get("event_log", {"next_turn": 1, "entries": []})
        if isinstance(log, list):
            log = {"next_turn": len(log) + 1, "entries": log}
        save_json(self.state_dir / SHARD_FILES["event_log"], log)

    def _migrate_to_shards(self, state: dict[str, Any]) -> None:
        log = state.get("event_log", [])
        if isinstance(log, list):
            state["event_log"] = {"next_turn": len(log) + 1, "entries": log}
        self._cache = state
        self.save(state)


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
