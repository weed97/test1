"""Power tiers + probabilistic through — via combat_stats."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.combat_precision import load_combat_precision_config, roll_sovereign_through  # noqa: E402
from utils.combat_stats import build_combatant_snapshot, hp_cap_milli_for, load_combat_bundle  # noqa: E402


class PowerTierTests(unittest.TestCase):
    def test_hp_caps(self) -> None:
        with isolated_game_root() as root:
            bundle = load_combat_bundle(root)
            self.assertEqual(hp_cap_milli_for("demigod", bundle=bundle), 1_000_000_000)
            self.assertEqual(hp_cap_milli_for("apex_mortal", bundle=bundle), 99_999_000)

    def test_through_rate_monte_carlo(self) -> None:
        with isolated_game_root() as root:
            combat = load_combat_precision_config(root)
            rng = random.Random(99)
            procs = sum(1 for _ in range(500_000) if roll_sovereign_through(rng, cfg=combat))
            self.assertGreater(procs, 2)
            self.assertLess(procs, 12)

    def test_mob_preset_builds(self) -> None:
        with isolated_game_root() as root:
            mob = build_combatant_snapshot(base_dir=root, preset_id="grand_coalition_mob")
            self.assertEqual(mob["tier"], "mortal")
            self.assertGreater(mob["attack_milli"], 0)


if __name__ == "__main__":
    unittest.main()
