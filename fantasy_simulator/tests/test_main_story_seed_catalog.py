"""Validate main story flow references exist in the seed catalog."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.content_loader import ContentLoader  # noqa: E402
from utils.io_helpers import load_json  # noqa: E402


class MainStorySeedCatalogTests(unittest.TestCase):
    def test_flow_step_queues_reference_known_seeds(self) -> None:
        with isolated_game_root() as root:
            catalog = ContentLoader(root).load_event_seeds()
            stories = load_json(root / "events" / "main_stories.json").get("stories", [])
            story = next(s for s in stories if s["id"] == "ashen_seal_cracking")
            missing: list[str] = []
            for flow_key in ("phase1_flow", "phase2_flow", "phase3_flow"):
                flow = story.get(flow_key, {})
                for step_events in flow.get("step_queue", {}).values():
                    for sid in step_events:
                        if sid not in catalog:
                            missing.append(f"{flow_key}:{sid}")
                for sid in flow.get("climax_seeds", []):
                    if sid not in catalog:
                        missing.append(f"{flow_key}:climax:{sid}")
            self.assertEqual(missing, [], f"unknown seed ids: {missing}")

    def test_progress_sources_reference_known_seeds(self) -> None:
        with isolated_game_root() as root:
            catalog = ContentLoader(root).load_event_seeds()
            stories = load_json(root / "events" / "main_stories.json").get("stories", [])
            story = next(s for s in stories if s["id"] == "ashen_seal_cracking")
            progress_ids = story.get("progress_sources", {}).get("seed_ids", {})
            missing = [sid for sid in progress_ids if sid not in catalog]
            self.assertEqual(missing, [], f"unknown progress seed ids: {missing}")


if __name__ == "__main__":
    unittest.main()
