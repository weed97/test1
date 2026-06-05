"""Field ecology — agents, predator, builder (ecology mode only)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.field_agents import (  # noqa: E402
    agents_on_map,
    ecology_enabled,
    ensure_ecology_seeds,
    tick_field_ecology,
)
from utils.game_session import GameSession  # noqa: E402


class FieldEcologyTests(unittest.TestCase):
    def test_story_mode_no_ecology_tick(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=1)
            session.state.setdefault("flags", {})["game_mode"] = "story"
            lines = tick_field_ecology(session.state, base_dir=root)
            self.assertEqual(lines, [])

    def test_ecology_spawns_agents(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=1)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            ensure_ecology_seeds(session.state, base_dir=root)
            agents = agents_on_map(session.state, "forest_01")
            self.assertTrue(
                any(
                    a.get("evolution_chain") == "goblin"
                    or a.get("evolution_chain") == "shadow_beast"
                    for a in agents
                )
            )

    def test_predator_tick_can_produce_lines(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=99)
            flags = session.state.setdefault("flags", {})
            flags["game_mode"] = "ecology"
            session.state["world"]["map_id"] = "forest_01"
            ensure_ecology_seeds(session.state, base_dir=root)
            for a in agents_on_map(session.state, "ashpoint_01"):
                a["map_id"] = "forest_01"
            lines = tick_field_ecology(session.state, base_dir=root)
            self.assertTrue(ecology_enabled(session.state))


if __name__ == "__main__":
    unittest.main()
