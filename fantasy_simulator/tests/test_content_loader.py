"""Tests for on-demand lore/event content loading."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.content_loader import ContentLoader  # noqa: E402
from utils.state_manager import StateManager  # noqa: E402


class ContentLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = ContentLoader(ROOT)

    def test_load_all_event_seeds(self) -> None:
        seeds = self.loader.load_event_seeds()
        self.assertEqual(len(seeds), 121)
        self.assertIn("plaza_song", seeds)

    def test_ashpoint_location_lore(self) -> None:
        text = self.loader.load_location_lore("실버우드 변경 마을 '애쉬포인트'")
        self.assertIn("애쉬포인트", text)

    def test_npc_lore_section(self) -> None:
        text = self.loader.load_npc_lore(["torren_blacksmith"])
        self.assertIn("토렌", text)
        self.assertNotIn("릴리안", text)

    def test_snapshot_includes_narrative_context(self) -> None:
        manager = StateManager(ROOT)
        snap = manager.snapshot(event_limit=3, lore_event_seeds=2)
        ctx = snap.get("narrative_context", {})
        self.assertIn("location_lore", ctx)
        self.assertLessEqual(len(ctx.get("event_seeds", [])), 2)
        self.assertIn("rumors", ctx)


if __name__ == "__main__":
    unittest.main()
