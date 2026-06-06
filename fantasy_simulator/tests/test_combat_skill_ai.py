"""Combat skill AI — situational pick, Arthur sovereign."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.combat_skill_ai import pick_combat_skill  # noqa: E402
from utils.level_unlocks import grant_axis_xp, normalize_hero_progress  # noqa: E402
from utils.skill_names import SIGNATURE_SKILLS  # noqa: E402


class CombatSkillAiTests(unittest.TestCase):
    def test_paladin_has_named_milestone_skill(self) -> None:
        with isolated_game_root() as root:
            from utils.ecology_objects import skill_definition

            sdef = skill_definition("paladin_atk_080", base_dir=root)
            self.assertEqual(sdef.get("label"), "신성 강하")
            self.assertIn("paladin_atk_080", SIGNATURE_SKILLS["paladin"])

    def test_high_level_knight_picks_attack(self) -> None:
        with isolated_game_root() as root:
            hero = normalize_hero_progress(
                {
                    "active_job_id": "knight",
                    "character_level": 400,
                    "jobs": {"knight": {"level": 400, "xp": 0}},
                    "weapon_masteries": {"two_handed_sword": {"level": 400, "xp": 0}},
                },
                base_dir=root,
            )
            grant_axis_xp(hero, job_xp=1, base_dir=root)
            hero["skills"] = list(hero.get("unlocked_skills", []))
            hero["mp"] = 500
            hero["hp"] = 100
            hero["max_hp"] = 100
            target = {"hp": 80, "max_hp": 80, "stats": {"vit": 10}}
            sk = pick_combat_skill(
                hero, target, base_dir=root, distance=1, rng=random.Random(1)
            )
            self.assertIsNotNone(sk)
            self.assertTrue(str(sk).startswith("knight_") or str(sk).startswith("wpn_"))

    def test_arthur_picks_judgment_when_critical(self) -> None:
        with isolated_game_root() as root:
            arthur = {
                "archetype_id": "npc_arthur_pendragon",
                "world_sovereign_holder": True,
                "skills": [
                    "sovereign_blade_combo",
                    "sovereign_broad_cleave",
                    "kings_aegis",
                    "excalibur_sovereign_judgment",
                ],
                "skill_cooldowns": {},
                "hp": 10,
                "max_hp": 100,
                "mp": 500,
            }
            target = {"hp": 50, "max_hp": 50}
            sk = pick_combat_skill(
                arthur,
                target,
                base_dir=root,
                distance=1,
                rng=random.Random(1),
                enemy_count=5,
            )
            self.assertEqual(sk, "excalibur_sovereign_judgment")

    def test_out_of_combat_wish_not_picked_in_combat(self) -> None:
        with isolated_game_root() as root:
            arthur = {
                "archetype_id": "npc_arthur_pendragon",
                "world_sovereign_holder": True,
                "skills": [
                    "sovereign_blade_combo",
                    "sovereign_wish_rite",
                ],
                "skill_cooldowns": {},
                "hp": 80,
                "max_hp": 100,
                "mp": 500,
            }
            target = {"hp": 50, "max_hp": 50}
            sk = pick_combat_skill(
                arthur, target, base_dir=root, distance=1, rng=random.Random(2)
            )
            self.assertEqual(sk, "sovereign_blade_combo")

    def test_eight_jobs_three_hundred_skills(self) -> None:
        with isolated_game_root() as root:
            from utils.skill_catalog import catalog_skill_count_for_job
            from utils.skill_catalog import load_progression_unlocks_config

            for job in load_progression_unlocks_config(root)["jobs"]:
                self.assertEqual(catalog_skill_count_for_job(job, base_dir=root), 300)


if __name__ == "__main__":
    unittest.main()
