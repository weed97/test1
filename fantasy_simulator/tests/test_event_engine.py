"""Tests for event engine — seeds, talk, quests."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.content_loader import ContentLoader  # noqa: E402
from utils.event_engine import EventEngine, resolve_npc_id  # noqa: E402
from utils.state_loader import StateLoader  # noqa: E402


class EventEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._isolated = isolated_game_root()
        self.root = self._isolated.__enter__()
        self.content = ContentLoader(self.root)
        self.rng = random.Random(42)
        self.engine = EventEngine(self.content, self.rng)
        self.loader = StateLoader.from_package_root(self.root)
        self.state = self.loader.load_world_state()
        # Reset quest to stage 1 for deterministic talk tests
        self.state["flags"]["quests"] = {
            "active": "smoke_on_the_mountain",
            "stage": 1,
            "completed": [],
        }
        self.state["flags"]["quest_talked_npcs"] = []

    def tearDown(self) -> None:
        self._isolated.__exit__(None, None, None)

    def test_resolve_npc_aliases(self) -> None:
        self.assertEqual(resolve_npc_id("talk torren"), "torren_blacksmith")
        self.assertEqual(resolve_npc_id("talk 릴리안"), "lilian_innkeeper")

    def test_trigger_event_consumes_pending(self) -> None:
        before = len(self.state["flags"]["pending_events"])
        self.state["world"]["time_of_day"] = "night"
        result = self.engine.try_trigger_event(self.state, "explore", turn=1)
        self.assertIsNotNone(result)
        self.assertIn(result["seed_id"], self.state["flags"].get("triggered_events", []))
        self.assertNotIn(result["seed_id"], self.state["flags"]["pending_events"])

    def test_talk_advances_quest_counter(self) -> None:
        self.engine.talk(self.state, "talk torren", 1, self.loader)
        self.engine.talk(self.state, "talk lilian", 2, self.loader)
        result = self.engine.talk(self.state, "talk grey cloak", 3, self.loader)
        self.assertEqual(self.state["flags"]["quests"]["stage"], 2)
        self.assertTrue(any("2단계" in line for line in result.get("lines", [])))

    def test_investigate_forest_stage_2(self) -> None:
        self.state["flags"]["quests"]["stage"] = 2
        result = self.engine.investigate(self.state, "investigate forest", turn=5)
        self.assertEqual(self.state["flags"]["quests"]["stage"], 3)
        self.assertIn("연기", result["summary"])

    def test_load_all_seed_shards(self) -> None:
        self.assertEqual(len(self.content.load_event_seeds()), 129)

    def test_expansion_seed_has_hook(self) -> None:
        seed = self.content.get_event_seed("whispering_well")
        self.assertIsNotNone(seed)
        assert seed is not None
        self.assertEqual(seed.get("seed_type"), "random_event")
        self.assertIn("hook", seed)

    def test_horror_seed_in_catalog(self) -> None:
        seed = self.content.get_event_seed("whispers_from_grave")
        self.assertIsNotNone(seed)
        assert seed is not None
        self.assertEqual(seed.get("seed_type"), "horror_event")

    def test_conspiracy_seed_links_main_plot(self) -> None:
        seed = self.content.get_event_seed("black_council")
        self.assertIsNotNone(seed)
        assert seed is not None
        self.assertEqual(seed.get("seed_type"), "conspiracy")
        self.assertEqual(seed.get("main_plot_link"), "smoke_on_the_mountain")

    def test_character_event_requires_matching_npc(self) -> None:
        self.state["flags"]["pending_events"] = ["lilian_information"]
        self.state["world"]["time_of_day"] = "afternoon"
        out = self.engine.talk(self.state, "talk torren", 1, self.loader)
        self.assertIn("토렌", out["summary"])
        self.assertIn("lilian_information", self.state["flags"]["pending_events"])
        out2 = self.engine.talk(self.state, "talk lilian", 2, self.loader)
        self.assertNotIn("lilian_information", self.state["flags"]["pending_events"])

    def test_stage_dialogue_for_torren(self) -> None:
        lines = self.content.load_npc_dialogues("torren_blacksmith", self.state)
        self.assertTrue(any("릴리안" in line or "회색" in line for line in lines))

    def test_forest_seeds_activate_at_stage_3(self) -> None:
        self.state["flags"]["quests"]["stage"] = 2
        self.engine.investigate(self.state, "investigate forest", turn=10)
        pending = self.state["flags"]["pending_events"]
        self.assertIn("broken_rune_pillar", pending)
        self.assertIn("sentinel_stirring", pending)

    def test_torren_side_quest_turn_in(self) -> None:
        self.state["flags"]["torren_side_quest"] = True
        self.state["flags"]["torren_mold_found"] = True
        self.engine._start_torren_side_quest(self.state)
        result = self.engine.talk(self.state, "talk torren", 20, self.loader)
        self.assertTrue(self.state["flags"].get("torren_side_quest_done"))
        self.assertTrue(any("사이드" in line for line in result.get("lines", [])))

    def test_outcome_lines_appended_to_event(self) -> None:
        self.state["flags"]["pending_events"] = ["black_smoke"]
        self.state["world"]["location"] = "ashpoint"
        self.state["world"]["time_of_day"] = "afternoon"
        result = self.engine.try_trigger_event(self.state, "explore", turn=1)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertGreater(len(result["lines"]), 2)
        self.assertTrue(any("봉인" in line for line in result["lines"]))


if __name__ == "__main__":
    unittest.main()
