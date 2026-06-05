"""Arthur core skills — definitions, pipeline, agent_mind preview."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.agent_mind import preview_skill_damage  # noqa: E402
from utils.combat_stats import (  # noqa: E402
    build_combatant_snapshot,
    load_combat_bundle,
    preview_arthur_skill_damage,
    resolve_arthur_skill,
)
from utils.ecology_objects import skill_definition  # noqa: E402

ARTHUR_SKILLS = [
    "sovereign_blade_combo",
    "sovereign_broad_cleave",
    "kings_aegis",
    "excalibur_sovereign_judgment",
    "sovereign_wish_rite",
]


class ArthurSkillsTests(unittest.TestCase):
    def test_arthur_combatant_has_five_skills(self) -> None:
        with isolated_game_root() as root:
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            self.assertEqual(arthur["skills"], ARTHUR_SKILLS)

    def test_equipment_skills_match_combatant(self) -> None:
        with isolated_game_root() as root:
            bundle = load_combat_bundle(root)
            wpn = bundle["equipment"]["weapons"]["excalibur_sovereign_blade"]
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            self.assertEqual(list(wpn["skills"]), list(arthur["skills"]))

    def test_all_skills_defined(self) -> None:
        with isolated_game_root() as root:
            for sk in ARTHUR_SKILLS:
                sdef = skill_definition(sk, base_dir=root)
                self.assertIn("combat_pipeline", sdef)
                self.assertIn("label", sdef)

    def test_blade_combo_10k_cap(self) -> None:
        with isolated_game_root() as root:
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            elite = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            result = resolve_arthur_skill(
                "sovereign_blade_combo", arthur, [elite], base_dir=root, rng=random.Random(1)
            )
            hit = result["results"][0]
            self.assertEqual(hit["per_hit_milli"], 10_000_000)
            self.assertEqual(hit["hits"], 3)
            self.assertEqual(hit["damage_milli"], 30_000_000)

    def test_broad_cleave_elite_survives(self) -> None:
        with isolated_game_root() as root:
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            elite = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            elite["distance_pixels"] = 30
            result = resolve_arthur_skill(
                "sovereign_broad_cleave", arthur, [elite], base_dir=root, rng=random.Random(1)
            )
            aoe = result["aoe"]
            self.assertFalse(aoe["ultimate"])
            self.assertFalse(aoe["results"][0]["killed"])
            self.assertEqual(aoe["results"][0]["damage_milli"], 5_000_000)

    def test_judgment_ultimate_kills(self) -> None:
        with isolated_game_root() as root:
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            elite = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            elite["distance_pixels"] = 20
            result = resolve_arthur_skill(
                "excalibur_sovereign_judgment",
                arthur,
                [elite],
                base_dir=root,
                rng=random.Random(1),
            )
            aoe = result["aoe"]
            self.assertTrue(aoe["ultimate"])
            self.assertTrue(aoe["results"][0]["killed"])

    def test_kings_aegis_buff_no_damage(self) -> None:
        with isolated_game_root() as root:
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            result = resolve_arthur_skill(
                "kings_aegis", arthur, [arthur], base_dir=root, rng=random.Random(1)
            )
            self.assertEqual(result["pipeline"], "sovereign_buff")
            self.assertIn("regen_per_sec_milli", result["buff"])
            self.assertGreater(result["buff"]["regen_per_sec_milli"], 0)

    def test_wish_rite_world_edict(self) -> None:
        with isolated_game_root() as root:
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            result = resolve_arthur_skill(
                "sovereign_wish_rite", arthur, [], base_dir=root, rng=random.Random(1)
            )
            self.assertEqual(result["pipeline"], "world_edict")
            self.assertEqual(result["wish_interval_years"], 4)
            self.assertIn("extinct_race", result["forbidden_edicts"])
            self.assertFalse(result["combat_damage"])

    def test_preview_arthur_skill_damage_paths(self) -> None:
        with isolated_game_root() as root:
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            elite = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            elite["distance_pixels"] = 0
            combo = preview_arthur_skill_damage(
                arthur, elite, "sovereign_blade_combo", base_dir=root, rng=random.Random(1)
            )
            self.assertEqual(combo["damage_milli"], 10_000_000)
            cleave = preview_arthur_skill_damage(
                arthur, elite, "sovereign_broad_cleave", base_dir=root, rng=random.Random(1)
            )
            self.assertEqual(cleave["damage_milli"], 5_000_000)

    def test_agent_mind_preview_arthur(self) -> None:
        with isolated_game_root() as root:
            arthur_agent = {
                "archetype_id": "npc_arthur_pendragon",
                "world_sovereign_holder": True,
                "combatant_preset": "npc_arthur_pendragon",
            }
            target = {"combatant_preset": "world_rank_02", "tier": "apex_elite"}
            rng = random.Random(1)
            dmg = preview_skill_damage(
                arthur_agent, target, "sovereign_blade_combo", base_dir=root, rng=rng
            )
            self.assertEqual(dmg, 10_000)
            aegis = preview_skill_damage(
                arthur_agent, target, "kings_aegis", base_dir=root, rng=rng
            )
            self.assertEqual(aegis, 0)


if __name__ == "__main__":
    unittest.main()
