"""Read/write the canonical world state and character files (atomic, resumable).

``world_state.json`` is the single source of truth for the live world; each character
lives in ``characters/<id>.json``.  All writes are atomic (write-temp-then-rename) so a
crash mid-tick never corrupts the save of a long-running simulation.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any


def _atomic_write(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


class StateStore:
    def __init__(self, world_state_path: str, characters_dir: str) -> None:
        self.world_state_path = world_state_path
        self.characters_dir = characters_dir
        self._world: dict | None = None
        self._characters: dict[str, dict] = {}

    # -- world ---------------------------------------------------------------
    def load_world(self) -> dict:
        with open(self.world_state_path, "r", encoding="utf-8") as fh:
            self._world = json.load(fh)
        return self._world

    @property
    def world(self) -> dict:
        if self._world is None:
            self.load_world()
        assert self._world is not None
        return self._world

    def save_world(self) -> None:
        _atomic_write(self.world_state_path, self.world)

    # -- characters ----------------------------------------------------------
    def character_ids(self) -> list[str]:
        if not os.path.isdir(self.characters_dir):
            return []
        ids = []
        for name in os.listdir(self.characters_dir):
            if name.endswith(".json") and not name.startswith("_"):
                ids.append(name[:-5])
        return sorted(ids)

    def load_characters(self) -> dict[str, dict]:
        self._characters = {}
        for cid in self.character_ids():
            self._characters[cid] = self._read_character(cid)
        return self._characters

    def _read_character(self, cid: str) -> dict:
        path = os.path.join(self.characters_dir, f"{cid}.json")
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def get_character(self, cid: str) -> dict | None:
        if cid in self._characters:
            return self._characters[cid]
        path = os.path.join(self.characters_dir, f"{cid}.json")
        if os.path.exists(path):
            self._characters[cid] = self._read_character(cid)
            return self._characters[cid]
        return None

    @property
    def characters(self) -> dict[str, dict]:
        if not self._characters:
            self.load_characters()
        return self._characters

    def save_character(self, cid: str) -> None:
        char = self._characters.get(cid)
        if char is None:
            return
        _atomic_write(os.path.join(self.characters_dir, f"{cid}.json"), char)

    def save_all_characters(self) -> None:
        for cid in list(self._characters):
            self.save_character(cid)

    def upsert_character(self, char: dict) -> None:
        self._characters[char["id"]] = char

    # -- convenience ---------------------------------------------------------
    def characters_at(self, location_id: str) -> list[dict]:
        return [c for c in self.characters.values()
                if c.get("current_location") == location_id and c.get("alive", True)]

    def save_all(self) -> None:
        self.save_world()
        self.save_all_characters()
