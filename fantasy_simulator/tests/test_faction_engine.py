"""Tests for faction reputation system."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.faction_engine import FactionEngine  # noqa: E402


class FactionEngineTests(unittest.TestCase):
    def test_legacy_migration_maps_ashpoint(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"reputation": {"ashpoint": 55, "lilian": 8}}}
            engine.ensure_initialized(state)
            rep = state["flags"]["faction_reputation"]
            self.assertEqual(rep["ashpoint_council"], 5)
            self.assertEqual(rep["merchant_guild"], -42)

    def test_adjust_reputation_rival_spill(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"faction_reputation": {fid: 0 for fid in engine.faction_ids()}}}
            lines = engine.adjust_reputation(state, "ash_church", 20)
            self.assertTrue(any("잿불 교단" in line for line in lines))
            self.assertLess(state["flags"]["faction_reputation"]["void_circle"], 0)

    def test_tier_hostile_blocks_zone(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"faction_reputation": {fid: 0 for fid in engine.faction_ids()}}}
            state["flags"]["faction_reputation"]["merchant_guild"] = -50
            blocked, name = engine.is_zone_blocked(state, "ashpoint_plaza")
            self.assertFalse(blocked)
            state["flags"]["faction_reputation"]["ashpoint_council"] = -45
            blocked, name = engine.is_zone_blocked(state, "ashpoint_plaza")
            self.assertTrue(blocked)
            self.assertIn("자치회", name or "")

    def test_apply_reputation_outcome_legacy_keys(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"reputation": {"ashpoint": 50}, "faction_reputation": {fid: 0 for fid in engine.faction_ids()}}}
            lines = engine.apply_reputation_outcome(state, {"reputation": {"ashpoint": 10}})
            self.assertEqual(state["flags"]["faction_reputation"]["ashpoint_council"], 10)
            self.assertTrue(lines)


if __name__ == "__main__":
    unittest.main()
