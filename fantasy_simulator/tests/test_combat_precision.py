"""Mill-precision combat — 0.001 sensitivity and balance guards."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.combat_precision import (  # noqa: E402
    apply_mitigation_milli,
    compute_crit_rate_milli,
    compute_hit_rate_milli,
    from_milli,
    load_combat_precision_config,
    resolve_strike_damage_milli,
    to_milli,
)


class CombatPrecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        with isolated_game_root() as root:
            self.cfg = load_combat_precision_config(root)
        self.rng = random.Random(42)

    def test_milli_roundtrip(self) -> None:
        self.assertEqual(to_milli(45.125, cfg=self.cfg), 45125)
        self.assertAlmostEqual(from_milli(45125, cfg=self.cfg), 45.125)

    def test_defense_plus_one_reduces_damage(self) -> None:
        atk = {"attack_milli": 400_000, "character_level": 100, "weapon_mastery_level": 100}
        def_a = {"defense_milli": 50_000, "character_level": 100, "weapon_mastery_level": 100}
        def_b = {"defense_milli": 51_000, "character_level": 100, "weapon_mastery_level": 100}
        r_a = resolve_strike_damage_milli(
            atk, def_a, cfg=self.cfg, rng=self.rng, force_hit=True, force_crit=False
        )
        r_b = resolve_strike_damage_milli(
            atk, def_b, cfg=self.cfg, rng=self.rng, force_hit=True, force_crit=False
        )
        min_drop = int(self.cfg["sensitivity_targets"]["defense_plus_1_000_reduces_damage_at_least_milli"])
        self.assertGreater(r_a["damage_milli"] - r_b["damage_milli"], min_drop)

    def test_attack_plus_one_increases_damage(self) -> None:
        defn = {"defense_milli": 40_000, "character_level": 50, "weapon_mastery_level": 50}
        r_a = resolve_strike_damage_milli(
            {"attack_milli": 80_000, "character_level": 50, "weapon_mastery_level": 50},
            defn,
            cfg=self.cfg,
            rng=self.rng,
            force_hit=True,
            force_crit=False,
        )
        r_b = resolve_strike_damage_milli(
            {"attack_milli": 81_000, "character_level": 50, "weapon_mastery_level": 50},
            defn,
            cfg=self.cfg,
            rng=self.rng,
            force_hit=True,
            force_crit=False,
        )
        min_gain = int(self.cfg["sensitivity_targets"]["attack_plus_1_000_increases_damage_at_least_milli"])
        self.assertGreater(r_b["damage_milli"] - r_a["damage_milli"], min_gain)

    def test_character_level_beats_grade_when_gap_large(self) -> None:
        low_char_high_grade = {
            "attack_milli": 50_000,
            "character_level": 10,
            "weapon_mastery_level": 10,
            "item_grade_index": 6,
        }
        high_char_low_grade = {
            "attack_milli": 50_000,
            "character_level": 200,
            "weapon_mastery_level": 200,
            "item_grade_index": 0,
        }
        defn = {"defense_milli": 20_000, "character_level": 100, "weapon_mastery_level": 100}
        r_low = resolve_strike_damage_milli(
            low_char_high_grade, defn, cfg=self.cfg, rng=self.rng, force_hit=True, force_crit=False
        )
        r_high = resolve_strike_damage_milli(
            high_char_low_grade, defn, cfg=self.cfg, rng=self.rng, force_hit=True, force_crit=False
        )
        self.assertGreater(r_high["damage_milli"], r_low["damage_milli"])

    def test_crit_and_hit_rates_bounded(self) -> None:
        atk = {"accuracy_milli": 999_999, "crit_rate_milli": 999_999}
        defn = {"evasion_milli": 999_999}
        hit = compute_hit_rate_milli(atk, defn, cfg=self.cfg)
        crit = compute_crit_rate_milli(atk, cfg=self.cfg)
        self.assertLessEqual(hit, int(self.cfg["evasion"]["max_hit_rate"]))
        self.assertGreaterEqual(hit, int(self.cfg["evasion"]["min_hit_rate"]))
        self.assertLessEqual(crit, int(self.cfg["critical"]["max_rate"]))

    def test_mitigation_monotonic(self) -> None:
        a1 = apply_mitigation_milli(200_000, 10_000, cfg=self.cfg)
        a2 = apply_mitigation_milli(200_000, 11_000, cfg=self.cfg)
        self.assertGreater(a1, a2)


if __name__ == "__main__":
    unittest.main()
