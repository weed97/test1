"""Monster pack — internal rivalry, alpha, greed over alliance."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.field_agents import ensure_ecology_seeds, get_agents, tick_field_ecology  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.monster_pack import refresh_pack_alphas  # noqa: E402


class MonsterPackTests(unittest.TestCase):
    def test_monsters_same_civ_not_all_allies(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=50)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            session.state["world"]["map_id"] = "forest_01"
            ensure_ecology_seeds(session.state, base_dir=root)
            goblins = [
                a for a in get_agents(session.state) if a.get("evolution_chain") == "goblin"
            ]
            self.assertGreaterEqual(len(goblins), 2)
            for g in goblins:
                self.assertIn("pack", g)
                self.assertGreaterEqual(int(g["pack"].get("greed", 0)), 70)

    def test_internal_fight_or_pack_logs(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=51)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            session.state["world"]["map_id"] = "forest_01"
            ensure_ecology_seeds(session.state, base_dir=root)
            lines: list[str] = []
            for _ in range(25):
                lines.extend(tick_field_ecology(session.state, base_dir=root))
            joined = "\n".join(lines)
            self.assertTrue(
                "[내부전]" in joined
                or "[무리]" in joined
                or "[스킬]" in joined
            )
            refresh_pack_alphas(
                [a for a in get_agents(session.state) if a.get("map_id") == "forest_01"],
                base_dir=root,
            )
            alphas = [
                a
                for a in get_agents(session.state)
                if a.get("pack", {}).get("role") == "alpha"
            ]
            self.assertGreaterEqual(len(alphas), 1)


if __name__ == "__main__":
    unittest.main()
