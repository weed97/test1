"""Headless Phase 2 playtest scenarios for flow invariants."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase2_route_helpers import setup_phase2_session  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.main_story_engine import MainStoryEngine  # noqa: E402


def _phase2_session(root: Path, *, phase1_choice: str = "ally_village") -> tuple[GameSession, MainStoryEngine]:
    session, engine = setup_phase2_session(root, phase1_choice=phase1_choice)
    return session, engine


class Phase2PlaytestTests(unittest.TestCase):
    def test_no_early_phase3_without_phase2_climax(self) -> None:
        with isolated_game_root() as root:
            session, engine = _phase2_session(root)
            state = session.state
            flags = state["flags"]
            ms = engine.ensure_initialized(state)
            ms["progress"] = 60
            flags["story_phase2_chosen"] = True
            ms["choices_made"] = ["ally_village", "path_alliance"]
            lines = engine._check_phase2_exit(state, engine.story_def("ashen_seal_cracking"), ms)
            self.assertFalse(lines)
            self.assertEqual(ms["phase"], 2)

    def test_climax_ready_requires_story_phase2_chosen(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "story_phase2_chosen": False,
                    "faction_reputation": {"ashpoint_council": 25},
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 2,
                        "choices_made": ["ally_village"],
                    },
                },
                "world": {"tension": 55},
            }
            engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine._update_phase2_climax_readiness(state, story, state["flags"]["main_story"])
            self.assertFalse(lines)
            self.assertFalse(state["flags"].get("phase2_climax_ready"))

    def test_climax_gate_achievable_after_branch(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "story_phase2_chosen": True,
                    "faction_reputation": {"ashpoint_council": 22},
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 2,
                        "choices_made": ["ally_village", "path_alliance"],
                    },
                },
                "world": {"tension": 50},
            }
            engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine._update_phase2_climax_readiness(state, story, state["flags"]["main_story"])
            self.assertTrue(state["flags"].get("phase2_climax_ready"))
            self.assertTrue(lines)

    def test_high_progress_stays_phase2_without_climax(self) -> None:
        with isolated_game_root() as root:
            session, engine = _phase2_session(root)
            state = session.state
            flags = state["flags"]
            ms = engine.ensure_initialized(state)
            flags["story_phase2_chosen"] = True
            ms.update(
                {
                    "progress": 54,
                    "choices_made": ["ally_village", "path_alliance"],
                }
            )
            state["world"]["tension"] = 70
            story = engine.story_def("ashen_seal_cracking")
            assert story
            engine._maybe_advance_phase(state, story, ms)
            lines = engine._check_phase2_exit(state, story, ms)
            self.assertEqual(ms["phase"], 2)
            self.assertFalse(flags.get("phase2_climax_done"))
            self.assertFalse(lines)


if __name__ == "__main__":
    unittest.main()
