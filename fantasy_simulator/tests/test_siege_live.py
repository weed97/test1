"""Live siege snapshot for Godot 2D battlefield."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.test_kingdom_system import _ready_for_kingdom  # noqa: E402
from utils.kingdom_system import complete_kingdom_founding  # noqa: E402
from utils.kingdom_war import (  # noqa: E402
    active_siege_live,
    kingdom_wars_status,
    siege_live_snapshot,
    start_siege_war,
)


class SiegeLiveTests(unittest.TestCase):
    def _state_with_siege(self, root: Path) -> tuple[dict, dict]:
        from utils.game_session import GameSession

        session = GameSession.from_root(root, mode="rule", seed=3)
        state = session.state
        state.setdefault("flags", {})["game_mode"] = "ecology"
        from utils.currency import grant

        grant(state, gold=500, base_dir=root)
        _ready_for_kingdom(state, root)
        complete_kingdom_founding(
            state,
            map_id="ashpoint_01",
            x=10,
            y=10,
            name="라이브 왕국",
            doctrine_id="martial_ascendancy",
            base_dir=root,
        )
        started = start_siege_war(
            state,
            attacker_civ="goblin_tribe",
            goal_id="plunder",
            goal_label="약탈",
            base_dir=root,
            rng=random.Random(2),
        )
        self.assertTrue(started["ok"])
        return state, started["war"]

    def test_siege_live_snapshot_fields(self) -> None:
        with isolated_game_root() as root:
            state, war = self._state_with_siege(root)
            live = siege_live_snapshot(state, war, base_dir=root)
            self.assertEqual(live["war_id"], war["war_id"])
            self.assertIn("phase", live)
            self.assertIn("barrier_hp", live)
            self.assertIn("attacker", live)
            self.assertIn("forces", live["attacker"])

    def test_kingdom_wars_includes_siege_live(self) -> None:
        with isolated_game_root() as root:
            state, _war = self._state_with_siege(root)
            status = kingdom_wars_status(state, base_dir=root)
            self.assertIsNotNone(status.get("siege_live"))
            self.assertIsNotNone(active_siege_live(state, base_dir=root))
