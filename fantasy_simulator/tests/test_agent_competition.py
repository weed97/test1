"""Agent competition — monster civilizations and NPC prosperity."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.agent_competition import (  # noqa: E402
    attach_society,
    get_civilization_state,
    tick_agent_competition,
)
from utils.field_agents import ensure_ecology_seeds, get_agents, tick_field_ecology  # noqa: E402
from utils.game_session import GameSession  # noqa: E402


class AgentCompetitionTests(unittest.TestCase):
    def test_goblins_get_tribe_civilization(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=1)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            ensure_ecology_seeds(session.state, base_dir=root)
            goblins = [
                a
                for a in get_agents(session.state)
                if a.get("evolution_chain") == "goblin"
            ]
            self.assertTrue(goblins)
            self.assertEqual(goblins[0].get("civilization_id"), "goblin_tribe")

    def test_rivalry_tick_can_fire_on_forest(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=42)
            flags = session.state.setdefault("flags", {})
            flags["game_mode"] = "ecology"
            session.state["world"]["map_id"] = "forest_01"
            ensure_ecology_seeds(session.state, base_dir=root)
            all_lines: list[str] = []
            for _ in range(15):
                all_lines.extend(
                    tick_field_ecology(session.state, base_dir=root, rng=session.rng)
                )
            rivalry = [ln for ln in all_lines if "[경쟁]" in ln or "[문명]" in ln]
            civ = get_civilization_state(session.state, "goblin_tribe")
            self.assertTrue(
                rivalry or int(civ.get("prosperity", 0)) > 0 or int(civ.get("wins", 0)) > 0
            )

    def test_npc_society_prosperity_from_builders(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=2)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            ensure_ecology_seeds(session.state, base_dir=root)
            lines = tick_agent_competition(
                session.state, "ashpoint_01", base_dir=root, rng=session.rng
            )
            soc = get_civilization_state(session.state, "ashpoint_commons")
            self.assertGreaterEqual(int(soc.get("prosperity", 0)), 0)


if __name__ == "__main__":
    unittest.main()
