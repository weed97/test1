"""Arthur grand-coalition siege math — parallel sum, regen, instant-kill anchors."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.combat_precision import load_combat_precision_config  # noqa: E402
from utils.sovereign_siege import (  # noqa: E402
    coalition_strike_batch,
    hp_damage_from_raw_milli,
    load_arthur_coalition_config,
    load_arthur_siege_math_config,
    resolve_parallel_strikes_milli,
    tick_sovereign_coalition_siege,
    wounded_regen_per_sec_milli,
)


class SovereignSiegeTests(unittest.TestCase):
    def setUp(self) -> None:
        with isolated_game_root() as root:
            self.siege = load_arthur_siege_math_config(root)
            self.coalition = load_arthur_coalition_config(root)
            self.combat = load_combat_precision_config(root)

    def test_raw_100k_becomes_one_hp(self) -> None:
        raw = int(self.siege["mitigation_anchor"]["raw_soft_cap_milli"])
        dmg = hp_damage_from_raw_milli(raw, combat_cfg=self.combat, siege_cfg=self.siege)
        self.assertGreaterEqual(dmg, 500)
        self.assertLessEqual(dmg, 2000)

    def test_wounded_regen_is_160_per_sec(self) -> None:
        regen = wounded_regen_per_sec_milli(
            siege_cfg=self.siege,
            coalition_cfg=self.coalition,
            wound_stacks=1,
            contested=False,
        )
        self.assertEqual(regen, 160_000)

    def test_one_million_simultaneous_one_hp_hits_kill(self) -> None:
        hp = int(self.siege["arthur"]["hp_milli"])
        strikes = [1000] * 1_000_000
        r = resolve_parallel_strikes_milli(
            strikes,
            hp_milli_before=hp,
            siege_cfg=self.siege,
            coalition_cfg=self.coalition,
            wound_stacks=0,
            contested=True,
        )
        self.assertTrue(r["instant_kill"])
        self.assertEqual(r["hp_milli_after"], 0)

    def test_pierce_elite_squad_instant_kill(self) -> None:
        ex = self.siege["instant_kill_examples"]["elite_pierce_squad"]
        n = int(ex["attackers"])
        per = int(ex["hp_damage_per_striker_milli"])
        hp = int(self.siege["arthur"]["hp_milli"])
        r = resolve_parallel_strikes_milli(
            [per] * n,
            hp_milli_before=hp,
            siege_cfg=self.siege,
            coalition_cfg=self.coalition,
            contested=True,
        )
        self.assertTrue(r["instant_kill"])

    def test_coalition_batch_elite_fraction(self) -> None:
        strikes = coalition_strike_batch(
            striker_count=2000,
            elite_count=100,
            siege_cfg=self.siege,
            combat_cfg=self.combat,
        )
        self.assertEqual(len(strikes), 2000)
        self.assertEqual(strikes.count(1_000_000), 100)

    def test_tick_updates_state(self) -> None:
        with isolated_game_root() as root:
            state: dict = {"flags": {"ecology": {}}}
            lines = tick_sovereign_coalition_siege(state, base_dir=root)
            self.assertIn("world_sovereign", state["flags"])
            self.assertIn("last_sovereign_siege", state["flags"]["ecology"])
            self.assertIsInstance(lines, list)


if __name__ == "__main__":
    unittest.main()
