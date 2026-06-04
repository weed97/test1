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
    def test_legacy_migration_maps_ashpoint_and_lilian(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"reputation": {"ashpoint": 55, "lilian": 8}}}
            engine.ensure_initialized(state)
            rep = state["flags"]["faction_reputation"]
            self.assertEqual(rep["ashpoint_council"], 5)
            self.assertEqual(rep["silverwood_trade_union"], -42)

    def test_relationship_spill_hostile_and_friendly(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"faction_reputation": {fid: 0 for fid in engine.faction_ids()}}}
            engine.adjust_reputation(state, "ashpoint_council", 20)
            rep = state["flags"]["faction_reputation"]
            self.assertLess(rep["blackfang_marauders"], 0)
            self.assertLess(rep["black_covenant"], 0)
            self.assertGreater(rep["silver_cross_order"], 0)

    def test_utilize_stance_mutual_gain(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"faction_reputation": {fid: 0 for fid in engine.faction_ids()}}}
            before_covenant = 0
            engine.adjust_reputation(state, "blackfang_marauders", 20)
            self.assertGreater(state["flags"]["faction_reputation"]["black_covenant"], before_covenant)

    def test_tier_hostile_blocks_zone(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"faction_reputation": {fid: 0 for fid in engine.faction_ids()}}}
            state["flags"]["faction_reputation"]["ashpoint_council"] = -45
            blocked, name = engine.is_zone_blocked(state, "ashpoint_plaza")
            self.assertTrue(blocked)
            self.assertIn("자치회", name or "")

    def test_milestone_queues_event(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"faction_reputation": {fid: 0 for fid in engine.faction_ids()}}}
            engine.adjust_reputation(state, "silver_cross_order", 45)
            pending = state["flags"]["pending_events"]
            self.assertIn("silver_cross_oath", pending)

    def test_legacy_faction_id_migration(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {
                "flags": {
                    "faction_reputation": {
                        "merchant_guild": 10,
                        "void_circle": -5,
                    }
                }
            }
            engine.ensure_initialized(state)
            rep = state["flags"]["faction_reputation"]
            self.assertEqual(rep["silverwood_trade_union"], 10)
            self.assertEqual(rep["black_covenant"], -5)
            self.assertNotIn("merchant_guild", rep)

    def test_player_reputation_mirror_in_factions(self) -> None:
        with isolated_game_root() as root:
            engine = FactionEngine(root)
            state = {"flags": {"faction_reputation": {fid: 0 for fid in engine.faction_ids()}}}
            engine.ensure_initialized(state)
            mirror = state["factions"]["player_reputation"]["ashpoint_council"]
            self.assertEqual(mirror["value"], 0)
            self.assertIn("tier", mirror)


if __name__ == "__main__":
    unittest.main()
