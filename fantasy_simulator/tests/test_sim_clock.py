"""Simulation clock — playtime linked to in-world minutes at realtime_scale."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.test_kingdom_system import _ready_for_kingdom  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.kingdom_system import complete_kingdom_founding  # noqa: E402
from utils.kingdom_war import start_siege_war  # noqa: E402
from utils.sim_clock import enable_sim_clock, sim_clock_enabled, sim_clock_status  # noqa: E402
from utils.sim_tick import tick_simulation  # noqa: E402
from utils.turn_processor import execute_turn  # noqa: E402
from utils.turn_context import TurnContext  # noqa: E402
from utils.world_clock import ensure_world_clock  # noqa: E402


class SimClockTests(unittest.TestCase):
    def _ecology_session(self, root: Path) -> GameSession:
        session = GameSession.from_root(root, mode="rule", seed=11, temporal_mode="precision")
        session.state.setdefault("flags", {})["game_mode"] = "ecology"
        enable_sim_clock(session.state, base_dir=root)
        return session

    def test_realtime_scale_advances_minute_of_day(self) -> None:
        with isolated_game_root() as root:
            session = self._ecology_session(root)
            world = session.state["world"]
            ensure_world_clock(world)
            start_min = int(world["minute_of_day"])
            # Per-tick cap is 5s real → 1 sim min at 12×; twelve ticks ≈ 1 real minute play.
            for _ in range(12):
                result = tick_simulation(session.state, dt_real_seconds=5.0, base_dir=root)
            self.assertTrue(result["ok"])
            self.assertEqual(int(world["minute_of_day"]), (start_min + 12) % 1440)
            self.assertAlmostEqual(result["sim_minutes"], 1.0, places=2)

    def test_explore_turn_does_not_advance_siege_when_sim_clock_on(self) -> None:
        with isolated_game_root() as root:
            session = self._ecology_session(root)
            state = session.state
            from utils.currency import grant

            grant(state, gold=500, base_dir=root)
            _ready_for_kingdom(state, root)
            complete_kingdom_founding(
                state,
                map_id="ashpoint_01",
                x=10,
                y=10,
                name="시계 왕국",
                doctrine_id="martial_ascendancy",
                base_dir=root,
            )
            start = start_siege_war(
                state,
                attacker_civ="goblin_tribe",
                goal_id="plunder",
                goal_label="약탈",
                base_dir=root,
                rng=random.Random(3),
            )
            self.assertTrue(start["ok"])
            war = start["war"]
            round_before = int(war.get("round", 0))

            turn = int(state.get("turn", 1))
            ctx = TurnContext(
                state=state,
                action="explore",
                turn=turn,
                mode="rule",
                manager=session.manager,
                rules=session.rules,
                client=None,
                temporal_mode="precision",
            )
            execute_turn(ctx, loader=session.loader)
            self.assertEqual(int(war.get("round", 0)), round_before)

    def test_sim_tick_advances_siege_rounds(self) -> None:
        with isolated_game_root() as root:
            session = self._ecology_session(root)
            state = session.state
            from utils.currency import grant

            grant(state, gold=500, base_dir=root)
            _ready_for_kingdom(state, root)
            complete_kingdom_founding(
                state,
                map_id="ashpoint_01",
                x=10,
                y=10,
                name="공성 왕국",
                doctrine_id="martial_ascendancy",
                base_dir=root,
            )
            start = start_siege_war(
                state,
                attacker_civ="goblin_tribe",
                goal_id="plunder",
                goal_label="약탈",
                base_dir=root,
                rng=random.Random(5),
            )
            self.assertTrue(start["ok"])
            war = start["war"]
            # first round: 5 sim min; 5 ticks × 5s real × 12 / 60 = 5 sim min
            result: dict = {}
            for _ in range(5):
                result = tick_simulation(
                    state, dt_real_seconds=5.0, base_dir=root, rng=session.rng
                )
            self.assertTrue(result["ok"])
            self.assertGreater(int(war.get("round", 0)), 0)
            self.assertIsNotNone(result.get("siege_simulation"))

    def test_sim_clock_status(self) -> None:
        with isolated_game_root() as root:
            session = self._ecology_session(root)
            self.assertTrue(sim_clock_enabled(session.state, base_dir=root))
            tick_simulation(session.state, dt_real_seconds=10.0, base_dir=root)
            status = sim_clock_status(session.state, base_dir=root)
            self.assertTrue(status["enabled"])
            self.assertEqual(status["realtime_scale"], 12.0)
            self.assertGreater(status["total_sim_minutes"], 0.0)


if __name__ == "__main__":
    unittest.main()
