"""Regional resource pools and danger-scaled loot."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.regional_resources import (  # noqa: E402
    combat_loot_for_zone,
    ensure_zone_pools,
    try_regional_gather,
)


class RegionalResourcesTests(unittest.TestCase):
    def test_gather_depletes_zone_pool(self) -> None:
        with isolated_game_root() as root:
            from utils.game_session import GameSession

            session = GameSession.from_root(root, mode="rule", seed=2)
            state = session.state
            state["world"]["zone_id"] = "ashpoint"
            pool = ensure_zone_pools(state, "ashpoint", base_dir=root)
            before = int(pool.get("wood", 0))
            lines = try_regional_gather(
                state, "explore", base_dir=root, rng=random.Random(1)
            )
            after = int(pool.get("wood", 0))
            self.assertTrue(lines)
            self.assertLess(after, before)

    def test_tower_loot_beats_ashpoint(self) -> None:
        with isolated_game_root() as root:
            ash = combat_loot_for_zone(
                "ashpoint", base_dir=root, rng=random.Random(3), threat_level=1
            )
            tower = combat_loot_for_zone(
                "tower", base_dir=root, rng=random.Random(3), threat_level=1
            )
            self.assertGreater(tower[0], ash[0])
