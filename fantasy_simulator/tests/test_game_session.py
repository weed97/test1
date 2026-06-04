"""Unit tests for GameSession (turn controller)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.main_story_engine import _current_turn  # noqa: E402


class GameSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._isolated = isolated_game_root()
        self.root = self._isolated.__enter__()

    def tearDown(self) -> None:
        self._isolated.__exit__(None, None, None)

    @property
    def session(self) -> GameSession:
        if not hasattr(self, "_session"):
            self._session = GameSession.from_root(self.root, mode="rule", seed=42)
        return self._session

    def test_from_root_loads_state(self) -> None:
        self.assertIn("world", self.session.state)
        self.assertEqual(self.session.mode, "rule")
        self.assertIsNone(self.session.client)

    def test_turn_counter_matches_event_log(self) -> None:
        self.assertEqual(self.session.turn, _current_turn(self.session.state) - 1)

    def test_ctx_bundles_dependencies(self) -> None:
        ctx = self.session.ctx("explore", turn=99)
        self.assertIs(ctx.state, self.session.state)
        self.assertIs(ctx.rules, self.session.rules)
        self.assertIs(ctx.manager, self.session.manager)
        self.assertEqual(ctx.action, "explore")
        self.assertEqual(ctx.turn, 99)
        self.assertEqual(ctx.mode, "rule")

    def test_run_turn_increments_turn_and_returns_dict(self) -> None:
        before = self.session.turn
        result = self.session.run_turn(action="quest")
        self.assertEqual(self.session.turn, before + 1)
        self.assertEqual(result["turn"], before + 1)
        self.assertIn("lines", result)
        self.assertIn("day", result)
        self.assertIn("time", result)
        self.assertEqual(result["mode"], "rule")

    def test_run_turn_advances_time_of_day(self) -> None:
        before_time = self.session.state["world"]["time_of_day"]
        self.session.run_turn(action="rest")
        after_time = self.session.state["world"]["time_of_day"]
        self.assertNotEqual(before_time, after_time)

    def test_status_report_includes_world_name(self) -> None:
        report = self.session.status_report()
        world_name = self.session.state["world"].get("name", "Eldoria")
        self.assertIn(world_name, report)
        self.assertIn("파티:", report)

    def test_save_persists_without_touching_package_root(self) -> None:
        self.session.state["inventory"]["party_gold"] = 12345
        self.session.save()
        reloaded = GameSession.from_root(self.root, mode="rule", seed=42)
        self.assertEqual(reloaded.state["inventory"]["party_gold"], 12345)
        package_gold = GameSession.from_root(ROOT, mode="rule", seed=42).state["inventory"]["party_gold"]
        self.assertNotEqual(package_gold, 12345)


class GameSessionLLMModeTests(unittest.TestCase):
    def test_llm_mode_creates_client(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="llm", seed=1)
            self.assertIsNotNone(session.client)


if __name__ == "__main__":
    unittest.main()
