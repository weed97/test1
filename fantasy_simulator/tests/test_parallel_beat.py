"""Parallel beat — simultaneous resolve on shared targets."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.ecology_objects import normalize_agent  # noqa: E402
from utils.field_agents import get_agents  # noqa: E402
from utils.parallel_beat import (  # noqa: E402
    parallel_beat_enabled,
    resolve_and_commit_field_beat,
    run_world_parallel_beat,
)
from utils.game_session import GameSession  # noqa: E402


class ParallelBeatTests(unittest.TestCase):
    def test_parallel_enabled_in_ecology_by_default(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=1)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            self.assertTrue(parallel_beat_enabled(session.state, base_dir=root))

    def test_simultaneous_damage_on_shared_target(self) -> None:
        with isolated_game_root() as root:
            rng = random.Random(7)
            base_stats = {"str": 20, "int": 10, "dex": 10, "vit": 10}
            attacker_a = {
                "instance_id": "atk_a",
                "label": "Alpha",
                "map_id": "test_map",
                "x": 0,
                "y": 0,
                "hp": 50,
                "max_hp": 50,
                "mp": 10,
                "max_mp": 10,
                "kind": "monster",
                "stats": dict(base_stats),
                "plunder": {},
            }
            attacker_b = {
                "instance_id": "atk_b",
                "label": "Beta",
                "map_id": "test_map",
                "x": 1,
                "y": 0,
                "hp": 50,
                "max_hp": 50,
                "mp": 10,
                "max_mp": 10,
                "kind": "monster",
                "stats": dict(base_stats),
                "plunder": {},
            }
            target = {
                "instance_id": "tgt",
                "label": "Prey",
                "map_id": "test_map",
                "x": 0,
                "y": 1,
                "hp": 30,
                "max_hp": 30,
                "mp": 5,
                "max_mp": 5,
                "kind": "monster",
                "stats": dict(base_stats),
            }
            for a in (attacker_a, attacker_b, target):
                normalize_agent(a, base_dir=root)

            agents_by_id = {
                attacker_a["instance_id"]: attacker_a,
                attacker_b["instance_id"]: attacker_b,
                target["instance_id"]: target,
            }
            dmg_a, dmg_b = 10, 12
            plans = [
                {
                    "actor_id": "atk_a",
                    "actor_label": "Alpha",
                    "priority": 50,
                    "action": "attack",
                    "target_id": "tgt",
                    "target_label": "Prey",
                    "base_damage": dmg_a,
                },
                {
                    "actor_id": "atk_b",
                    "actor_label": "Beta",
                    "priority": 40,
                    "action": "attack",
                    "target_id": "tgt",
                    "target_label": "Prey",
                    "base_damage": dmg_b,
                },
            ]
            state = {"flags": {"ecology": {"agents": list(agents_by_id.values())}}}
            maps = {"test_map": {"width": 8, "height": 8}}
            resolve_and_commit_field_beat(
                plans,
                agents_by_id,
                maps,
                state=state,
                base_dir=root,
                rng=rng,
                eco_cfg={"settlement_stages": []},
            )
            self.assertEqual(int(target["hp"]), 30 - dmg_a - dmg_b)

    def test_world_parallel_beat_sets_mode(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=11)
            flags = session.state.setdefault("flags", {})
            flags["game_mode"] = "ecology"
            session.state["world"]["map_id"] = "forest_01"
            lines = run_world_parallel_beat(session.state, base_dir=root, turn=1)
            eco = flags.setdefault("ecology", {})
            self.assertEqual(eco.get("beat_mode"), "parallel")
            self.assertIn("last_parallel_beat", eco)
            self.assertTrue(lines or get_agents(session.state))


if __name__ == "__main__":
    unittest.main()
