"""Combat stats builder + strike pipeline."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.combat_stats import (  # noqa: E402
    build_combatant_snapshot,
    combat_power_estimate,
    compute_skill_damage,
    elite_coalition_pierce_dps,
    elite_pierce_dps,
    load_combat_bundle,
    resolve_excalibur_aoe,
    strike_damage_milli,
)
from utils.sovereign_siege import (  # noqa: E402
    estimate_coalition_siege_seconds,
    load_arthur_coalition_config,
    tick_sovereign_coalition_siege,
)


class CombatStatsTests(unittest.TestCase):
    def test_arthur_snapshot(self) -> None:
        with isolated_game_root() as root:
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            self.assertEqual(arthur["tier"], "demigod")
            self.assertEqual(arthur["hp_milli"], 1_000_000_000)
            self.assertTrue(arthur["armor_pierce"])
            self.assertGreater(combat_power_estimate(arthur, base_dir=root), 1000)

    def test_apex_without_through_zero(self) -> None:
        with isolated_game_root() as root:
            rng = random.Random(1)
            atk = build_combatant_snapshot(base_dir=root, preset_id="apex_knight_lv999")
            defn = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            r = strike_damage_milli(
                atk, defn, base_dir=root, rng=rng, force_hit=True, force_sovereign_through=False
            )
            self.assertEqual(r["damage_milli"], 0)

    def test_apex_through_9999(self) -> None:
        with isolated_game_root() as root:
            rng = random.Random(1)
            atk = build_combatant_snapshot(base_dir=root, preset_id="apex_knight_lv999")
            defn = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            r = strike_damage_milli(
                atk, defn, base_dir=root, rng=rng, force_hit=True, force_sovereign_through=True
            )
            self.assertGreaterEqual(r["damage_milli"], 9_999_000)

    def test_siege_anchor_25000s(self) -> None:
        with isolated_game_root() as root:
            coalition = load_arthur_coalition_config(root)
            self.assertEqual(estimate_coalition_siege_seconds(coalition_cfg=coalition), 25_000)
            self.assertEqual(int(coalition["siege"]["mob_army"]["net_dps_milli"]), 40_000)

    def test_siege_tick_runs(self) -> None:
        with isolated_game_root() as root:
            state: dict = {"flags": {"ecology": {}}}
            lines = tick_sovereign_coalition_siege(state, base_dir=root)
            self.assertIn("world_sovereign", state["flags"])
            self.assertIsInstance(lines, list)

    def test_rank2_pierce_dps_1000(self) -> None:
        with isolated_game_root() as root:
            bundle = load_combat_bundle(root)
            self.assertEqual(elite_pierce_dps(2, bundle=bundle), 1000.0)
            rank2 = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            self.assertEqual(rank2["pierce_dps_milli"], 1_000_000)

    def test_elite_hits_arthur_with_partial_pierce(self) -> None:
        with isolated_game_root() as root:
            rng = random.Random(1)
            atk = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            defn = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            r = strike_damage_milli(
                atk, defn, base_dir=root, rng=rng, force_hit=True, force_sovereign_through=False
            )
            self.assertGreater(r["damage_milli"], 0)
            self.assertGreater(r.get("partial_pierce_milli", 0), 0)

    def test_elite_coalition_combined_dps(self) -> None:
        with isolated_game_root() as root:
            bundle = load_combat_bundle(root)
            coal = elite_coalition_pierce_dps(bundle=bundle)
            self.assertGreater(coal["combined_pierce_dps"], 3000)
            self.assertLess(coal["combined_pierce_dps"], 8500)
            self.assertLessEqual(coal["seconds_to_kill_arthur"], 400)

    def test_elite_hp_500k(self) -> None:
        with isolated_game_root() as root:
            elite = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            self.assertEqual(elite["hp_milli"], 500_000_000)

    def test_arthur_aoe_elite_survives_normal_ultimate_kills(self) -> None:
        with isolated_game_root() as root:
            bundle = load_combat_bundle(root)
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            elite = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            elite["distance_pixels"] = 30
            normal = resolve_excalibur_aoe(arthur, [elite], bundle=bundle, ultimate=False)
            ult = resolve_excalibur_aoe(arthur, [elite], bundle=bundle, ultimate=True)
            self.assertFalse(normal["results"][0]["killed"])
            self.assertLess(normal["results"][0]["damage_milli"], elite["hp_milli"])
            self.assertTrue(ult["results"][0]["killed"])
            self.assertTrue(ult["casts_skill_lock"])

    def test_ultimate_mage_only_vital_dodge_10px(self) -> None:
        with isolated_game_root() as root:
            bundle = load_combat_bundle(root)
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            mage = build_combatant_snapshot(base_dir=root, preset_id="world_rank_02")
            knight = build_combatant_snapshot(base_dir=root, preset_id="world_rank_03")
            mage["job_id"] = "mage"
            mage["distance_pixels"] = 91
            knight["distance_pixels"] = 91
            ult = resolve_excalibur_aoe(arthur, [mage, knight], bundle=bundle, ultimate=True)
            by_id = {r["target_id"]: r for r in ult["results"]}
            self.assertFalse(by_id[mage["id"]]["killed"])
            self.assertEqual(by_id[mage["id"]]["vital_dodge_pixels"], 10)
            self.assertTrue(by_id[knight["id"]]["killed"])

    def test_full_coalition_cluster_ultimate_wipe(self) -> None:
        with isolated_game_root() as root:
            bundle = load_combat_bundle(root)
            arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
            targets = []
            for r in range(2, 12):
                t = build_combatant_snapshot(base_dir=root, preset_id=f"world_rank_{r:02d}")
                t["distance_pixels"] = 25
                targets.append(t)
            ult = resolve_excalibur_aoe(arthur, targets, bundle=bundle, ultimate=True)
            self.assertEqual(ult["kills"], 10)
            self.assertTrue(ult["cluster_wipe"]["full_coalition_clustered"])

    def test_mythic_skill_scaling(self) -> None:
        with isolated_game_root() as root:
            bundle = load_combat_bundle(root)
            snap = {
                "primary": {"str": 1000, "int": 500},
                "character_level": 920,
                "weapon_grade": "mythic",
                "world_apex_rank": 2,
                "mythic_3t_weapon": True,
            }
            r = compute_skill_damage(
                snap, bundle=bundle, skill_power_percent=700, skill_kind="melee_phys_single", crit=True
            )
            self.assertGreater(r["total_damage"], 1000)
            self.assertGreater(r["pierce_damage"], 100)


if __name__ == "__main__":
    unittest.main()
