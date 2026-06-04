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

    def test_phase1_smoke_queues_rumors(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {"main_story": {"id": "ashen_seal_cracking", "phase": 1, "progress": 0}},
                "event_log": {"next_turn": 5, "entries": []},
            }
            engine.ensure_initialized(state)
            engine.on_flag_set(state, "black_smoke_seen", turn=3)
            self.assertEqual(state["flags"]["main_story"]["phase1_step"], 1)
            self.assertIn("phase1_village_rumors", state["flags"]["pending_events"])

    def test_rumors_delayed_until_turns_after_smoke(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "black_smoke_seen": True,
                    "pending_events": ["phase1_village_rumors"],
                    "main_story": {"id": "ashen_seal_cracking", "phase": 1, "smoke_seen_turn": 5},
                },
                "event_log": {"next_turn": 6, "entries": []},
            }
            seed = {"requires_main_story_turns_since_smoke_min": 2}
            self.assertFalse(engine.meets_story_requirements(state, seed))
            state["event_log"]["next_turn"] = 8
            self.assertTrue(engine.meets_story_requirements(state, seed))

    def test_climax_gate_two_of_four(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "story_phase1_chosen": True,
                    "faction_reputation": {"ashpoint_council": 30},
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 1,
                        "mountain_visits": 3,
                        "choices_made": ["ally_village"],
                        "factions_contacted": ["ashpoint_council"],
                    },
                },
                "world": {"tension": 20},
            }
            engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine._update_climax_readiness(state, story, state["flags"]["main_story"])
            self.assertTrue(state["flags"].get("phase1_climax_ready"))
            self.assertTrue(lines)
            self.assertIn("phase1_climax_village", state["flags"]["pending_events"])

    def test_mountain_visit_tracks_visits(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {"flags": {"main_story": {"id": "ashen_seal_cracking", "phase": 1}}}
            engine.ensure_initialized(state)
            engine.record_mountain_visit(state, found=True)
            self.assertEqual(state["flags"]["main_story"]["mountain_visits"], 1)
            self.assertTrue(state["flags"].get("phase1_mountain_found"))

    def test_elder_decline_on_mountain_before_response(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {"id": "ashen_seal_cracking", "phase": 1},
                    "phase1_elder_request": True,
                    "faction_reputation": {"ashpoint_council": 0},
                },
            }
            engine.ensure_initialized(state)
            lines = engine.record_mountain_visit(state)
            self.assertTrue(state["flags"].get("phase1_elder_declined"))
            self.assertTrue(state["flags"].get("phase1_elder_responded"))
            self.assertTrue(any("독단" in line for line in lines))

    def test_phase1_hint_in_summary(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {"id": "ashen_seal_cracking", "phase": 1, "phase1_step": 1},
                    "black_smoke_seen": True,
                },
            }
            engine.ensure_initialized(state)
            summary = engine.format_summary(state)
            self.assertIn("다음:", summary)
            self.assertIn("소문", summary)

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
            engine.apply_choice(state, "seek_truth")
            self.assertIn("seek_truth", state["flags"]["main_story"]["choices_made"])

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


if __name__ == "__main__":
    unittest.main()
