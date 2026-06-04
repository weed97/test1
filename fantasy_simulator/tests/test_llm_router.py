"""Tests for keyword-based LLM routing and interactive CLI parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from simulation_engine import (  # noqa: E402
    _should_run_interactive,
    parse_player_input,
    resolve_enemy_id,
)
from utils.llm_router import decide_model_and_prompt  # noqa: E402
from utils.state_loader import StateLoader  # noqa: E402


class LLMRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_state: dict = {"combat": None, "world": {"name": "Eldoria"}}

    def test_combat_routes_to_codex(self) -> None:
        d = decide_model_and_prompt("attack the goblin", self.base_state)
        self.assertTrue(d["use_llm"])
        self.assertEqual(d["model"], "codex")
        self.assertEqual(d["prompt_file"], "prompts/mechanics_codex.md")
        self.assertEqual(d["priority"], "strict_rules")

    def test_explore_routes_to_claude(self) -> None:
        d = decide_model_and_prompt("explore the forest", self.base_state)
        self.assertTrue(d["use_llm"])
        self.assertEqual(d["model"], "claude")
        self.assertEqual(d["prompt_file"], "prompts/narrator_claude.md")
        self.assertEqual(d["priority"], "immersion")

    def test_rest_defaults_to_rule(self) -> None:
        d = decide_model_and_prompt("rest", self.base_state, mode="llm")
        self.assertFalse(d["use_llm"])
        self.assertEqual(d["model"], "rule_based")
        self.assertIsNone(d["prompt_file"])

    def test_active_combat_forces_codex(self) -> None:
        state = dict(self.base_state)
        state["combat"] = {"round": 1}
        d = decide_model_and_prompt("look around", state)
        self.assertEqual(d["model"], "codex")

    def test_rule_mode_skips_llm(self) -> None:
        d = decide_model_and_prompt("explore", self.base_state, mode="rule")
        self.assertFalse(d["use_llm"])
        self.assertEqual(d["model"], "rule_based")


class InteractiveCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = StateLoader.from_package_root(ROOT)

    def test_parse_quit(self) -> None:
        self.assertEqual(parse_player_input("quit")["kind"], "quit")

    def test_parse_combat_with_enemy(self) -> None:
        parsed = parse_player_input("combat malachar", self.loader)
        self.assertEqual(parsed["kind"], "turn")
        self.assertEqual(parsed["action"], "combat")
        self.assertEqual(parsed["enemy_id"], "malachar_voidweaver")

    def test_resolve_enemy_partial(self) -> None:
        self.assertEqual(resolve_enemy_id("gareth", self.loader), "gareth_ironshield")

    def test_should_run_batch_when_turns_gt_one(self) -> None:
        import argparse

        args = argparse.Namespace(
            batch=False,
            combat=None,
            status=False,
            show_routing=False,
            show_prompts=False,
            export_legacy=False,
            interactive=False,
            turns=3,
            action="explore",
        )
        self.assertFalse(_should_run_interactive(args))


if __name__ == "__main__":
    unittest.main()
