"""Ecology agent objects — stats, MP, skills, intelligence."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.ecology_objects import build_ecology_agent, normalize_agent  # noqa: E402
from utils.field_agents import (  # noqa: E402
    agents_manifest,
    ensure_ecology_seeds,
    get_agents,
    tick_field_ecology,
)
from utils.game_session import GameSession  # noqa: E402


class EcologyObjectTests(unittest.TestCase):
    def test_build_agent_has_stats_hp_mp(self) -> None:
        with isolated_game_root() as root:
            agent = build_ecology_agent(
                archetype_id="innkeeper_civilian",
                kind="npc",
                map_id="ashpoint_01",
                x=1,
                y=2,
                base_dir=root,
            )
            self.assertEqual(agent["object_type"], "ecology_agent")
            self.assertIn("stats", agent)
            self.assertGreater(agent["max_hp"], 0)
            self.assertGreater(agent["max_mp"], 0)
            self.assertIn("intelligence", agent)
            self.assertIn("iq", agent["intelligence"])

    def test_tick_uses_skills(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=11)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            session.state["world"]["map_id"] = "forest_01"
            ensure_ecology_seeds(session.state, base_dir=root)
            lines: list[str] = []
            for _ in range(12):
                lines.extend(tick_field_ecology(session.state, base_dir=root))
            joined = "\n".join(lines)
            self.assertTrue(
                "[스킬]" in joined or "[전투]" in joined or "[지성]" in joined
            )
            manifest = agents_manifest(session.state, "forest_01", base_dir=root)
            self.assertTrue(manifest)
            self.assertEqual(manifest[0].get("object_type"), "ecology_agent")
            self.assertIn("godot_sprite_key", manifest[0])

    def test_legacy_agent_normalized(self) -> None:
        with isolated_game_root() as root:
            legacy = {"kind": "monster", "hp": 20, "skills": ["scratch"]}
            norm = normalize_agent(legacy, base_dir=root)
            self.assertEqual(norm["object_type"], "ecology_agent")
            self.assertIn("mp", norm)


if __name__ == "__main__":
    unittest.main()
