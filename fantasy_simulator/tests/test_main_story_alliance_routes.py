"""Main story alliance route catalog and gating."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.io_helpers import load_json  # noqa: E402
from utils.main_story_engine import MainStoryEngine  # noqa: E402


class MainStoryAllianceRouteTests(unittest.TestCase):
    def test_alliance_climax_requires_phase1_and_path2(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "phase2_climax_ready": True,
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 2,
                        "choices_made": ["ally_village", "path_alliance"],
                    },
                },
                "world": {"tension": 60, "location": "ashpoint"},
            }
            seed = {
                "requires_main_story_choices": ["ally_village", "path_alliance"],
                "requires_flags": ["phase2_climax_ready"],
            }
            self.assertTrue(engine.meets_story_requirements(state, seed))
            state["flags"]["main_story"]["choices_made"] = ["seek_truth", "path_alliance"]
            self.assertFalse(engine.meets_story_requirements(state, seed))

    def test_phase2_alliance_routes_cover_all_phase1_branches(self) -> None:
        with isolated_game_root() as root:
            story = next(
                s
                for s in load_json(root / "events" / "main_stories.json")["stories"]
                if s["id"] == "ashen_seal_cracking"
            )
            routes = story.get("phase2_alliance_routes", {})
            self.assertEqual(
                set(routes.keys()),
                {"ally_village", "seek_truth", "pursue_power", "exploit_chaos", "stay_neutral"},
            )


if __name__ == "__main__":
    unittest.main()
