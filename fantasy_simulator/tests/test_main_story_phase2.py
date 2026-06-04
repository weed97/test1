"""Unit tests for Phase 2 main story engine flow."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.main_story_engine import MainStoryEngine  # noqa: E402


class MainStoryPhase2Tests(unittest.TestCase):
    def test_begin_phase2_queues_opening(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {"id": "ashen_seal_cracking", "phase": 2, "progress": 35},
                    "phase1_climax_done": True,
                },
            }
            ms = engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            engine._begin_phase2(state, story, ms)
            pending = state["flags"]["pending_events"]
            self.assertIn("phase2_council_summons", pending)

    def test_clash_before_opening_does_not_skip_to_branch(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {"id": "ashen_seal_cracking", "phase": 2, "progress": 35},
                    "story_faction_clash_seen": True,
                },
            }
            ms = engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            engine._advance_phase2_from_flag(state, story, ms, "story_faction_clash_seen")
            self.assertFalse(state["flags"].get("phase2_escalation_done"))
            self.assertNotIn("story_alliance_council", state["flags"].get("pending_events", []))

    def test_phase2_exit_on_climax(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 2,
                        "progress": 55,
                        "choices_made": ["ally_village", "path_alliance"],
                    },
                    "phase2_climax_done": True,
                },
            }
            ms = engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine._check_phase2_exit(state, story, ms)
            self.assertTrue(lines)
            self.assertEqual(ms["phase"], 3)


if __name__ == "__main__":
    unittest.main()
