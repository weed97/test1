"""Unified agent planning — sequential and parallel share plan_agent_action."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.agent_mind import plan_agent_action  # noqa: E402
from utils.parallel_beat import plan_agent_beat  # noqa: E402


class AgentPlanningTests(unittest.TestCase):
    def test_parallel_plan_matches_shared_planner(self) -> None:
        with isolated_game_root() as root:
            rng = random.Random(11)
            agent = {
                "instance_id": "a1",
                "label": "Hunter",
                "map_id": "ashpoint_01",
                "x": 2,
                "y": 2,
                "hp": 40,
                "max_hp": 50,
                "mp": 10,
                "max_mp": 10,
                "kind": "monster",
                "stats": {"str": 14, "int": 8, "dex": 10, "vit": 10},
                "skills": [],
                "unlocked_skills": [],
                "relations": {},
                "intelligence": {"iq": 55, "strategy": "predator_pack"},
            }
            target = {
                "instance_id": "t1",
                "label": "Prey",
                "map_id": "ashpoint_01",
                "x": 3,
                "y": 2,
                "hp": 20,
                "max_hp": 20,
                "kind": "monster",
                "stats": {"str": 8, "int": 8, "dex": 8, "vit": 8},
            }
            agents_by_id = {agent["instance_id"]: agent, target["instance_id"]: target}
            others = [target]

            direct = plan_agent_action(agent, others, base_dir=root, rng=rng)
            via_parallel = plan_agent_beat(
                agent,
                agents_by_id,
                {},
                base_dir=root,
                rng=rng,
                eco_cfg={},
            )
            self.assertIsNotNone(via_parallel)
            assert via_parallel is not None
            for key in ("action", "target_id", "skill_id", "base_damage", "move_to"):
                if key in direct:
                    self.assertEqual(via_parallel.get(key), direct.get(key), key)


if __name__ == "__main__":
    unittest.main()
