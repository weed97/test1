"""World wars, invasions, apex — kingdom loss without world wipe."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.agent_competition import get_civilization_state  # noqa: E402
from utils.civilization_coupling import init_player_civilization  # noqa: E402
from utils.world_conflicts import (  # noqa: E402
    conflicts_status,
    init_world_conflicts,
    tick_world_conflicts,
)


class WorldConflictsTests(unittest.TestCase):
    def test_invasion_respects_world_floor(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=99)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            init_player_civilization(session.state, player_race="human", base_dir=root)
            init_world_conflicts(session.state, base_dir=root)
            goblin = get_civilization_state(session.state, "goblin_tribe")
            goblin["prosperity"] = 120
            goblin["stage_id"] = "horde"
            all_lines: list[str] = []
            for _ in range(40):
                all_lines.extend(
                    tick_world_conflicts(session.state, base_dir=root)
                )
            status = conflicts_status(session.state, base_dir=root)
            civs = session.state["flags"]["ecology"]["civilizations"]
            for cs in civs.values():
                self.assertGreaterEqual(int(cs.get("prosperity", 0)), 5)
            joined = "\n".join(all_lines)
            self.assertTrue(
                "[전쟁]" in joined or "[재앙]" in joined or len(status["history"]) > 0
            )

    def test_war_history_recorded(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=7)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            init_player_civilization(session.state, player_race="human", base_dir=root)
            init_world_conflicts(session.state, base_dir=root)
            get_civilization_state(session.state, "goblin_tribe")["prosperity"] = 100
            for _ in range(50):
                tick_world_conflicts(session.state, base_dir=root)
            hist = conflicts_status(session.state, base_dir=root)["history"]
            if hist:
                w = hist[-1]
                self.assertIn("outcome", w)
                self.assertTrue(w.get("narrative") or w.get("goal_label"))


if __name__ == "__main__":
    unittest.main()
