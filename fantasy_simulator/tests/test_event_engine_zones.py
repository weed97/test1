"""Event engine — main story seed zones and talk eligibility."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.content_loader import ContentLoader  # noqa: E402
from utils.event_engine import EventEngine  # noqa: E402


class EventEngineZoneTests(unittest.TestCase):
    def test_main_story_choice_eligible_in_forest_on_talk(self) -> None:
        with isolated_game_root() as root:
            content = ContentLoader(root)
            engine = EventEngine(content, random.Random(0))
            state = {
                "flags": {
                    "pending_events": ["story_alliance_council"],
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 2,
                        "progress": 45,
                        "choices_made": ["ally_village"],
                    },
                },
                "world": {"location": "북쪽 숲 — 연기가 보이는 외곽", "time_of_day": "afternoon"},
            }
            eligible = engine._eligible_seeds(state, "talk", related_npc="elder_maren")
            ids = [s["id"] for s in eligible]
            self.assertIn("story_alliance_council", ids)

    def test_main_story_seed_without_zones_allows_forest(self) -> None:
        with isolated_game_root() as root:
            content = ContentLoader(root)
            engine = EventEngine(content, random.Random(0))
            state = {
                "flags": {
                    "pending_events": ["phase2_seal_tremor"],
                    "main_story": {"id": "ashen_seal_cracking", "phase": 2},
                },
                "world": {"location": "북쪽 숲", "time_of_day": "afternoon"},
            }
            eligible = engine._eligible_seeds(state, "investigate")
            self.assertTrue(any(s["id"] == "phase2_seal_tremor" for s in eligible))


if __name__ == "__main__":
    unittest.main()
