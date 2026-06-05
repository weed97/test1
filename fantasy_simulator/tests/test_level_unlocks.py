"""Level unlock system — 300 skills/job, weapon mastery equip gates."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.level_unlocks import (  # noqa: E402
    can_wield_grade,
    grant_axis_xp,
    level_from_xp,
    normalize_hero_progress,
    skills_available_for_hero,
    sync_unlocked_skills,
    unlock_status_for_hero,
    xp_threshold_for_level,
)
from utils.skill_catalog import (  # noqa: E402
    catalog_skill,
    catalog_skill_count_for_job,
    catalog_skills_for_job,
    effective_skill_power,
    load_progression_unlocks_config,
)


class LevelUnlockTests(unittest.TestCase):
    def test_three_hundred_skills_per_job(self) -> None:
        with isolated_game_root() as root:
            unlocks = load_progression_unlocks_config(root)
            target = int(unlocks["skill_catalog"]["skills_per_job"])
            self.assertEqual(len(unlocks["jobs"]), 8)
            for job in unlocks["jobs"]:
                self.assertEqual(catalog_skill_count_for_job(job, base_dir=root), target)

    def test_category_distribution(self) -> None:
        with isolated_game_root() as root:
            skills = catalog_skills_for_job("knight", base_dir=root)
            cats: dict[str, int] = {}
            for s in skills:
                cats[s["category"]] = cats.get(s["category"], 0) + 1
            self.assertEqual(cats.get("attack"), 80)
            self.assertEqual(cats.get("passive"), 40)
            self.assertEqual(sum(cats.values()), 300)

    def test_unlock_levels_span_one_to_999(self) -> None:
        with isolated_game_root() as root:
            skills = catalog_skills_for_job("knight", base_dir=root)
            atk = [s for s in skills if s["category"] == "attack"]
            levels = [s["unlock_requirements"]["job_level"] for s in atk]
            self.assertEqual(min(levels), 1)
            self.assertEqual(max(levels), 999)

    def test_low_level_hero_few_skills(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress(
                {
                    "active_job_id": "knight",
                    "character_level": 1,
                    "jobs": {"knight": {"level": 1, "xp": 0}},
                    "weapon_masteries": {"two_handed_sword": {"level": 1, "xp": 0}},
                    "unlocked_skills": [],
                },
                base_dir=root,
            )
            avail = skills_available_for_hero(hero, base_dir=root)
            self.assertGreater(len(avail), 0)
            self.assertLess(len(avail), 30)

    def test_high_level_unlocks_many_skills(self) -> None:
        with isolated_game_root() as root:
            hero = {
                "active_job_id": "knight",
                "character_level": 999,
                "jobs": {"knight": {"level": 999, "xp": 0}},
                "weapon_masteries": {"two_handed_sword": {"level": 999, "xp": 0}},
                "unlocked_skills": [],
            }
            sync_unlocked_skills(hero, base_dir=root)
            self.assertGreaterEqual(len(hero["unlocked_skills"]), 280)

    def test_skill_power_scales_with_level(self) -> None:
        with isolated_game_root() as root:
            sdef = catalog_skill("knight_atk_080", base_dir=root)
            assert sdef
            low = effective_skill_power(sdef, hero_levels={"job_level": 50, "character_level": 50, "job_skill_enhance_tier": 1})
            high = effective_skill_power(
                sdef,
                hero_levels={"job_level": 900, "character_level": 900, "job_skill_enhance_tier": 5},
            )
            self.assertGreater(high, low)

    def test_grant_axis_xp_unlocks(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress(
                {"active_job_id": "ranger", "jobs": {"ranger": {"level": 1, "xp": 0}}},
                base_dir=root,
            )
            before = len(hero.get("unlocked_skills", []))
            lines = grant_axis_xp(
                hero,
                character_xp=500_000,
                job_xp=500_000,
                weapon_xp=500_000,
                weapon_class="bow",
                base_dir=root,
            )
            self.assertGreater(len(hero.get("unlocked_skills", [])), before)
            self.assertTrue(any("성장" in ln for ln in lines))

    def test_mythic_wield_gate(self) -> None:
        with isolated_game_root() as root:
            weak = normalize_hero_progress(
                {
                    "character_level": 100,
                    "jobs": {"knight": {"level": 100}},
                    "weapon_masteries": {"two_handed_sword": {"level": 100}},
                },
                base_dir=root,
            )
            ok, _ = can_wield_grade(weak, "mythic", weapon_class="two_handed_sword", base_dir=root)
            self.assertFalse(ok)
            strong = normalize_hero_progress(
                {
                    "character_level": 600,
                    "jobs": {"knight": {"level": 600}},
                    "weapon_masteries": {"two_handed_sword": {"level": 750}},
                },
                base_dir=root,
            )
            ok2, _ = can_wield_grade(strong, "mythic", weapon_class="two_handed_sword", base_dir=root)
            self.assertTrue(ok2)

    def test_unlock_status_shape(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress({"active_job_id": "knight"}, base_dir=root)
            st = unlock_status_for_hero(hero, base_dir=root)
            self.assertEqual(st["skills"]["job_total"], 300)
            self.assertIn("next_job_skills", st["skills"])

    def test_level_from_xp_reaches_999(self) -> None:
        formula = {"base": 80, "exponent": 1.82}
        need = xp_threshold_for_level(999, formula) + 1
        self.assertEqual(level_from_xp(need, formula, max_level=999), 999)


if __name__ == "__main__":
    unittest.main()
