"""Tests for structured output parsing and state sharding."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys

sys.path.insert(0, str(ROOT))

from utils.structured_output import (  # noqa: E402
    StructuredOutputClient,
    StructuredOutputError,
    extract_json_object,
    validate_schema,
)
from utils.state_store import StateStore  # noqa: E402


class StructuredOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = StructuredOutputClient(schemas_dir=ROOT / "schemas")

    def test_extract_from_markdown_block(self) -> None:
        text = (
            'Here is output:\n```json\n'
            '{"consistency_score": 8, "issues_found": [], '
            '"recommended_corrections": [], "narrative_direction_suggestion": "hint"}\n```'
        )
        data = extract_json_object(text)
        self.assertEqual(data["narrative_direction_suggestion"], "hint")
        parsed = self.client.parse_and_validate(text, "world_arbiter_consistency")
        self.assertIn("consistency_score", parsed)

    def test_validate_combat_schema(self) -> None:
        schema = self.client.load_schema("combat_referee")
        valid = {
            "combat_log": ["a"],
            "combat_state": {"round": 1},
            "world_updates": {"event_log_append": []},
            "character_updates": {},
        }
        self.assertEqual(validate_schema(valid, schema), [])

    def test_validate_event_alternatives_schema(self) -> None:
        schema = self.client.load_schema("event_alternatives")
        valid = {
            "alternatives": [
                {"id": "a", "summary": "test", "risk": "low"},
                {"id": "b", "summary": "test2", "risk": "high"},
            ],
            "recommended_id": "a",
            "narrative_hint": "hint",
        }
        self.assertEqual(validate_schema(valid, schema), [])
    def test_validate_mechanics_schema(self) -> None:
        schema = self.client.load_schema("mechanics_codex")
        valid = {
            "result_type": "exploration",
            "success": True,
            "description": "Found gold.",
            "state_changes": {},
            "consequences": ["+10 gold"],
        }
        self.assertEqual(validate_schema(valid, schema), [])

    def test_validate_world_arbiter_consistency_schema(self) -> None:
        schema = self.client.load_schema("world_arbiter_consistency")
        invalid = {
            "consistency_score": 8,
            "issues_found": [],
            "recommended_corrections": [],
            "narrative_direction_suggestion": "ok",
            "extra": True,
        }
        errors = validate_schema(invalid, schema)
        self.assertTrue(any("additional property" in e for e in errors))


class StateStoreTests(unittest.TestCase):
    def test_shard_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "state").mkdir()
            for name in ("meta", "world", "factions", "inventory", "flags", "combat"):
                (root / "state" / f"{name}.json").write_text("{}", encoding="utf-8")
            (root / "state" / "party.json").write_text(
                json.dumps({"party": ["a"], "active_characters": ["a"], "npc_locations": {}}),
                encoding="utf-8",
            )
            (root / "state" / "event_log.json").write_text(
                json.dumps({"next_turn": 1, "entries": []}), encoding="utf-8"
            )
            store = StateStore(root)
            state = store.load()
            state["world"] = {"name": "test", "day": 2}
            store.save(state)
            reloaded = store.load()
            self.assertEqual(reloaded["world"]["day"], 2)


if __name__ == "__main__":
    unittest.main()
