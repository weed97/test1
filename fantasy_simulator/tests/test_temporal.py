"""Temporal model — Nex moments vs Classic turns."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.temporal import classify_moment, resolve_time_steps  # noqa: E402


class TemporalClassificationTests(unittest.TestCase):
    def test_classify_talk_and_glance(self) -> None:
        self.assertEqual(classify_moment("talk lilian"), "talk")
        self.assertEqual(classify_moment("look"), "glance")

    def test_resolve_classic_always_one_step(self) -> None:
        steps, kind, rest = resolve_time_steps(
            "look", temporal_mode="classic", time_scale=0.0
        )
        self.assertEqual(steps, 1)
        self.assertFalse(rest)

    def test_resolve_nex_glance_zero_steps(self) -> None:
        steps, kind, rest = resolve_time_steps(
            "look", temporal_mode="nex", time_scale=1.0
        )
        self.assertEqual(steps, 0)
        self.assertEqual(kind, "glance")
        self.assertFalse(rest)

    def test_resolve_nex_rest_until_morning(self) -> None:
        steps, kind, rest = resolve_time_steps(
            "rest", temporal_mode="nex", time_scale=1.0
        )
        self.assertEqual(steps, 0)
        self.assertTrue(rest)


class TemporalRunTurnTests(unittest.TestCase):
    def test_classic_explore_advances_one_period(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=42)
            before = session.state["world"]["time_of_day"]
            session.run_turn("explore", temporal_mode="classic")
            after = session.state["world"]["time_of_day"]
            self.assertNotEqual(before, after)
            result = session.run_turn("explore", temporal_mode="classic")
            self.assertFalse(any("[체감]" in line for line in result["lines"]))

    def test_nex_glance_does_not_advance_time(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=42)
            session.state["world"]["time_of_day"] = "afternoon"
            session.manager.save(session.state)
            result = session.run_turn("look", temporal_mode="nex")
            self.assertEqual(session.state["world"]["time_of_day"], "afternoon")
            self.assertEqual(result.get("time_steps"), 0)
            self.assertTrue(any("[체감]" in line for line in result["lines"]))

    def test_nex_talk_advances_and_includes_somatic(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=42)
            session.state["world"]["time_of_day"] = "afternoon"
            session.manager.save(session.state)
            result = session.run_turn("talk lilian", temporal_mode="nex")
            self.assertEqual(result.get("time_steps"), 1)
            self.assertNotEqual(session.state["world"]["time_of_day"], "afternoon")
            self.assertTrue(any("[체감]" in line for line in result["lines"]))

    def test_nex_rest_jumps_to_morning(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=42)
            session.state["world"]["time_of_day"] = "evening"
            session.manager.save(session.state)
            session.run_turn("rest", temporal_mode="nex")
            self.assertEqual(session.state["world"]["time_of_day"], "morning")


if __name__ == "__main__":
    unittest.main()
