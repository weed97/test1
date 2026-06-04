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
        self.assertLess(len(self.state["flags"]["pending_events"]), before)

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

    def test_load_ten_seeds(self) -> None:
        self.assertEqual(len(self.content.load_event_seeds()), 10)


if __name__ == "__main__":
    unittest.main()
