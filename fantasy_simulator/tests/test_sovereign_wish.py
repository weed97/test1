"""Sovereign wish — cooldown, forbidden edicts, empower kingdom."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.sovereign_wish import (  # noqa: E402
    can_cast_sovereign_wish,
    resolve_sovereign_wish,
    wish_status,
)


class SovereignWishTests(unittest.TestCase):
    def test_forbidden_edict_rejected(self) -> None:
        with isolated_game_root() as root:
            state = {"world": {"day": 5000}, "flags": {"world_sovereign": {"holder_id": "npc_arthur_pendragon"}}}
            result = resolve_sovereign_wish(
                state,
                {"edict_type": "instant_win"},
                base_dir=root,
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "forbidden_edict")

    def test_empower_kingdom_sets_prosperity(self) -> None:
        with isolated_game_root() as root:
            state = {
                "world": {"day": 5000},
                "flags": {
                    "world_sovereign": {"holder_id": "npc_arthur_pendragon"},
                    "ecology": {"civilizations": {"ashpoint_commons": {"prosperity": 10}}},
                },
            }
            result = resolve_sovereign_wish(
                state,
                {"edict_type": "empower_kingdom", "civilization_id": "ashpoint_commons", "prosperity_gain": 20},
                base_dir=root,
            )
            self.assertTrue(result["ok"])
            pros = state["flags"]["ecology"]["civilizations"]["ashpoint_commons"]["prosperity"]
            self.assertGreaterEqual(pros, 30)

    def test_cooldown_blocks_second_wish(self) -> None:
        with isolated_game_root() as root:
            state = {
                "world": {"day": 100},
                "flags": {
                    "world_sovereign": {"holder_id": "npc_arthur_pendragon"},
                    "sovereign": {"last_sovereign_wish_world_day": 50},
                    "ecology": {"civilizations": {}},
                },
            }
            ok, _ = can_cast_sovereign_wish(state, base_dir=root)
            self.assertFalse(ok)
            st = wish_status(state, base_dir=root)
            self.assertFalse(st["can_cast"])
            self.assertGreater(st["days_until_ready"], 0)


if __name__ == "__main__":
    unittest.main()
