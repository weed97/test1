"""Headless Phase 3 playtest scenarios for flow invariants."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase3_route_helpers import setup_phase3_session  # noqa: E402
from utils.main_story_engine import MainStoryEngine  # noqa: E402


class Phase3PlaytestTests(unittest.TestCase):
    def test_no_ending_at_progress_100_without_phase3_climax(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 3,
                        "progress": 100,
                        "choices_made": ["ally_village", "path_alliance", "final_reinforce"],
                    },
                },
                "world": {"tension": 60},
            }
            ms = engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine.add_progress(state, 0, reason="test")
            self.assertFalse(ms.get("resolved_ending"))
            self.assertFalse(any("[결말]" in line for line in lines))

    def test_climax_ready_requires_story_phase3_chosen(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "story_seal_near_break": True,
                    "faction_reputation": {"ashpoint_council": 20},
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 3,
                        "choices_made": ["ally_village", "path_alliance"],
                    },
                },
                "world": {"tension": 60},
            }
            engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine._update_phase3_climax_readiness(state, story, state["flags"]["main_story"])
            self.assertFalse(lines)
            self.assertFalse(state["flags"].get("phase3_climax_ready"))

    def test_applicable_climax_seeds_filters_alliance_path(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            ms = {
                "choices_made": ["seek_truth", "path_alliance"],
            }
            seeds = engine._applicable_climax_seeds(story, ms, phase=3)
            self.assertEqual(seeds, ["phase3_climax_alliance_wardens"])

    def test_high_progress_stays_phase3_without_climax(self) -> None:
        with isolated_game_root() as root:
            session, engine = setup_phase3_session(root)
            state = session.state
            flags = state["flags"]
            ms = engine.ensure_initialized(state)
            flags["story_phase3_chosen"] = True
            ms.update(
                {
                    "progress": 90,
                    "choices_made": ["ally_village", "path_alliance", "final_reinforce"],
                }
            )
            story = engine.story_def("ashen_seal_cracking")
            assert story
            engine._maybe_advance_phase(state, story, ms)
            lines = engine._check_phase3_exit(state, story, ms)
            self.assertEqual(ms["phase"], 3)
            self.assertFalse(flags.get("phase3_climax_done"))
            self.assertFalse(ms.get("resolved_ending"))
            self.assertFalse(lines)


if __name__ == "__main__":
    unittest.main()
