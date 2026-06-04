"""Unit tests for Phase 3 main story engine flow."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.main_story_engine import MainStoryEngine  # noqa: E402


class MainStoryPhase3Tests(unittest.TestCase):
    def test_begin_phase3_queues_opening(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {"id": "ashen_seal_cracking", "phase": 3, "progress": 65},
                    "phase2_climax_done": True,
                },
            }
            ms = engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            engine._begin_phase3(state, story, ms)
            pending = state["flags"]["pending_events"]
            self.assertIn("phase3_tower_alarm", pending)

    def test_progress_100_blocked_without_phase3_climax(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 3,
                        "progress": 95,
                        "choices_made": ["ally_village", "path_alliance"],
                    },
                },
                "world": {"tension": 60},
            }
            ms = engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine.add_progress(state, 10, reason="test")
            self.assertFalse(ms.get("resolved_ending"))
            self.assertFalse(any("[결말]" in line for line in lines))

    def test_phase3_exit_resolves_ending(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 3,
                        "progress": 90,
                        "choices_made": ["ally_village", "path_alliance", "final_reinforce"],
                        "ending_scores": {"seal_maintained": 40},
                        "leading_ending": "seal_maintained",
                    },
                    "phase3_climax_done": True,
                },
                "world": {"tension": 60},
            }
            ms = engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine._check_phase3_exit(state, story, ms)
            self.assertTrue(lines)
            self.assertTrue(ms.get("resolved_ending"))


if __name__ == "__main__":
    unittest.main()
