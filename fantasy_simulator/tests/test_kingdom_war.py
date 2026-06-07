"""Kingdom siege wars — class lanes, monster legions."""

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
from utils.kingdom_system import complete_kingdom_founding, recruit_military  # noqa: E402
from utils.kingdom_war import (  # noqa: E402
    build_monster_legion,
    defender_forces_from_charter,
    kingdom_wars_status,
    resolve_siege_round,
    simulate_kingdom_wars_for_turn,
    simulate_siege_round,
    start_siege_war,
    tick_kingdom_wars,
)
from utils.kingdom_system import get_kingdom_charter  # noqa: E402


class KingdomWarTests(unittest.TestCase):
    def _state_with_kingdom(self, root: Path) -> dict:
        session = GameSession.from_root(root, mode="rule", seed=7)
        state = session.state
        state.setdefault("flags", {})["game_mode"] = "ecology"
        state.setdefault("inventory", {})["party_gold"] = 500_000
        complete_kingdom_founding(
            state,
            map_id="ashpoint_01",
            x=10,
            y=10,
            name="방어 왕국",
            doctrine_id="martial_ascendancy",
            base_dir=root,
        )
        charter = get_kingdom_charter(state)
        assert charter is not None
        charter["interior"]["food_store"] = 500
        charter["fortifications"]["walls_level"] = 2
        recruit_military(state, "guard", 5, base_dir=root)
        recruit_military(state, "wall_archer", 4, base_dir=root)
        return state

    def test_monster_legion_has_class_mix(self) -> None:
        with isolated_game_root() as root:
            from utils.kingdom_war import load_war_config

            wcfg = load_war_config(root)
            legion = build_monster_legion("goblin_tribe", wcfg, random.Random(1))
            forces = legion["forces"]
            self.assertGreater(forces.get("sword", 0), 0)
            self.assertGreater(legion["total"], 20)

    def test_defender_maps_military_to_classes(self) -> None:
        with isolated_game_root() as root:
            state = self._state_with_kingdom(root)
            charter = get_kingdom_charter(state)
            assert charter is not None
            from utils.kingdom_war import load_war_config

            forces = defender_forces_from_charter(charter, load_war_config(root))
            self.assertIn("sword", forces)
            self.assertIn("bow", forces)

    def test_start_siege_war(self) -> None:
        with isolated_game_root() as root:
            state = self._state_with_kingdom(root)
            r = start_siege_war(
                state,
                attacker_civ="goblin_tribe",
                goal_id="plunder",
                goal_label="약탈",
                base_dir=root,
                rng=random.Random(2),
            )
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["war"]["type"], "siege")
            st = kingdom_wars_status(state, base_dir=root)
            self.assertEqual(len(st["active_sieges"]), 1)

    def test_siege_rounds_with_classes(self) -> None:
        with isolated_game_root() as root:
            state = self._state_with_kingdom(root)
            r = start_siege_war(
                state,
                attacker_civ="shadow_clan",
                goal_id="mana",
                goal_label="마나 샘",
                base_dir=root,
                rng=random.Random(3),
            )
            war = r["war"]
            result = resolve_siege_round(state, war, base_dir=root, rng=random.Random(4))
            lines = result.get("lines", [])
            events = result.get("events", [])
            self.assertTrue(any("공성" in ln for ln in lines))
            self.assertGreater(len(events), 0)

    def test_simulate_round_api_shape(self) -> None:
        with isolated_game_root() as root:
            state = self._state_with_kingdom(root)
            r = start_siege_war(
                state,
                attacker_civ="beastkin_prides",
                goal_id="resource",
                goal_label="자원",
                base_dir=root,
                rng=random.Random(5),
            )
            war_id = r["war"]["war_id"]
            sim = simulate_siege_round(state, war_id, base_dir=root, rng=random.Random(6))
            self.assertTrue(sim["ok"], sim)

    def test_simulate_on_turn_precision(self) -> None:
        with isolated_game_root() as root:
            state = self._state_with_kingdom(root)
            start_siege_war(
                state,
                attacker_civ="goblin_tribe",
                goal_id="plunder",
                goal_label="약탈",
                base_dir=root,
                rng=random.Random(7),
            )
            sim = simulate_kingdom_wars_for_turn(
                state,
                turn=5,
                temporal_mode="precision",
                minutes_advanced=60,
                base_dir=root,
                rng=random.Random(8),
            )
            self.assertIsNotNone(sim["simulation"])
            self.assertGreaterEqual(sim["simulation"]["rounds_per_war"], 1)
            self.assertTrue(sim["lines"])

    def test_explore_turn_includes_siege_simulation(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=9)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            session.state.setdefault("inventory", {})["party_gold"] = 500_000
            complete_kingdom_founding(
                session.state,
                map_id="ashpoint_01",
                x=1,
                y=1,
                name="시뮬 왕국",
                base_dir=root,
            )
            start_siege_war(
                session.state,
                attacker_civ="goblin_tribe",
                goal_id="plunder",
                goal_label="약탈",
                base_dir=root,
                rng=random.Random(10),
            )
            result = session.run_turn("explore", temporal_mode="precision")
            self.assertIn("lines", result)
            self.assertIsNotNone(result.get("siege_simulation"))


if __name__ == "__main__":
    unittest.main()
