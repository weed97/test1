"""Tests for shared StateStore and hub sync."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.state_loader import StateLoader  # noqa: E402
from utils.state_manager import StateManager  # noqa: E402


def _bootstrap_state(root: Path) -> None:
    state_dir = root / "state"
    state_dir.mkdir()
    shards = {
        "meta.json": {"version": 1},
        "world.json": {"name": "Eldoria", "day": 1, "time_of_day": "morning", "location": "test"},
        "factions.json": {},
        "party.json": {"party": ["hero"], "active_characters": ["hero"], "npc_locations": {}},
        "inventory.json": {"wallet": {"copper": 10, "silver": 0, "gold": 0}},
        "flags.json": {},
        "combat.json": None,
        "event_log.json": {"next_turn": 1, "entries": []},
    }
    for name, data in shards.items():
        (state_dir / name).write_text(json.dumps(data), encoding="utf-8")


class SharedStateStoreTests(unittest.TestCase):
    def test_loader_and_manager_share_one_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bootstrap_state(root)
            loader = StateLoader(base_dir=root)
            manager = StateManager(root, store=loader.store)

            loader.append_event_log(loader.load_world_state(), {"turn": 1, "type": "test", "summary": "via loader"})
            via_manager = manager.load(force=True)
            entries = via_manager["event_log"]["entries"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["summary"], "via loader")

    def test_refresh_state_keeps_dict_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bootstrap_state(root)
            manager = StateManager(root)
            state = manager.load()
            state_id = id(state)
            state["world"]["day"] = 99
            manager.save(state)
            manager.refresh_state(state)
            self.assertEqual(id(state), state_id)
            self.assertEqual(state["world"]["day"], 99)

    def test_hub_export_matches_shards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bootstrap_state(root)
            manager = StateManager(root)
            state = manager.load()
            state["inventory"]["wallet"] = {"copper": 999, "silver": 0, "gold": 0}
            manager.save(state)
            hub = json.loads((root / "world_state.json").read_text(encoding="utf-8"))
            self.assertEqual(hub["inventory"]["wallet"]["copper"], 999)


if __name__ == "__main__":
    unittest.main()
