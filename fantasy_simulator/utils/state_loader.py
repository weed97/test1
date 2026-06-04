"""Load and persist world state, characters, rules, and prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.io_helpers import load_json, load_text, save_json


@dataclass
class StateLoader:
    """Central accessor for simulation assets rooted at `base_dir`."""

    base_dir: Path
    _characters: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)
    _prompts: dict[str, str] = field(default_factory=dict, init=False)
    _rules: dict[str, str] = field(default_factory=dict, init=False)

    @classmethod
    def from_package_root(cls, root: Path | str | None = None) -> StateLoader:
        if root is None:
            root = Path(__file__).resolve().parent.parent
        return cls(base_dir=Path(root))

    @property
    def world_state_path(self) -> Path:
        return self.base_dir / "world_state.json"

    @property
    def characters_dir(self) -> Path:
        return self.base_dir / "characters"

    @property
    def rules_dir(self) -> Path:
        return self.base_dir / "rules"

    @property
    def prompts_dir(self) -> Path:
        return self.base_dir / "prompts"

    def load_world_state(self) -> dict[str, Any]:
        return load_json(self.world_state_path)

    def save_world_state(self, state: dict[str, Any]) -> None:
        state.setdefault("meta", {})
        state["meta"]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_json(self.world_state_path, state)

    def load_character(self, character_id: str) -> dict[str, Any]:
        if character_id not in self._characters:
            path = self.characters_dir / f"{character_id}.json"
            if not path.exists():
                raise FileNotFoundError(f"Character not found: {character_id} ({path})")
            self._characters[character_id] = load_json(path)
        return self._characters[character_id]

    def load_party(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        return [self.load_character(cid) for cid in state.get("party", [])]

    def load_active_characters(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        return [self.load_character(cid) for cid in state.get("active_characters", [])]

    def load_prompt(self, role: str) -> str:
        if role not in self._prompts:
            path = self.prompts_dir / f"{role}.txt"
            if not path.exists():
                raise FileNotFoundError(f"Prompt not found: {role} ({path})")
            self._prompts[role] = load_text(path)
        return self._prompts[role]

    def load_rule(self, name: str) -> str:
        if name not in self._rules:
            path = self.rules_dir / f"{name}.md"
            if not path.exists():
                raise FileNotFoundError(f"Rule doc not found: {name} ({path})")
            self._rules[name] = load_text(path)
        return self._rules[name]

    def list_characters(self) -> list[str]:
        return sorted(p.stem for p in self.characters_dir.glob("*.json"))

    def list_prompts(self) -> list[str]:
        return sorted(p.stem for p in self.prompts_dir.glob("*.txt"))

    def apply_character_updates(
        self, state: dict[str, Any], updates: dict[str, dict[str, Any]]
    ) -> None:
        """Merge runtime character stat changes back into loaded cache and optionally persist."""
        for cid, patch in updates.items():
            char = self.load_character(cid)
            _deep_merge(char, patch)
            self._characters[cid] = char
            path = self.characters_dir / f"{cid}.json"
            save_json(path, char)

    def append_event_log(self, state: dict[str, Any], entry: dict[str, Any]) -> None:
        state.setdefault("event_log", []).append(entry)


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
