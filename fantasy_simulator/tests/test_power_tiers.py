"""Demigod HP 1M, apex mortal 99,999, armor-pierce vs chip damage."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.combat_precision import (  # noqa: E402
    hp_cap_milli_for_tier,
    load_combat_precision_config,
    load_power_tiers_config,
    resolve_strike_damage_milli,
)
from utils.sovereign_siege import (  # noqa: E402
    estimate_mob_army_net_hp_per_sec_milli,
    load_arthur_siege_math_config,
    wounded_regen_per_sec_milli,
    load_arthur_coalition_config,
)


class PowerTierTests(unittest.TestCase):
    def setUp(self) -> None:
        with isolated_game_root() as root:
            self.combat = load_combat_precision_config(root)
            self.tiers = load_power_tiers_config(root)
            self.siege = load_arthur_siege_math_config(root)
            self.coalition = load_arthur_coalition_config(root)
        self.rng = random.Random(7)

    def test_demigod_hp_cap_one_million(self) -> None:
        cap = hp_cap_milli_for_tier("demigod", tiers_cfg=self.tiers)
        self.assertEqual(cap, 1_000_000_000)

    def test_apex_mortal_hp_cap_99999(self) -> None:
        cap = hp_cap_milli_for_tier("apex_mortal", tiers_cfg=self.tiers)
        demi = hp_cap_milli_for_tier("demigod", tiers_cfg=self.tiers)
        self.assertEqual(cap, 99_999_000)
        self.assertGreater(demi, cap * 10)

    def test_apex_mythic_max_chips_one_vs_arthur(self) -> None:
        atk = {
            "attack_milli": 100_000_000,
            "character_level": 999,
            "weapon_mastery_level": 999,
            "item_grade_index": 6,
            "tier": "apex_mortal",
        }
        defn = {"defense_milli": 100_000_000, "tier": "demigod", "world_sovereign": True}
        r = resolve_strike_damage_milli(
            atk, defn, cfg=self.combat, rng=self.rng, force_hit=True, force_crit=False
        )
        self.assertLessEqual(r["damage_milli"], 1000)
        self.assertEqual(r.get("armor_pierce_milli", 0), 0)

    def test_demigod_pierce_9999_vs_arthur(self) -> None:
        atk = {
            "attack_milli": 100_000_000,
            "tier": "demigod",
            "armor_pierce": True,
            "character_level": 999,
            "weapon_mastery_level": 999,
        }
        defn = {"defense_milli": 100_000_000, "tier": "demigod"}
        r = resolve_strike_damage_milli(
            atk, defn, cfg=self.combat, rng=self.rng, force_hit=True, force_crit=False
        )
        self.assertGreaterEqual(r.get("armor_pierce_milli", 0), 9_000_000)

    def test_mob_million_army_cannot_out_dps_regen(self) -> None:
        net = estimate_mob_army_net_hp_per_sec_milli(
            siege_cfg=self.siege, combat_cfg=self.combat
        )
        regen = wounded_regen_per_sec_milli(
            siege_cfg=self.siege,
            coalition_cfg=self.coalition,
            wound_stacks=1,
            contested=False,
        )
        self.assertLess(net, regen)


if __name__ == "__main__":
    unittest.main()
