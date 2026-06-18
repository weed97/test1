"""Player settlement — construction level, build, hire."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.currency import get_wallet, grant, wallet_to_copper  # noqa: E402
from utils.settlement_build import (  # noqa: E402
    get_player_settlement,
    hire_workers,
    start_build,
    tick_player_build_projects,
)
from utils.game_session import GameSession  # noqa: E402


class SettlementBuildTests(unittest.TestCase):
    def _ecology_state(self, root: Path) -> dict:
        session = GameSession.from_root(root, mode="rule", seed=1)
        state = session.state
        state.setdefault("flags", {})["game_mode"] = "ecology"
        grant(state, copper=2000, silver=10, base_dir=root)
        return state

    def test_blacksmith_requires_level_2(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            ps = get_player_settlement(state)
            ps["construction_level"] = 1
            r = start_build(
                state,
                "blacksmith",
                map_id="ashpoint_01",
                x=10,
                y=10,
                base_dir=root,
            )
            self.assertFalse(r["ok"])

    def test_start_blacksmith_at_level_2(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            ps = get_player_settlement(state)
            ps["construction_level"] = 2
            ps["stockpile"] = {"wood": 100, "stone": 100, "iron": 50}
            before = wallet_to_copper(get_wallet(state, base_dir=root), base_dir=root)
            r = start_build(
                state,
                "blacksmith",
                map_id="ashpoint_01",
                x=10,
                y=10,
                mode="self",
                base_dir=root,
            )
            self.assertTrue(r["ok"])
            after = wallet_to_copper(get_wallet(state, base_dir=root), base_dir=root)
            self.assertLess(after, before)

    def test_hire_workers_costs_gold(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            get_player_settlement(state)["construction_level"] = 2
            r = hire_workers(state, 2, base_dir=root)
            self.assertTrue(r["ok"])
            self.assertEqual(r["hired_workers"], 2)

    def test_build_progress_on_tick(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            ps = get_player_settlement(state)
            ps["construction_level"] = 2
            start_build(
                state,
                "camp_fire",
                map_id="ashpoint_01",
                x=5,
                y=5,
                mode="self",
                base_dir=root,
            )
            lines = tick_player_build_projects(state, base_dir=root)
            self.assertTrue(lines)
