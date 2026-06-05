"""Spatial sync — Godot tiles ↔ world state ↔ zones."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.spatial import (  # noqa: E402
    check_map_transition,
    load_world_maps,
    maps_manifest,
    sync_position,
)


class SpatialTests(unittest.TestCase):
    def test_sync_ashpoint_tile(self) -> None:
        with isolated_game_root() as root:
            cfg = load_world_maps(str(root))
            state = {"world": {}, "flags": {}}
            meta = sync_position(
                state,
                map_id="ashpoint_01",
                x=40,
                y=48,
                base_dir=root,
            )
            self.assertTrue(meta["ok"])
            self.assertEqual(state["world"]["zone_id"], "ashpoint")
            self.assertEqual(state["world"]["x"], 40)

    def test_exit_to_forest(self) -> None:
        with isolated_game_root() as root:
            cfg = load_world_maps(str(root))
            tr = check_map_transition(cfg, "ashpoint_01", 74, 30)
            self.assertIsNotNone(tr)
            self.assertEqual(tr["to_map"], "forest_01")
            state = {"world": {}, "flags": {}}
            meta = sync_position(
                state,
                map_id="ashpoint_01",
                x=74,
                y=30,
                base_dir=root,
            )
            self.assertEqual(state["world"]["map_id"], "forest_01")
            self.assertEqual(state["world"]["zone_id"], "forest")

    def test_game_session_apply_position(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=1)
            meta = session.apply_position(
                map_id="forest_01", x=10, y=10, facing="north"
            )
            self.assertTrue(meta["ok"])
            self.assertEqual(session.state["world"]["zone_id"], "forest")

    def test_maps_manifest_for_godot(self) -> None:
        with isolated_game_root() as root:
            m = maps_manifest(root)
            self.assertIn("ashpoint_01", m["maps"])
            self.assertIn("godot_scene", m["maps"]["ashpoint_01"])


if __name__ == "__main__":
    unittest.main()
