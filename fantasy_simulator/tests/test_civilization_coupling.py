"""Player-race civilization init and world coupling ripples."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.civilization_coupling import (  # noqa: E402
    civilization_world_status,
    init_player_civilization,
    tick_civilization_coupling,
)
from utils.game_session import GameSession  # noqa: E402
from utils.settlement_build import get_player_settlement  # noqa: E402
from utils.world_systems import tick_world_systems  # noqa: E402


class CivilizationCouplingTests(unittest.TestCase):
    def test_human_start_profile(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=1)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            profile = init_player_civilization(
                session.state, player_race="human", base_dir=root
            )
            self.assertEqual(profile["race"], "human")
            self.assertEqual(profile["player_civilization_id"], "player_frontier_kingdom")
            self.assertEqual(session.state["world"]["realm_id"], "human")

    def test_elf_start_forest_map(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=2)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            profile = init_player_civilization(
                session.state, player_race="elf", base_dir=root
            )
            self.assertEqual(profile["player_civilization_id"], "player_silver_enclave")
            self.assertEqual(session.state["world"]["map_id"], "forest_01")

    def test_player_build_ripples_off_map_civs(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=3)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            init_player_civilization(session.state, player_race="human", base_dir=root)
            ps = get_player_settlement(session.state)
            ps["construction_level"] = 3
            ps["construction_xp"] = 200
            before = civilization_world_status(session.state, base_dir=root)
            dwarf_before = int(
                before["civilizations"].get("dwarf_deepforge", {}).get("prosperity", 0)
            )
            for _ in range(5):
                tick_civilization_coupling(session.state, base_dir=root, rng=session.rng)
            after = civilization_world_status(session.state, base_dir=root)
            dwarf_after = int(
                after["civilizations"].get("dwarf_deepforge", {}).get("prosperity", 0)
            )
            player_after = int(
                after["civilizations"]
                .get("player_frontier_kingdom", {})
                .get("prosperity", 0)
            )
            self.assertGreater(player_after, 0)
            self.assertGreaterEqual(dwarf_after, dwarf_before)
            self.assertTrue(after.get("recent_events"))

    def test_world_systems_includes_coupling_in_ecology(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=4)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            init_player_civilization(session.state, player_race="human", base_dir=root)
            lines = tick_world_systems(
                session.state, base_dir=root, turn=1, rng=session.rng
            )
            joined = "\n".join(lines)
            self.assertTrue(
                "[세계]" in joined
                or "[여정]" in joined
                or session.state["flags"]["ecology"].get("world_pulse")
            )


if __name__ == "__main__":
    unittest.main()
