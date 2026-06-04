"""Tests for world tension tiers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.world_tension import (  # noqa: E402
    adjust_tension,
    event_weight_multiplier,
    get_tier,
    passive_drift,
    tier_for_value,
)


class WorldTensionTests(unittest.TestCase):
    def test_tier_boundaries(self) -> None:
        self.assertEqual(tier_for_value(10)["id"], "calm")
        self.assertEqual(tier_for_value(30)["id"], "uneasy")
        self.assertEqual(tier_for_value(51)["id"], "tense")
        self.assertEqual(tier_for_value(80)["id"], "crisis")

    def test_event_weight_scales_with_tension(self) -> None:
        calm = {"world": {"tension": 10}}
        crisis = {"world": {"tension": 85}}
        seed = {"tension_tags": ["crisis"]}
        self.assertLess(event_weight_multiplier(calm, seed), event_weight_multiplier(crisis, seed))

    def test_passive_drift_seal_broken(self) -> None:
        state = {"world": {"tension": 40}, "flags": {"world_seal_broken": True}}
        delta, note = passive_drift(state)
        self.assertGreater(delta, 0)
        self.assertIsNotNone(note)

    def test_get_tier_from_state(self) -> None:
        state = {"world": {"tension": 51}}
        self.assertEqual(get_tier(state)["label_ko"], "긴장")
        adjust_tension(state, -26)
        self.assertEqual(get_tier(state)["id"], "uneasy")


if __name__ == "__main__":
    unittest.main()
