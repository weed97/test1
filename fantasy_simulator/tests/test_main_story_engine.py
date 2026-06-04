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
            state = {"flags": {"main_story": {"id": "ashen_seal_cracking", "phase": 1, "progress": 28}}}
            engine.add_progress(state, 5, reason="test")
            self.assertGreaterEqual(state["flags"]["main_story"]["progress"], 30)
            self.assertEqual(state["flags"]["main_story"]["phase"], 2)

    def test_phase1_choice_sets_rumor_and_scores(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {"faction_reputation": {fid: 0 for fid in [
                    "ashpoint_council", "silverwood_trade_union", "blackfang_marauders",
                    "ashen_wardens", "black_covenant", "silver_cross_order",
                ]}, "main_story": {"id": "ashen_seal_cracking", "phase": 1, "progress": 15}},
                "world": {"rumors": []},
            }
            lines = engine.apply_choice(state, "ally_warden_seal")
            self.assertTrue(lines)
            self.assertIn("ally_warden_seal", state["flags"]["main_story"]["choices_made"])
            self.assertEqual(state["flags"]["main_story"]["rumor_tone"], "mystery")
            self.assertGreater(state["flags"]["main_story"]["ending_scores"].get("seal_maintained", 0), 0)

    def test_phase_events_queued_at_progress(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"main_story": {"id": "ashen_seal_cracking", "phase": 1, "progress": 10}}}
            engine.ensure_initialized(state)
            engine.add_progress(state, 3, reason="test")
            pending = state["flags"]["pending_events"]
            self.assertIn("story_choice_council", pending)

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
                        "choices_made": ["ally_warden_seal", "path_alliance"],
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
