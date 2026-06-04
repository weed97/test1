"""Tests for long-term main story engine."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.main_story_engine import MainStoryEngine  # noqa: E402


class MainStoryEngineTests(unittest.TestCase):
    def test_default_story_links_active_quest(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"quests": {"active": "smoke_on_the_mountain", "stage": 1}}}
            ms = engine.ensure_initialized(state)
            self.assertEqual(ms["id"], "seal_breaking")

    def test_seed_progress(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"quests": {"active": "smoke_on_the_mountain", "stage": 3}}}
            engine.ensure_initialized(state)
            lines = engine.on_seed_triggered(state, {"id": "sentinel_stirring", "title": "센티넬"})
            self.assertTrue(lines)
            self.assertGreater(state["flags"]["main_story"]["progress"], 0)

    def test_stage_advance_at_threshold(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"main_story": {"id": "seal_breaking", "stage": 1, "progress": 18}}}
            engine.add_progress(state, 5, reason="test")
            self.assertGreaterEqual(state["flags"]["main_story"]["progress"], 20)
            self.assertEqual(state["flags"]["main_story"]["stage"], 2)


if __name__ == "__main__":
    unittest.main()
