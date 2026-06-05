"""Skill tree API payload."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.level_unlocks import grant_axis_xp, normalize_hero_progress  # noqa: E402
from utils.skill_tree import build_skill_tree  # noqa: E402


class SkillTreeTests(unittest.TestCase):
    def test_build_skill_tree_categories(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress(
                {"active_job_id": "assassin", "jobs": {"assassin": {"level": 50, "xp": 0}}},
                base_dir=root,
            )
            grant_axis_xp(hero, job_xp=100_000, base_dir=root)
            tree = build_skill_tree(hero, base_dir=root, character_id="test_hero")
            self.assertEqual(tree["job_id"], "assassin")
            self.assertIn("attack", tree["categories"])
            self.assertGreater(tree["counts"]["job_unlocked"], 0)
            self.assertEqual(tree["counts"]["job_total"], 300)

    def test_signatures_present(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress({"active_job_id": "cleric"}, base_dir=root)
            tree = build_skill_tree(hero, base_dir=root)
            self.assertIn("cleric_sup_060", tree["signatures"])


if __name__ == "__main__":
    unittest.main()
