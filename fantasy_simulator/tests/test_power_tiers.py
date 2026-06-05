"""Demigod HP, sovereign through (1/100k), coalition siege anchor."""

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
    roll_sovereign_through,
)
from utils.sovereign_siege import (  # noqa: E402
    coalition_net_dps_milli,
    estimate_coalition_siege_seconds,
    load_arthur_coalition_config,
    load_arthur_siege_math_config,
    wounded_regen_per_sec_milli,
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

    def test_apex_no_through_deals_zero(self) -> None:
        atk = {
            "attack_milli": 100_000_000,
            "character_level": 999,
            "weapon_mastery_level": 999,
            "tier": "apex_mortal",
        }
        defn = {"defense_milli": 100_000_000, "tier": "demigod", "world_sovereign": True}
        r = resolve_strike_damage_milli(
            atk,
            defn,
            cfg=self.combat,
            rng=self.rng,
            force_hit=True,
            force_sovereign_through=False,
        )
        self.assertEqual(r["damage_milli"], 0)
        self.assertFalse(r.get("sovereign_through"))

    def test_apex_on_through_deals_9999(self) -> None:
        atk = {
            "attack_milli": 100_000_000,
            "character_level": 999,
            "tier": "apex_mortal",
        }
        defn = {"defense_milli": 100_000_000, "tier": "demigod"}
        r = resolve_strike_damage_milli(
            atk,
            defn,
            cfg=self.combat,
            rng=self.rng,
            force_hit=True,
            force_sovereign_through=True,
        )
        self.assertGreaterEqual(r["damage_milli"], 9_999_000)
        self.assertTrue(r.get("sovereign_through"))

    def test_sovereign_through_rate_about_one_in_100k(self) -> None:
        rng = random.Random(99)
        procs = sum(1 for _ in range(500_000) if roll_sovereign_through(rng, cfg=self.combat))
        self.assertGreater(procs, 2)
        self.assertLess(procs, 12)

    def test_coalition_siege_25000_seconds(self) -> None:
        net = coalition_net_dps_milli(siege_cfg=self.siege)
        self.assertEqual(net, 40_000)
        secs = estimate_coalition_siege_seconds(siege_cfg=self.siege)
        self.assertEqual(secs, 25_000)
        regen = wounded_regen_per_sec_milli(
            siege_cfg=self.siege,
            coalition_cfg=self.coalition,
            wound_stacks=1,
            contested=False,
        )
        self.assertEqual(regen, 160_000)


if __name__ == "__main__":
    unittest.main()
