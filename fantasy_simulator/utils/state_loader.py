"""Load and persist world state, characters, rules, and prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from utils.io_helpers import load_json, load_text, save_json
from utils.prompt_router import PromptRouter
from utils.state_store import StateStore


def event_entries(state: dict[str, Any]) -> list[dict[str, Any]]:
    log = state.get("event_log", [])
    if isinstance(log, dict):
        return list(log.get("entries", []))
    return list(log)


@dataclass
class StateLoader:
    """Central accessor for simulation assets rooted at `base_dir`."""

    base_dir: Path
    store: StateStore = field(init=False)
    _characters: dict[str, dict[str, Any]] = field(default_factory=dict, init=False)
    _rules: dict[str, str] = field(default_factory=dict, init=False)
    _prompt_router: PromptRouter | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.store = StateStore.from_package_root(self.base_dir)

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

    @property
    def prompt_router(self) -> PromptRouter:
        if self._prompt_router is None:
            self._prompt_router = PromptRouter.from_package_root(self.base_dir)
        return self._prompt_router

    def load_world_state(self) -> dict[str, Any]:
        return self.store.load()

    def save_world_state(self, state: dict[str, Any]) -> None:
        self.store.save(state)

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

    def list_prompts(self) -> list[str]:
        return self.prompt_router.list_roles()

    def load_prompt(self, role: str, *, model: str | None = None) -> str:
        return self.prompt_router.assemble(role, model=model)

    def load_rule(self, name: str) -> str:
        if name not in self._rules:
            path = self.rules_dir / f"{name}.md"
            if not path.exists():
                raise FileNotFoundError(f"Rule doc not found: {name} ({path})")
            self._rules[name] = load_text(path)
        return self._rules[name]

    def list_characters(self) -> list[str]:
        return sorted(p.stem for p in self.characters_dir.glob("*.json"))

    def apply_character_updates(
        self, state: dict[str, Any], updates: dict[str, dict[str, Any]]
    ) -> None:
        for cid, patch in updates.items():
            char = self.load_character(cid)
            _deep_merge(char, patch)
            self._characters[cid] = char
            path = self.characters_dir / f"{cid}.json"
            save_json(path, char)

    def append_event_log(self, state: dict[str, Any], entry: dict[str, Any]) -> None:
        self.store.append_event(entry)
        state["event_log"] = self.store.load()["event_log"]


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
