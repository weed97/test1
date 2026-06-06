"""Skill buff effects — kings_aegis in ecology combat."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.agent_mind import use_skill  # noqa: E402
from utils.skill_effects import apply_damage_with_buffs, tick_agent_buffs  # noqa: E402


class SkillEffectsTests(unittest.TestCase):
    def test_kings_aegis_applies_buff(self) -> None:
        with isolated_game_root() as root:
            arthur = {
                "archetype_id": "npc_arthur_pendragon",
                "world_sovereign_holder": True,
                "hp": 40,
                "max_hp": 100,
                "mp": 200,
                "skill_cooldowns": {},
            }
            dmg, sid = use_skill(
                arthur,
                arthur,
                "kings_aegis",
                base_dir=root,
                rng=random.Random(1),
            )
            self.assertEqual(sid, "kings_aegis")
            self.assertEqual(dmg, 0)
            self.assertIn("kings_aegis", arthur.get("active_buffs", {}))

    def test_damage_reduction_from_buff(self) -> None:
        with isolated_game_root() as root:
            defender = {
                "hp": 80,
                "max_hp": 100,
                "active_buffs": {
                    "kings_aegis": {
                        "effects": {"damage_reduction_milli": 500},
                        "beats_remaining": 4,
                    }
                },
            }
            dealt = apply_damage_with_buffs(defender, 20, base_dir=root)
            self.assertEqual(dealt, 10)

    def test_buff_ticks_regen_and_expires(self) -> None:
        with isolated_game_root() as root:
            agent = {
                "label": "테스트",
                "hp": 50,
                "max_hp": 100,
                "active_buffs": {
                    "kings_aegis": {
                        "label": "왕의 가호",
                        "effects": {"regen_per_sec_milli": 160_000},
                        "beats_remaining": 1,
                    }
                },
            }
            lines = tick_agent_buffs(agent, base_dir=root)
            self.assertGreater(int(agent["hp"]), 50)
            self.assertNotIn("active_buffs", agent)
            self.assertTrue(any("종료" in ln for ln in lines))


if __name__ == "__main__":
    unittest.main()
