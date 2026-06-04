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
            self.assertEqual(ms["id"], "ashen_seal_cracking")

    def test_legacy_seal_breaking_migrates(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"main_story": {"id": "seal_breaking", "stage": 2, "progress": 10}}}
            ms = engine.ensure_initialized(state)
            self.assertEqual(ms["id"], "ashen_seal_cracking")
            self.assertEqual(ms["phase"], 2)

    def test_seed_progress(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"quests": {"active": "smoke_on_the_mountain", "stage": 3}}}
            engine.ensure_initialized(state)
            lines = engine.on_seed_triggered(state, {"id": "sentinel_stirring", "title": "센티넬"})
            self.assertTrue(lines)
            self.assertGreater(state["flags"]["main_story"]["progress"], 0)

    def test_phase_advance_at_threshold(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"main_story": {"id": "ashen_seal_cracking", "phase": 1, "progress": 33}}}
            engine.add_progress(state, 5, reason="test")
            self.assertGreaterEqual(state["flags"]["main_story"]["progress"], 35)
            self.assertEqual(state["flags"]["main_story"]["phase"], 2)

    def test_phase1_smoke_queues_rumors(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"main_story": {"id": "ashen_seal_cracking", "phase": 1, "progress": 0}}}
            engine.ensure_initialized(state)
            lines = engine.on_outcome(
                state,
                {"main_story_phase1_flag": "black_smoke_seen", "flags_set": {"black_smoke_seen": True}},
            )
            self.assertEqual(state["flags"]["main_story"]["phase1_step"], 1)
            self.assertIn("phase1_village_rumors", state["flags"]["pending_events"])

    def test_phase1_choice_five_way(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "faction_reputation": {fid: 0 for fid in [
                        "ashpoint_council", "silverwood_trade_union", "blackfang_marauders",
                        "ashen_wardens", "black_covenant", "silver_cross_order",
                    ]},
                    "main_story": {"id": "ashen_seal_cracking", "phase": 1, "progress": 15, "phase1_step": 3},
                },
                "world": {"rumors": []},
            }
            lines = engine.apply_choice(state, "seek_truth")
            self.assertIn("seek_truth", state["flags"]["main_story"]["choices_made"])
            self.assertTrue(state["flags"].get("story_path_truth"))

    def test_faction_contact_opens_branch(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"main_story": {"id": "ashen_seal_cracking", "phase": 1, "phase1_step": 2}}}
            engine.ensure_initialized(state)
            engine.record_faction_contact(state, "ashpoint_council")
            pending = state["flags"]["pending_events"]
            self.assertTrue(any(s.startswith("story_choice_") for s in pending))

    def test_phase1_exit_on_climax(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {"id": "ashen_seal_cracking", "phase": 1, "progress": 20, "phase1_step": 5},
                    "phase1_climax_done": True,
                },
                "world": {"tension": 50},
            }
            engine.ensure_initialized(state)
            lines = engine._check_phase1_exit(state, engine.story_def("ashen_seal_cracking"), state["flags"]["main_story"])
            self.assertTrue(lines)
            self.assertEqual(state["flags"]["main_story"]["phase"], 2)

    def test_ending_resolves_at_full_progress(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "faction_reputation": {
                        "ashen_wardens": 40,
                        "ashpoint_council": 30,
                        "black_covenant": -20,
                        "silverwood_trade_union": 0,
                        "blackfang_marauders": 0,
                        "silver_cross_order": 10,
                    },
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 3,
                        "progress": 95,
                        "choices_made": ["seek_truth", "path_alliance"],
                    },
                },
                "world": {"tension": 55},
            }
            engine.ensure_initialized(state)
            lines = engine.add_progress(state, 10, reason="finale")
            self.assertTrue(state["flags"]["main_story"].get("resolved_ending"))
            self.assertTrue(any("결말" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
