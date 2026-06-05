"""Content loader — Phase 3 NPC dialogue pools."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.content_loader import ContentLoader  # noqa: E402


class Phase3DialogueTests(unittest.TestCase):
    def test_elder_phase3_early_dialogue(self) -> None:
        with isolated_game_root() as root:
            loader = ContentLoader(root)
            state = {
                "flags": {
                    "main_story": {"phase": 3, "phase3_subphase": "early"},
                },
            }
            lines = loader.load_npc_dialogues("elder_maren", state)
            self.assertTrue(any("3단계" in line for line in lines))

    def test_elder_phase3_mid_dialogue(self) -> None:
        with isolated_game_root() as root:
            loader = ContentLoader(root)
            state = {
                "flags": {
                    "main_story": {"phase": 3, "phase3_subphase": "mid"},
                    "quests": {"active": "smoke_on_the_mountain", "stage": 1},
                },
            }
            lines = loader.load_npc_dialogues("elder_maren", state)
            self.assertTrue(any("3단계" in line or "봉인" in line for line in lines))

    def test_lilian_phase3_late_dialogue(self) -> None:
        with isolated_game_root() as root:
            loader = ContentLoader(root)
            state = {
                "flags": {
                    "main_story": {"phase": 3, "phase3_subphase": "late"},
                },
            }
            lines = loader.load_npc_dialogues("lilian_innkeeper", state)
            self.assertTrue(any("강화" in line or "혼돈" in line for line in lines))

    def test_grey_cloak_phase3_climax_dialogue(self) -> None:
        with isolated_game_root() as root:
            loader = ContentLoader(root)
            state = {
                "flags": {
                    "main_story": {"phase": 3, "phase3_subphase": "climax"},
                },
            }
            lines = loader.load_npc_dialogues("grey_cloak", state)
            self.assertTrue(any("결말" in line for line in lines))

    def test_torren_phase3_mid_dialogue(self) -> None:
        with isolated_game_root() as root:
            loader = ContentLoader(root)
            state = {
                "flags": {
                    "main_story": {"phase": 3, "phase3_subphase": "mid"},
                },
            }
            lines = loader.load_npc_dialogues("torren_blacksmith", state)
            self.assertTrue(any("최후" in line or "봉인" in line for line in lines))

    def test_alliance_faction_dialogue_on_elder(self) -> None:
        with isolated_game_root() as root:
            loader = ContentLoader(root)
            state = {
                "flags": {
                    "alliance_faction": "ashpoint_council",
                    "main_story": {"phase": 3, "phase3_subphase": "early"},
                },
            }
            lines = loader.load_npc_dialogues("elder_maren", state)
            self.assertTrue(any("자치회" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
