"""Content loader — Phase 2 NPC dialogue pools."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.content_loader import ContentLoader  # noqa: E402


class Phase2DialogueTests(unittest.TestCase):
    def test_elder_phase2_mid_dialogue(self) -> None:
        with isolated_game_root() as root:
            loader = ContentLoader(root)
            state = {
                "flags": {
                    "main_story": {"phase": 2, "phase2_subphase": "mid"},
                    "quests": {"active": "smoke_on_the_mountain", "stage": 1},
                },
            }
            lines = loader.load_npc_dialogues("elder_maren", state)
            self.assertTrue(any("2단계" in line or "동맹" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
