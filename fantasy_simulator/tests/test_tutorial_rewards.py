"""Tutorial copper stipends before kingdom founding."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.currency import wallet_to_copper  # noqa: E402
from utils.kingdom_system import founding_cost_preview  # noqa: E402
from utils.tutorial_rewards import apply_tutorial_reward, tutorial_progress_summary  # noqa: E402


class TutorialRewardsTests(unittest.TestCase):
    def test_explore_grants_copper_not_gold(self) -> None:
        with isolated_game_root() as root:
            from utils.currency import ensure_wallet, get_wallet
            from utils.game_session import GameSession

            session = GameSession.from_root(root, mode="rule", seed=5)
            state = session.state
            state.setdefault("flags", {})["game_mode"] = "hybrid"
            ensure_wallet(state, base_dir=root)
            before = wallet_to_copper(get_wallet(state, base_dir=root), base_dir=root)
            lines = apply_tutorial_reward(state, "explore", base_dir=root)
            after = wallet_to_copper(get_wallet(state, base_dir=root), base_dir=root)
            self.assertGreater(after, before)
            self.assertEqual(int(get_wallet(state, base_dir=root).get("gold", 0)), 0)
            self.assertTrue(any("튜토리얼" in ln for ln in lines))

    def test_founding_preview_includes_tutorial(self) -> None:
        with isolated_game_root() as root:
            from utils.game_session import GameSession

            session = GameSession.from_root(root, mode="rule", seed=6)
            state = session.state
            preview = founding_cost_preview(state, base_dir=root)
            tut = preview.get("tutorial", {})
            self.assertTrue(tut.get("active"))
            self.assertTrue(tut.get("progress_path"))

    def test_summary_after_kingdom_inactive(self) -> None:
        with isolated_game_root() as root:
            from tests.test_kingdom_system import _ready_for_kingdom
            from utils.currency import grant
            from utils.game_session import GameSession
            from utils.kingdom_system import complete_kingdom_founding

            session = GameSession.from_root(root, mode="rule", seed=7)
            state = session.state
            grant(state, gold=500, base_dir=root)
            _ready_for_kingdom(state, root)
            complete_kingdom_founding(
                state,
                map_id="ashpoint_01",
                x=1,
                y=1,
                name="튜토리얼 종료",
                doctrine_id="martial_ascendancy",
                base_dir=root,
            )
            summary = tutorial_progress_summary(state, base_dir=root)
            self.assertFalse(summary.get("active"))
