"""Unit tests for turn_processor — process_player_action in isolation."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.content_loader import ContentLoader  # noqa: E402
from utils.event_engine import EventEngine  # noqa: E402
from utils.rule_engine import RuleEngine  # noqa: E402
from utils.state_manager import StateManager  # noqa: E402
from utils.turn_context import TurnContext  # noqa: E402
from utils.turn_processor import process_player_action, run_rule_engine  # noqa: E402


def _build_context(root: Path, *, action: str = "explore", turn: int = 1, mode: str = "rule") -> TurnContext:
    manager = StateManager(root)
    state = manager.load()
    rng = random.Random(42)
    content = ContentLoader(root)
    event_engine = EventEngine(content, rng)
    rules = RuleEngine(state, rng, event_engine=event_engine)
    return TurnContext(
        state=state,
        action=action,
        turn=turn,
        mode=mode,  # type: ignore[arg-type]
        manager=manager,
        rules=rules,
        client=None,
    )


class ProcessPlayerActionTests(unittest.TestCase):
    def test_quest_action_uses_rule_engine(self) -> None:
        with isolated_game_root() as root:
            ctx = _build_context(root, action="quest")
            out = process_player_action(ctx)
            self.assertFalse(out["decision"]["use_llm"])
            self.assertEqual(out["decision"]["model"], "rule_based")
            self.assertTrue(any("퀘스트" in line or "연기" in line for line in out["lines"]))

    def test_rule_mode_skips_llm_for_explore(self) -> None:
        with isolated_game_root() as root:
            ctx = _build_context(root, action="explore", mode="rule")
            out = process_player_action(ctx)
            self.assertFalse(out["decision"]["use_llm"])
            models = {r.get("model") for r in out["results"]}
            self.assertIn("rule", models)

    def test_unknown_action_returns_summary(self) -> None:
        with isolated_game_root() as root:
            manager = StateManager(root)
            state = manager.load()
            rng = random.Random(42)
            rules = RuleEngine(state, rng, event_engine=None)
            ctx = TurnContext(
                state=state,
                action="dance wildly",
                turn=1,
                mode="rule",
                manager=manager,
                rules=rules,
                client=None,
            )
            mechanical = run_rule_engine(ctx)
            self.assertIn("알 수 없는", mechanical["summary"])


class ExecuteTurnIntegrationTests(unittest.TestCase):
    def test_execute_turn_advances_time(self) -> None:
        from utils.turn_processor import execute_turn

        with isolated_game_root() as root:
            ctx = _build_context(root, action="rest", turn=5)
            before = ctx.state["world"]["time_of_day"]
            result = execute_turn(ctx, loader=ctx.manager.loader)
            self.assertNotEqual(before, ctx.state["world"]["time_of_day"])
            self.assertEqual(result.turn, 5)
            self.assertTrue(result.lines)


if __name__ == "__main__":
    unittest.main()
