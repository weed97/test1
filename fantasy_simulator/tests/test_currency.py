"""Copper / silver / gold wallet."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.currency import (  # noqa: E402
    can_afford,
    ensure_wallet,
    grant,
    party_gold,
    spend,
    spend_gold_coins,
    wallet_to_copper,
)


class CurrencyTests(unittest.TestCase):
    def test_starting_wallet_is_copper_not_gold(self) -> None:
        with isolated_game_root() as root:
            from utils.game_session import GameSession

            session = GameSession.from_root(root, mode="rule", seed=1)
            w = ensure_wallet(session.state, base_dir=root)
            self.assertEqual(int(w.get("gold", 0)), 0)
            self.assertGreater(int(w.get("copper", 0)), 0)

    def test_spend_silver_for_settlement_cost(self) -> None:
        with isolated_game_root() as root:
            state = {"inventory": {"wallet": {"copper": 0, "silver": 5, "gold": 0}}}
            self.assertTrue(
                spend(state, {"copper": 0, "silver": 3, "gold": 0}, base_dir=root)
            )
            self.assertEqual(state["inventory"]["wallet"]["silver"], 2)

    def test_gold_coins_separate_from_silver(self) -> None:
        with isolated_game_root() as root:
            state = {"inventory": {"wallet": {"copper": 0, "silver": 99, "gold": 2}}}
            self.assertTrue(spend_gold_coins(state, 1, base_dir=root))
            self.assertEqual(party_gold(state, base_dir=root), 1)
            self.assertEqual(state["inventory"]["wallet"]["silver"], 99)

    def test_legacy_party_gold_migrates_to_copper_cap(self) -> None:
        with isolated_game_root() as root:
            state = {"inventory": {"party_gold": 80}}
            w = ensure_wallet(state, base_dir=root)
            self.assertEqual(int(w.get("gold", 0)), 0)
            self.assertLessEqual(wallet_to_copper(w, base_dir=root), 200)
