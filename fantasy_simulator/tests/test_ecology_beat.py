"""Ecology beat consolidation — kingdom upkeep on sequential path."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.ecology_beat import run_ecology_beat  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.kingdom_system import complete_kingdom_founding, get_kingdom_charter  # noqa: E402
from utils.parallel_beat import parallel_beat_enabled  # noqa: E402


class EcologyBeatTests(unittest.TestCase):
    def test_sequential_beat_runs_kingdom_upkeep(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=3)
            state = session.state
            state.setdefault("flags", {})["game_mode"] = "ecology"
            state.setdefault("flags", {}).setdefault("ecology", {})["parallel_beat"] = False
            self.assertFalse(parallel_beat_enabled(state, base_dir=root))

            complete_kingdom_founding(
                state, map_id="m", x=1, y=1, name="Beat Realm", base_dir=root
            )
            charter = get_kingdom_charter(state)
            assert charter is not None
            charter["interior"]["farmland_plots"] = 2
            charter["interior"]["food_store"] = 200
            food_before = int(charter["interior"]["food_store"])

            run_ecology_beat(state, base_dir=root, turn=1, rng=session.rng)
            self.assertGreater(
                int(charter["interior"]["food_store"]),
                food_before,
                "sequential ecology beat must call tick_kingdom",
            )


if __name__ == "__main__":
    unittest.main()
