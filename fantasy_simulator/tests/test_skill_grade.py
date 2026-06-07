"""Skill grade bands — Lv1-100 common … Lv801-999 mythic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.level_unlocks import (  # noqa: E402
    grant_axis_xp,
    normalize_hero_progress,
    skills_available_for_hero,
)
from utils.skill_catalog import catalog_skills_for_job  # noqa: E402
from utils.skill_grade import (  # noqa: E402
    grade_for_unlock_level,
    hero_can_learn_grade,
    min_level_for_grade,
)
from utils.skill_tree import build_skill_tree  # noqa: E402


class SkillGradeTests(unittest.TestCase):
    def test_grade_bands_mapping(self) -> None:
        with isolated_game_root() as root:
            self.assertEqual(grade_for_unlock_level(50, base_dir=root), "common")
            self.assertEqual(grade_for_unlock_level(150, base_dir=root), "high")
            self.assertEqual(grade_for_unlock_level(300, base_dir=root), "rare")
            self.assertEqual(grade_for_unlock_level(500, base_dir=root), "hero")
            self.assertEqual(grade_for_unlock_level(700, base_dir=root), "legend")
            self.assertEqual(grade_for_unlock_level(900, base_dir=root), "mythic")

    def test_low_character_cannot_learn_hero_skills(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress(
                {
                    "active_job_id": "knight",
                    "character_level": 200,
                    "jobs": {"knight": {"level": 999, "xp": 0}},
                },
                base_dir=root,
            )
            available = skills_available_for_hero(hero, base_dir=root)
            grades = {
                str(s.get("skill_grade"))
                for s in catalog_skills_for_job("knight", base_dir=root)
                if str(s["skill_id"]) in available
            }
            self.assertNotIn("hero", grades)
            self.assertNotIn("legend", grades)
            self.assertNotIn("mythic", grades)

    def test_high_level_unlocks_mythic_band(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress(
                {
                    "active_job_id": "knight",
                    "character_level": 900,
                    "jobs": {"knight": {"level": 999, "xp": 0}},
                },
                base_dir=root,
            )
            grant_axis_xp(hero, base_dir=root)
            available = skills_available_for_hero(hero, base_dir=root)
            mythic_ids = [
                str(s["skill_id"])
                for s in catalog_skills_for_job("knight", base_dir=root)
                if str(s.get("skill_grade")) == "mythic"
            ]
            self.assertTrue(any(mid in available for mid in mythic_ids))

    def test_hero_skills_have_cooldown(self) -> None:
        with isolated_game_root() as root:
            hero_grade = [
                s
                for s in catalog_skills_for_job("ranger", base_dir=root)
                if str(s.get("skill_grade")) == "hero"
            ]
            self.assertTrue(hero_grade)
            self.assertGreaterEqual(int(hero_grade[0].get("cooldown_beats", 0)), 4)

    def test_skill_tree_exposes_grade_bands(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress({"active_job_id": "cleric"}, base_dir=root)
            tree = build_skill_tree(hero, base_dir=root)
            bands = tree.get("skill_grade_bands", [])
            self.assertEqual(len(bands), 6)
            self.assertEqual(bands[0]["grade"], "common")
            self.assertEqual(bands[-1]["min"], 801)
            atk = tree["categories"].get("attack", [])
            self.assertTrue(atk)
            self.assertIn("skill_grade", atk[0])

    def test_grade_gate_thresholds(self) -> None:
        with isolated_game_root() as root:
            self.assertFalse(hero_can_learn_grade(400, "hero", base_dir=root))
            self.assertTrue(hero_can_learn_grade(401, "hero", base_dir=root))
            self.assertEqual(min_level_for_grade("rare", base_dir=root), 201)


if __name__ == "__main__":
    unittest.main()
