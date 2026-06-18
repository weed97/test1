"""Tests for state_report presentation helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.state_loader import StateLoader  # noqa: E402
from utils.state_report import format_status_report, format_summary  # noqa: E402


class StateReportTests(unittest.TestCase):
    def test_format_summary_includes_gold(self) -> None:
        with isolated_game_root() as root:
            loader = StateLoader.from_package_root(root)
            state = loader.load_world_state()
            text = format_summary(state, base_dir=root)
            self.assertIn("Gold:", text)
            self.assertIn("Copper:", text)
            self.assertIn(state["world"]["name"], text)

    def test_format_status_report_delegates_party_block(self) -> None:
        with isolated_game_root() as root:
            loader = StateLoader.from_package_root(root)
            state = loader.load_world_state()
            text = format_status_report(state, loader, mode="rule")
            self.assertIn("파티:", text)
            self.assertIn("모드: rule", text)


if __name__ == "__main__":
    unittest.main()
