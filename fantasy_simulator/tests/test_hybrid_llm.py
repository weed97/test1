"""Hybrid / LLM mode tests with injected MockLLMClient."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.mock_llm_client import MockLLMClient  # noqa: E402
from utils.content_loader import ContentLoader  # noqa: E402
from utils.event_engine import EventEngine  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.rule_engine import RuleEngine  # noqa: E402
from utils.state_manager import StateManager  # noqa: E402
from utils.turn_context import TurnContext  # noqa: E402
from utils.turn_processor import process_player_action  # noqa: E402


def _hybrid_context(root: Path, mock: MockLLMClient, *, action: str = "explore", turn: int = 1) -> TurnContext:
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
        mode="hybrid",
        manager=manager,
        rules=rules,
        client=mock,  # type: ignore[arg-type]
    )


class HybridModeTests(unittest.TestCase):
    def test_hybrid_runs_rule_then_mock_llm(self) -> None:
        mock = MockLLMClient(narrator_text="숲길이 고요하다.")
        with isolated_game_root() as root:
            ctx = _hybrid_context(root, mock, action="explore")
            out = process_player_action(ctx)

        self.assertTrue(out["decision"]["use_llm"])
        models = [r.get("model") for r in out["results"]]
        self.assertIn("rule", models)
        self.assertTrue(any(r.get("role") == "narrator" for r in out["results"]))
        self.assertTrue(any("숲길이 고요하다" in line for line in out["lines"]))
        self.assertEqual(len(mock.calls), 1)
        self.assertEqual(mock.calls[0]["role"], "narrator")

    def test_llm_failure_falls_back_to_rule_engine(self) -> None:
        mock = MockLLMClient(fail_roles={"narrator"})
        with isolated_game_root() as root:
            ctx = _hybrid_context(root, mock, action="explore")
            ctx.mode = "llm"  # type: ignore[misc]
            out = process_player_action(ctx)

        self.assertTrue(any("규칙 엔진" in line for line in out["lines"]))
        rule_results = [r for r in out["results"] if r.get("model") == "rule"]
        self.assertTrue(rule_results)
        self.assertIn("fallback_reason", rule_results[-1])

    def test_game_session_accepts_injected_client(self) -> None:
        mock = MockLLMClient(narrator_text="injected")
        with isolated_game_root() as root:
            manager = StateManager(root)
            state = manager.load()
            session = GameSession(manager, state, mode="hybrid", seed=42, client=mock)  # type: ignore[arg-type]
            self.assertIs(session.client, mock)
            result = session.run_turn(action="explore")
            self.assertTrue(any("injected" in line for line in result["lines"]))


if __name__ == "__main__":
    unittest.main()
