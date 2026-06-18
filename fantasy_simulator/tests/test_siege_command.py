"""Siege command chain — 5 commanders, doctrine, chain collapse."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.test_kingdom_system import _ready_for_kingdom  # noqa: E402
from utils.kingdom_system import complete_kingdom_founding  # noqa: E402
from utils.kingdom_war import resolve_siege_round, start_siege_war  # noqa: E402
from utils.siege_command import (  # noqa: E402
    command_chain_intact,
    ensure_kingdom_commander_roster,
    init_war_command,
    kingdom_commander_roster_status,
    set_defender_siege_command,
)


class SiegeCommandTests(unittest.TestCase):
    def _war(self, root: Path) -> tuple[dict, dict]:
        from utils.game_session import GameSession

        session = GameSession.from_root(root, mode="rule", seed=9)
        state = session.state
        state.setdefault("flags", {})["game_mode"] = "ecology"
        state.setdefault("inventory", {})["party_gold"] = 500_000
        _ready_for_kingdom(state, root)
        complete_kingdom_founding(
            state,
            map_id="ashpoint_01",
            x=10,
            y=10,
            name="지휘 왕국",
            doctrine_id="martial_ascendancy",
            base_dir=root,
        )
        charter = state["flags"]["ecology"]["kingdom_charter"]
        charter["military"]["elite"] = 8
        charter["fortifications"]["walls_level"] = 3
        started = start_siege_war(
            state,
            attacker_civ="goblin_tribe",
            goal_id="plunder",
            goal_label="약탈",
            base_dir=root,
            rng=random.Random(4),
        )
        self.assertTrue(started["ok"])
        return state, started["war"]

    def test_roster_has_five_commanders(self) -> None:
        with isolated_game_root() as root:
            state, _war = self._war(root)
            charter = state["flags"]["ecology"]["kingdom_charter"]
            roster = ensure_kingdom_commander_roster(charter, base_dir=root)
            self.assertEqual(len(roster), 5)
            self.assertGreater(roster[0]["hp"], roster[4]["hp"])
            status = kingdom_commander_roster_status(state, base_dir=root)
            self.assertEqual(len(status["roster"]), 5)

    def test_war_init_commanders(self) -> None:
        with isolated_game_root() as root:
            _state, war = self._war(root)
            cmd = war.get("command", {})
            self.assertEqual(len(cmd["defender"]["commanders"]), 5)
            self.assertEqual(len(cmd["attacker"]["commanders"]), 5)
            self.assertTrue(command_chain_intact(cmd["defender"]))

    def test_set_defender_doctrine(self) -> None:
        with isolated_game_root() as root:
            _state, war = self._war(root)
            r = set_defender_siege_command(
                war,
                doctrine="coordinate_defense",
                posture="citadel",
                base_dir=root,
            )
            self.assertTrue(r["ok"])
            self.assertEqual(war["command"]["defender"]["posture"], "citadel")

    def test_commander_death_can_collapse_chain(self) -> None:
        with isolated_game_root() as root:
            state, war = self._war(root)
            def_block = war["command"]["defender"]
            for c in def_block["commanders"]:
                c["alive"] = False
                c["hp"] = 0
            def_block["command_chain_intact"] = False
            def_block["autonomous"] = True
            r = set_defender_siege_command(
                war, doctrine="protect_commanders", base_dir=root
            )
            self.assertFalse(r["ok"])

    def test_focus_commander_kills_defender_over_many_rounds(self) -> None:
        with isolated_game_root() as root:
            state, war = self._war(root)
            atk_block = war["command"]["attacker"]
            atk_block["doctrine"] = "focus_commander"
            atk_block["posture"] = "forward_command"
            set_defender_siege_command(
                war,
                doctrine="coordinate_defense",
                posture="forward_command",
                base_dir=root,
            )
            supreme = war["command"]["defender"]["commanders"][0]
            start_hp = int(supreme.get("hp", 0))
            fallen = 0
            for i in range(18):
                resolve_siege_round(state, war, base_dir=root, rng=random.Random(20 + i))
                def_cmds = war["command"]["defender"]["commanders"]
                fallen = sum(1 for c in def_cmds if not c.get("alive", True))
                if fallen > 0 or war.get("status") != "active":
                    break
            end_hp = int(supreme.get("hp", 0)) if supreme.get("alive", True) else 0
            dmg = start_hp - end_hp
            self.assertTrue(
                fallen > 0 or dmg >= int(start_hp * 0.35),
                f"지휘관 암살 doctrine 피해 부족 (fallen={fallen}, dmg={dmg}/{start_hp})",
            )

    def test_resolve_round_emits_command_events(self) -> None:
        with isolated_game_root() as root:
            state, war = self._war(root)
            result = resolve_siege_round(
                state, war, base_dir=root, rng=random.Random(11)
            )
            kinds = {e.get("kind") for e in result.get("events", [])}
            self.assertTrue(
                kinds & {"commander_hit", "commander_fall", "strike", "defend"},
                msg=f"unexpected kinds {kinds}",
            )
