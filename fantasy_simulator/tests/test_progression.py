"""Character progression — jobs, evolution chains, spawn caps."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.field_agents import agents_on_map, ensure_ecology_seeds  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.progression import (  # noqa: E402
    can_spawn_agent,
    equip_item,
    grant_evolution_xp,
    init_heroes_from_party,
    load_progression_config,
    on_explore_progression,
    progression_status,
    spawn_evolved_monster,
    spawn_limits_for_map,
    unlock_skill,
)


class ProgressionTests(unittest.TestCase):
    def test_goblin_spawn_and_species_cap(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=1)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            ensure_ecology_seeds(session.state, base_dir=root)
            goblins = [
                a
                for a in agents_on_map(session.state, "forest_01")
                if a.get("evolution_chain") == "goblin"
            ]
            self.assertGreaterEqual(len(goblins), 1)
            self.assertEqual(goblins[0].get("evolution_tier"), 1)
            self.assertEqual(goblins[0].get("label"), "고블린")

            ok, _ = can_spawn_agent(
                session.state,
                map_id="forest_01",
                kind="monster",
                species_id="goblin",
                base_dir=root,
            )
            cfg = load_progression_config(root)
            limits = spawn_limits_for_map(cfg, "forest_01")
            cap = int(limits["species_caps"]["goblin"])
            spawned = 0
            while ok and spawned < 10:
                agent, _ = spawn_evolved_monster(
                    session.state,
                    "goblin",
                    map_id="forest_01",
                    x=5 + spawned,
                    y=5,
                    tier=1,
                    base_dir=root,
                )
                if agent is None:
                    break
                spawned += 1
                ok, _ = can_spawn_agent(
                    session.state,
                    map_id="forest_01",
                    kind="monster",
                    species_id="goblin",
                    base_dir=root,
                )
            total_goblins = sum(
                1
                for a in agents_on_map(session.state, "forest_01")
                if a.get("species_id") == "goblin"
            )
            self.assertLessEqual(total_goblins, cap)

    def test_evolution_tier_up(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=2)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            agent, _ = spawn_evolved_monster(
                session.state,
                "goblin",
                map_id="forest_01",
                x=1,
                y=1,
                tier=1,
                base_dir=root,
            )
            assert agent is not None
            agent["evolution_xp"] = 100
            lines = grant_evolution_xp(agent, 0, base_dir=root)
            self.assertTrue(any("진화" in ln for ln in lines) or agent.get("evolution_tier", 1) >= 2)

    def test_hero_jobs_and_explore_xp(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=3)
            flags = session.state.setdefault("flags", {})
            flags["game_mode"] = "ecology"
            init_heroes_from_party(session.state, base_dir=root)
            gareth = progression_status(session.state, base_dir=root)["heroes"].get(
                "gareth_ironshield"
            )
            self.assertIsNotNone(gareth)
            self.assertEqual(gareth["job_id"], "knight")
            before_xp = int(gareth["xp"])
            on_explore_progression(session.state, base_dir=root)
            gareth2 = progression_status(session.state, base_dir=root)["heroes"]["gareth_ironshield"]
            self.assertGreater(int(gareth2["xp"]), before_xp)

    def test_unlock_and_equip(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=4)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            init_heroes_from_party(session.state, base_dir=root)
            prog = session.state["flags"]["ecology"]["progression"]["heroes"]["gareth_ironshield"]
            prog["skill_points"] = 2
            prog["job_level"] = 2
            bad = unlock_skill(
                session.state, "gareth_ironshield", "not_a_real_skill", base_dir=root
            )
            self.assertFalse(bad["ok"])
            ok = unlock_skill(
                session.state, "gareth_ironshield", "iron_wall", base_dir=root
            )
            self.assertTrue(ok["ok"])
            eq = equip_item(
                session.state, "gareth_ironshield", "iron_sword", base_dir=root
            )
            self.assertTrue(eq["ok"])
            self.assertEqual(
                prog["equipment"].get("weapon"),
                "iron_sword",
            )


if __name__ == "__main__":
    unittest.main()
