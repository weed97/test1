"""Tests for CLI tab-completion helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.cli import completion_candidates, enemy_short_names  # noqa: E402


class CLIAutocompleteTests(unittest.TestCase):
    def test_empty_line_suggests_base_commands(self) -> None:
        opts = completion_candidates("")
        self.assertIn("explore", opts)
        self.assertIn("talk", opts)

    def test_partial_command(self) -> None:
        self.assertEqual(completion_candidates("ex"), ["explore"])

    def test_talk_npc_prefix(self) -> None:
        self.assertIn("torren", completion_candidates("talk tor"))
        opts = completion_candidates("talk ")
        self.assertIn("토렌", opts)
        self.assertIn("torren", opts)

    def test_investigate_targets(self) -> None:
        opts = completion_candidates("investigate f")
        self.assertIn("forest", opts)

    def test_combat_enemy_from_characters(self) -> None:
        opts = completion_candidates("combat silver", ROOT)
        self.assertTrue(any("silver" in o for o in opts))

    def test_enemy_short_names_includes_malachar(self) -> None:
        names = enemy_short_names(ROOT)
        self.assertIn("malachar", names)


if __name__ == "__main__":
    unittest.main()
