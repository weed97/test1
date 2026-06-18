"""Siege balance — no barrier regen during siege, meaningful barrier damage."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.test_kingdom_system import _ready_for_kingdom  # noqa: E402
from utils.kingdom_system import (  # noqa: E402
    complete_kingdom_founding,
    get_kingdom_charter,
    tick_kingdom,
)
from utils.kingdom_war import (  # noqa: E402
    resolve_siege_round,
    start_siege_war,
)
from utils.sim_tick import tick_simulation


class SiegeBalanceTests(unittest.TestCase):
    def _siege_state(self, root: Path) -> tuple[dict, dict]:
        from utils.game_session import GameSession
        from utils.sim_clock import enable_sim_clock

        session = GameSession.from_root(root, mode="rule", seed=3)
        state = session.state
        state.setdefault("flags", {})["game_mode"] = "ecology"
        enable_sim_clock(state, base_dir=root)
        _ready_for_kingdom(state, root)
        complete_kingdom_founding(
            state,
            map_id="ashpoint_01",
            x=10,
            y=10,
            name="밸런스 왕국",
            doctrine_id="martial_ascendancy",
            base_dir=root,
        )
        started = start_siege_war(
            state,
            attacker_civ="goblin_tribe",
            goal_id="plunder",
            goal_label="약탈",
            base_dir=root,
            rng=random.Random(1),
        )
        assert started["ok"]
        return state, started["war"]

    def test_no_barrier_regen_during_active_siege(self) -> None:
        with isolated_game_root() as root:
            state, _war = self._siege_state(root)
            charter = get_kingdom_charter(state)
            assert charter is not None
            charter["barrier"]["hp"] = 11000
            before = int(charter["barrier"]["hp"])
            tick_kingdom(state, base_dir=root)
            after = int(charter["barrier"]["hp"])
            self.assertEqual(before, after)

    def test_barrier_damage_per_round_meaningful(self) -> None:
        with isolated_game_root() as root:
            state, war = self._siege_state(root)
            charter = get_kingdom_charter(state)
            assert charter is not None
            max_hp = int(charter["barrier"]["max_hp"])
            before = int(charter["barrier"]["hp"])
            result = resolve_siege_round(state, war, base_dir=root, rng=random.Random(2))
            after = int(charter["barrier"]["hp"])
            dmg = before - after
            self.assertGreater(result.get("net", 0), 0)
            self.assertGreaterEqual(dmg, int(max_hp * 0.025))

    def test_sim_tick_barrier_does_not_increase_during_siege(self) -> None:
        with isolated_game_root() as root:
            state, _war = self._siege_state(root)
            charter = get_kingdom_charter(state)
            assert charter is not None
            for _ in range(25):
                tick_simulation(state, dt_real_seconds=5.0, base_dir=root, rng=random.Random(4))
            hp = int(charter["barrier"]["hp"])
            self.assertLess(hp, 12000)
